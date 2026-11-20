"""Social networks (docs/09, settings): one registry for the panel form, the footer and JSON-LD.

To add a network: a URLField on SiteSettings, a row here, and a WebP icon in static/img/social/.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from django.core.exceptions import ValidationError

ICON_DIR = "img/social"


@dataclass(frozen=True)
class Network:
    field: str
    label: str
    icon: str
    hosts: tuple[str, ...]  # [ASSUMPTION] the network's own domains; a link elsewhere is refused


NETWORKS = (
    Network("instagram_url", "اینستاگرام", "instagram.webp", ("instagram.com",)),
    Network("telegram_url", "تلگرام", "telegram.webp", ("t.me", "telegram.me", "telegram.org")),
    Network("x_url", "ایکس (توییتر)", "x.webp", ("x.com", "twitter.com")),
    Network("bale_url", "بله", "bale.webp", ("ble.ir", "bale.ai")),
    Network("eitaa_url", "ایتا", "eitaa.webp", ("eitaa.com",)),
    Network("rubika_url", "روبیکا", "rubika.webp", ("rubika.ir",)),
    Network("igap_url", "آی‌گپ", "igap.webp", ("igap.net",)),
    Network("soroush_url", "سروش پلاس", "soroush.webp", ("splus.ir", "sapp.ir")),
)


def normalize(network: Network, raw: str | None) -> str:
    """Complete a pasted address to https and refuse anything that is not on this network's own domains."""
    value = (raw or "").strip()
    if not value:
        return ""
    invalid = ValidationError("نشانی معتبر نیست")
    if any(ch.isspace() for ch in value):
        raise invalid
    if "://" not in value:
        value = f"https://{value.lstrip('/')}"
    try:
        parts = urlsplit(value)
        host = (parts.hostname or "").lower()
    except ValueError:
        raise invalid from None
    if parts.scheme not in ("http", "https") or parts.username or parts.password:
        raise invalid
    if not any(host == own or host.endswith(f".{own}") for own in network.hosts):
        raise ValidationError("نشانی باید از دامنه‌ی خود این شبکه باشد: " + "، ".join(network.hosts))
    return urlunsplit(("https", parts.netloc, parts.path, parts.query, ""))


def links(site) -> list[dict]:
    """The networks the store filled in, in registry order."""
    return [
        {"label": network.label, "url": url, "icon": f"{ICON_DIR}/{network.icon}"}
        for network in NETWORKS
        if (url := getattr(site, network.field, ""))
    ]
