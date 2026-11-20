from pathlib import Path

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.core import social

BY_FIELD = {network.field: network for network in social.NETWORKS}


@pytest.mark.parametrize(
    ("field", "raw", "expected"),
    [
        ("instagram_url", "instagram.com/malmal", "https://instagram.com/malmal"),
        ("instagram_url", "http://www.instagram.com/malmal/", "https://www.instagram.com/malmal/"),
        ("telegram_url", " t.me/malmal ", "https://t.me/malmal"),
        ("x_url", "", ""),
    ],
)
def test_normalize_completes_and_upgrades_to_https(field, raw, expected):
    assert social.normalize(BY_FIELD[field], raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "javascript:alert(1)",
        "ftp://instagram.com/x",
        "https://evil.example/instagram.com",
        "https://instagram.com@evil.example/",
        "https://instagram.com.evil.example/",
        "https://notinstagram.com/x",
        "https://insta gram.com",
    ],
)
def test_normalize_refuses_foreign_or_unsafe_links(raw):
    with pytest.raises(ValidationError):
        social.normalize(BY_FIELD["instagram_url"], raw)


def test_every_network_has_its_icon_file():
    """A missing file would crash {% static %} under ManifestStaticFilesStorage in production."""
    folder = Path(settings.BASE_DIR) / "static" / social.ICON_DIR
    missing = [n.icon for n in social.NETWORKS if not (folder / n.icon).is_file()]
    assert not missing, missing
