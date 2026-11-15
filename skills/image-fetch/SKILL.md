---
name: image-fetch
description: Find images on the internet and download them to disk, optionally having a cheap vision model describe each one so you know what it is without spending your own tokens. Uses the Serper (Google Images) API. Use this skill whenever the user or a task needs a real photo or picture from the web - "download a picture of a refrigerator", "find me 5 photos of X", "get an image for this page/slide/product", "save reference images", or any time you need image files and do not already have them, even if the user does not say "download".
---

# image-fetch

One script does everything: `scripts/imgfetch.py` (Python 3, standard library only).
API keys for Serper and the vision router are **already embedded in the script**, so there is nothing to configure.

Run it as:

```
python3 <skill_dir>/scripts/imgfetch.py <command> [options]
```

## 1. Search + download

```
python3 scripts/imgfetch.py search "white refrigerator" -n 5 -o ./images
```

It asks Serper for more candidates than needed, downloads in parallel, skips broken links, non-images, tiny files and duplicates, and keeps going until it has `-n` good images (or runs out of candidates). Files are saved as `<query_slug>_01.jpg`, `_02.png`, ... in the output folder, which is created if missing.

Output is a short text list: path, size, title, source site, page URL. Add `--json` for machine-readable output.

### Optional: let a cheap model look at the images

```
python3 scripts/imgfetch.py search "white refrigerator" -n 5 -o ./images --analyze
```

Each image is sent to the router (model `fast`) and you get a 1-2 sentence description plus `MATCH: yes/partial/no` for how well it fits the query. **Use this when you need to know what the images actually show** (pick the best one, reject wrong ones, find the one with a certain feature). It costs you only the short text, not image tokens. Skip it when the first result is obviously fine.

Customize the question with `--prompt`:

```
... --analyze --prompt "Is the background plain white? Is there any watermark? Answer briefly."
```

### Common options

| Option | Meaning |
|---|---|
| `-n 8` | how many images you want (default 5) |
| `-o DIR` | where to save (default `./images`); any path works |
| `--name foo` | filename prefix instead of the query slug |
| `--analyze` | describe each image with the vision model |
| `--prompt "..."` | custom analysis question |
| `--model fast` | vision model name (default `fast`) |
| `--min-width 800 --min-height 600` | skip small images (uses Serper's metadata) |
| `--size large\|medium\|icon` | Google size filter |
| `--type photo\|clipart\|lineart\|face\|animated` | Google image-type filter |
| `--tbs "ic:specific,isc:white"` | raw Google filter, e.g. dominant color white |
| `--gl us --hl en` | country / language (use `--gl ir --hl fa` for Persian/Iran results) |
| `--page 2` | next page of results, for different images |
| `--exclude-domain pinterest` | skip a site (repeatable) |
| `--candidates 30` | how many results to request from Serper (default max(10, 2n), up to 100) |
| `--no-download` | only list image URLs and metadata, download nothing |
| `--workers 6` | parallelism for downloads/analysis |
| `--json` | JSON output |

## 2. Analyze images you already have

```
python3 scripts/imgfetch.py analyze a.jpg b.png --prompt "What brand is this?"
```

## Working tips

- **Write the query in English** unless a local-language result is what you want; Google Images results are better and more varied. Be specific: "samsung french door refrigerator stainless steel front view" beats "fridge".
- Need several distinct kinds of images? Run separate searches with different queries and `--name`, instead of one big `-n`.
- If you got too few or bad results: change the query, raise `--candidates`, try `--page 2`, drop filters, or `--exclude-domain` a problematic site.
- A result marked `THUMBNAIL ONLY` means the full-size file was blocked and only the low-res thumbnail was saved. Prefer another image if quality matters.
- Move or rename files freely afterwards (`mv`); the files are normal images and nothing else tracks them.
- Exit code 2 = search worked but zero images could be downloaded; exit code 1 = an error (message on stderr, e.g. bad key or no network).
- Network access to `google.serper.dev`, the router host, and arbitrary image websites is required. If the environment blocks them, tell the user which domains need to be allowed.
- Most Google images are copyrighted. Tell the user the source site (shown in the output) when handing images over, and if the images will be published commercially, suggest Unsplash/Pexels/Wikimedia instead.

## Changing keys or endpoints

Edit the constants at the top of `scripts/imgfetch.py`, or override per run with environment variables: `SERPER_API_KEY`, `SERPER_URL`, `ROUTER_BASE_URL`, `ROUTER_API_KEY`, `ROUTER_MODEL`.
