"""Minimal .env loader and environment helpers (no external dependencies)."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

_ENV_LOADED = False


def load_dotenv(base_dir: Path) -> None:
    """Load key=value pairs from .env if present, without overwriting process env."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True

    env_path = base_dir / ".env"
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def get_env(name: str, default: str = "") -> str:
    val = os.environ.get(name, "").strip()
    return val if val else default


def get_env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, "").strip().lower()
    if not val:
        return default
    return val in ("1", "true", "yes", "on")


def get_env_list(name: str, default: list[str] | None = None) -> list[str]:
    val = os.environ.get(name, "").strip()
    if not val:
        return list(default) if default is not None else []
    return [item.strip() for item in val.split(",") if item.strip()]


def derive_ratelimit_redis_url(redis_url: str) -> str:
    """Return a Redis URL pointing to a separate DB index for rate limiting."""
    parsed = urlparse(redis_url)
    if parsed.scheme == "unix":  # one socket = one database; the "mm:rl" key prefix keeps the keys apart
        return redis_url
    path = (parsed.path or "").lstrip("/")
    try:
        current_db = int(path) if path else 0
    except ValueError:
        current_db = 0
    next_db = (current_db + 1) % 16
    if next_db == current_db:
        next_db = 2
    return urlunparse(parsed._replace(path=f"/{next_db}"))
