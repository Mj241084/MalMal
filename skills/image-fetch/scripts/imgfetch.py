#!/usr/bin/env python3
"""
imgfetch - find images with the Serper API, download them to disk, and
(optionally) have a cheap vision model describe each one so the calling agent
does not need to spend its own tokens looking at them.

Only the Python standard library is required (Pillow is used for resizing
before analysis if it happens to be installed).

Usage:
  python3 imgfetch.py search "white refrigerator" -n 5 -o ./imgs
  python3 imgfetch.py search "white refrigerator" -n 5 -o ./imgs --analyze
  python3 imgfetch.py analyze a.jpg b.png --prompt "Is there a logo?"
Run with -h on each sub-command for all options.
"""

import argparse
import base64
import concurrent.futures as cf
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# --------------------------------------------------------------------------
# CONFIG - keys are embedded on purpose (owner asked for it).
# Environment variables, if set, override the embedded values.
# --------------------------------------------------------------------------
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "ab5e46a80791050e9e7fcdac0cbdd7ca3a73a7dd")
SERPER_URL = os.environ.get("SERPER_URL", "https://google.serper.dev/images")

ROUTER_BASE_URL = os.environ.get("ROUTER_BASE_URL", "https://gemini-hermes-router.matghz24.workers.dev/v1")
ROUTER_API_KEY = os.environ.get("ROUTER_API_KEY", "mj241084")
ROUTER_MODEL = os.environ.get("ROUTER_MODEL", "fast")

# Browser-like UA: some CDNs / workers reject the default python-urllib UA.
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

BASE_PROMPT = (
    "Describe this image in 1-2 short factual sentences: what exactly it shows "
    "(object type, color, style, angle, background, any visible text or brand)."
)


# --------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------
def http_json(url, payload, headers, timeout=60, retries=2):
    """POST JSON, return parsed JSON. Retries on network errors, 429 and 5xx."""
    data = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA}
    h.update(headers)
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=h, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            last = RuntimeError(f"HTTP {e.code} from {url}: {body}")
            if e.code < 500 and e.code != 429:
                break
        except Exception as e:  # timeouts, DNS, bad JSON...
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise last


def safe_url(url):
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (
            p.scheme,
            p.netloc.encode("idna").decode("ascii") if p.netloc else p.netloc,
            urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=~-._"),
            urllib.parse.quote(p.query, safe="=&%:@!$'()*+,;/?~-._"),
            "",
        )
    )


def fetch_bytes(url, referer, timeout, max_bytes=15_000_000):
    h = {"User-Agent": UA, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(safe_url(url), headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("file too large")
    return data


def sniff(b):
    """Return file extension from magic bytes, or None if it is not an image."""
    if b[:3] == b"\xff\xd8\xff":
        return "jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "webp"
    if b[4:12] == b"ftypavif":
        return "avif"
    if b[:2] == b"BM":
        return "bmp"
    return None


MIME = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "avif": "image/avif",
    "bmp": "image/bmp",
}


# --------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------
def try_download(item, a):
    """Try the full-size URL, then the thumbnail. Returns dict or (None, reason)."""
    reasons = []
    referer = item.get("link")
    for key, is_thumb in (("imageUrl", False), ("thumbnailUrl", True)):
        url = item.get(key)
        if not url:
            continue
        try:
            data = fetch_bytes(url, referer, a.timeout)
        except Exception as e:
            reasons.append(f"{key}: {type(e).__name__}: {str(e)[:80]}")
            continue
        ext = sniff(data)
        if not ext:
            reasons.append(f"{key}: not an image")
            continue
        if len(data) < a.min_bytes:
            reasons.append(f"{key}: too small ({len(data)} B)")
            continue
        return {"data": data, "ext": ext, "thumbnail_only": is_thumb, "url": url}, None
    return None, "; ".join(reasons) or "no url"


def next_path(outdir, prefix, ext, counter):
    while True:
        counter[0] += 1
        p = os.path.join(outdir, f"{prefix}_{counter[0]:02d}.{ext}")
        if not os.path.exists(p):
            return p


# --------------------------------------------------------------------------
# Vision analysis (OpenAI-compatible chat completions on the router)
# --------------------------------------------------------------------------
def prep_image(path, max_side):
    with open(path, "rb") as fh:
        raw = fh.read()
    ext = sniff(raw)
    try:
        from PIL import Image  # optional

        im = Image.open(io.BytesIO(raw))
        im.load()
        if max(im.size) > max_side or im.format not in ("JPEG", "PNG"):
            im = im.convert("RGB")
            im.thumbnail((max_side, max_side))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=85)
            return buf.getvalue(), "image/jpeg"
    except Exception:
        pass
    return raw, MIME.get(ext, "image/jpeg")


def describe(path, prompt, model, max_side, max_tokens):
    data, mime = prep_image(path, max_side)
    b64 = base64.b64encode(data).decode("ascii")
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }
        ],
    }
    resp = http_json(
        ROUTER_BASE_URL.rstrip("/") + "/chat/completions",
        payload,
        {"Authorization": "Bearer " + ROUTER_API_KEY},
        timeout=120,
    )
    content = resp["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
    return (content or "").strip()


def analyze_paths(paths, prompt, a):
    def one(p):
        try:
            return describe(p, prompt, a.model, a.max_side, a.max_tokens), None
        except Exception as e:
            return None, f"{type(e).__name__}: {str(e)[:200]}"

    with cf.ThreadPoolExecutor(max(1, a.workers)) as ex:
        return list(ex.map(one, paths))


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
def build_tbs(a):
    parts = []
    parts += {"large": ["isz:l"], "medium": ["isz:m"], "icon": ["isz:i"]}.get(a.size, [])
    parts += {
        "photo": ["itp:photo"],
        "clipart": ["itp:clipart"],
        "lineart": ["itp:lineart"],
        "face": ["itp:face"],
        "animated": ["itp:animated"],
    }.get(a.type, [])
    if a.tbs:
        parts.append(a.tbs)
    return ",".join(parts)


def slug(q):
    return re.sub(r"[^a-z0-9]+", "_", q.lower()).strip("_")[:40] or "img"


def cmd_search(a):
    n = max(1, a.num)
    cand_n = a.candidates or min(100, max(10, n * 2))
    payload = {"q": a.query, "num": cand_n, "gl": a.gl, "hl": a.hl}
    if a.page and a.page > 1:
        payload["page"] = a.page
    if a.location:
        payload["location"] = a.location
    tbs = build_tbs(a)
    if tbs:
        payload["tbs"] = tbs

    resp = http_json(SERPER_URL, payload, {"X-API-KEY": SERPER_API_KEY})
    raw = resp.get("images") or []

    # filter + dedupe candidates
    excl = [d.lower() for d in (a.exclude_domain or [])]
    cands, seen_urls = [], set()
    for it in raw:
        url = it.get("imageUrl")
        if not url or url in seen_urls:
            continue
        dom = (it.get("domain") or urllib.parse.urlsplit(it.get("link") or "").netloc).lower()
        if any(x in dom for x in excl):
            continue
        w, h = it.get("imageWidth"), it.get("imageHeight")
        if a.min_width and w and w < a.min_width:
            continue
        if a.min_height and h and h < a.min_height:
            continue
        seen_urls.add(url)
        cands.append(it)

    report = {
        "query": a.query,
        "requested": n,
        "candidates_found": len(raw),
        "candidates_after_filters": len(cands),
        "images": [],
        "skipped": [],
    }

    if a.no_download:
        for it in cands[:n]:
            report["images"].append(
                {
                    "title": it.get("title"),
                    "image_url": it.get("imageUrl"),
                    "page_url": it.get("link"),
                    "source": it.get("source") or it.get("domain"),
                    "width": it.get("imageWidth"),
                    "height": it.get("imageHeight"),
                }
            )
        return report

    outdir = os.path.abspath(a.out)
    os.makedirs(outdir, exist_ok=True)

    # download until we have n good, unique images
    good, seen_hash, i = [], set(), 0
    while len(good) < n and i < len(cands):
        chunk = cands[i : i + max(a.workers, n - len(good))]
        i += len(chunk)
        with cf.ThreadPoolExecutor(max(1, a.workers)) as ex:
            outs = list(ex.map(lambda it: try_download(it, a), chunk))
        for it, (res, why) in zip(chunk, outs, strict=False):
            if not res:
                report["skipped"].append({"url": it.get("imageUrl"), "reason": why})
                continue
            h = hashlib.sha1(res["data"]).hexdigest()
            if h in seen_hash:
                continue
            seen_hash.add(h)
            good.append((it, res))
            if len(good) >= n:
                break

    prefix = a.name or slug(a.query)
    counter = [0]
    paths = []
    for it, res in good:
        p = next_path(outdir, prefix, res["ext"], counter)
        with open(p, "wb") as f:
            f.write(res["data"])
        paths.append(p)
        report["images"].append(
            {
                "path": p,
                "bytes": len(res["data"]),
                "width": it.get("imageWidth"),
                "height": it.get("imageHeight"),
                "title": it.get("title"),
                "source": it.get("source") or it.get("domain"),
                "page_url": it.get("link"),
                "image_url": res["url"],
                "thumbnail_only": res["thumbnail_only"],
            }
        )

    if a.analyze and paths:
        prompt = a.prompt
        if not prompt:
            prompt = (
                BASE_PROMPT + f' The user searched for "{a.query}". '
                'End with "MATCH: yes", "MATCH: partial" or "MATCH: no" depending on '
                "how well the image fits that search."
            )
        for info, (text, err) in zip(report["images"], analyze_paths(paths, prompt, a), strict=False):
            if err:
                info["analysis_error"] = err
            else:
                info["analysis"] = text
    return report


def cmd_analyze(a):
    files = [os.path.abspath(f) for f in a.files]
    missing = [f for f in files if not os.path.isfile(f)]
    if missing:
        sys.exit("File(s) not found: " + ", ".join(missing))
    prompt = a.prompt or BASE_PROMPT
    report = {"images": []}
    for p, (text, err) in zip(files, analyze_paths(files, prompt, a), strict=False):
        info = {"path": p}
        if err:
            info["analysis_error"] = err
        else:
            info["analysis"] = text
        report["images"].append(info)
    return report


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def print_report(rep):
    if "query" in rep:
        print(
            f'Query: "{rep["query"]}" | requested {rep["requested"]} | '
            f"got {len(rep['images'])} | candidates {rep['candidates_found']} "
            f"(after filters {rep['candidates_after_filters']}) | skipped {len(rep['skipped'])}"
        )
    for i, im in enumerate(rep["images"], 1):
        loc = im.get("path") or im.get("image_url")
        meta = []
        if im.get("width") and im.get("height"):
            meta.append(f"{im['width']}x{im['height']}")
        if im.get("bytes"):
            meta.append(f"{im['bytes'] // 1024} KB")
        if im.get("thumbnail_only"):
            meta.append("THUMBNAIL ONLY (full-size download failed)")
        print(f"[{i}] {loc}" + (f"  ({', '.join(meta)})" if meta else ""))
        if im.get("title"):
            print(f"    title: {im['title']}")
        if im.get("source"):
            print(f"    source: {im['source']}")
        if im.get("page_url"):
            print(f"    page: {im['page_url']}")
        if im.get("analysis"):
            print("    analysis: " + im["analysis"].replace("\n", " "))
        if im.get("analysis_error"):
            print("    analysis_error: " + im["analysis_error"])
    if rep.get("skipped") and "query" in rep and len(rep["images"]) < rep["requested"]:
        print("Some candidates were skipped; first reasons:")
        for s in rep["skipped"][:3]:
            print(f"  - {s['reason']}")


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Search, download and (optionally) analyze images.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_analysis_opts(p):
        p.add_argument("--model", default=ROUTER_MODEL, help=f"vision model on the router (default: {ROUTER_MODEL})")
        p.add_argument("--prompt", help="custom analysis prompt (replaces the default)")
        p.add_argument(
            "--max-side",
            type=int,
            default=1024,
            help="downscale images to this size before analysis if Pillow is installed (default 1024)",
        )
        p.add_argument("--max-tokens", type=int, default=300, help="max tokens of each analysis answer (default 300)")
        p.add_argument("--workers", type=int, default=6, help="parallel workers (default 6)")

    s = sub.add_parser("search", help="search Google Images via Serper and download results")
    s.add_argument("query")
    s.add_argument("-n", "--num", type=int, default=5, help="how many images to end up with (default 5)")
    s.add_argument("-o", "--out", default="./images", help="output directory (default ./images)")
    s.add_argument("--name", help="filename prefix (default: slug of the query)")
    s.add_argument("--analyze", action="store_true", help="describe each downloaded image with the vision model")
    s.add_argument("--no-download", action="store_true", help="only list URLs, download nothing")
    s.add_argument("--min-width", type=int, default=0)
    s.add_argument("--min-height", type=int, default=0)
    s.add_argument("--min-bytes", type=int, default=3000, help="discard files smaller than this (default 3000)")
    s.add_argument("--size", choices=["large", "medium", "icon"], help="Google size filter")
    s.add_argument(
        "--type", choices=["photo", "clipart", "lineart", "face", "animated"], help="Google image-type filter"
    )
    s.add_argument("--tbs", help="raw Google tbs filter string, e.g. 'ic:specific,isc:white'")
    s.add_argument("--gl", default="us", help="country code (default us)")
    s.add_argument("--hl", default="en", help="language code (default en)")
    s.add_argument("--location", help="search location, e.g. 'Tehran, Iran'")
    s.add_argument("--page", type=int, default=1, help="result page (default 1)")
    s.add_argument(
        "--candidates", type=int, help="how many results to request from Serper (default max(10, 2*num), max 100)"
    )
    s.add_argument(
        "--exclude-domain", action="append", help="skip results whose domain contains this text (repeatable)"
    )
    s.add_argument("--timeout", type=int, default=25, help="download timeout in seconds (default 25)")
    s.add_argument("--json", action="store_true", help="print JSON instead of text")
    add_analysis_opts(s)
    s.set_defaults(func=cmd_search)

    t = sub.add_parser("analyze", help="describe existing image files with the vision model")
    t.add_argument("files", nargs="+")
    t.add_argument("--json", action="store_true")
    add_analysis_opts(t)
    t.set_defaults(func=cmd_analyze)

    a = ap.parse_args()
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        rep = a.func(a)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print_report(rep)
    if a.cmd == "search" and not rep["images"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
