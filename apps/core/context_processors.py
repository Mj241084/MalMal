"""Template context processors for shared shell data."""

from __future__ import annotations

from django.conf import settings

from apps.core.models import FooterLink, SiteSettings

# Sample top-level categories used in the P0 header shell before catalog lands in P1.
_SAMPLE_CATEGORIES = [
    {"name": "یخچال و فریزر", "slug": "refrigerator", "children": ["ساید بای ساید", "دوقلو", "کمبی"]},
    {"name": "ماشین لباسشویی", "slug": "washing-machine", "children": ["اتوماتیک", "خشک‌کن دار"]},
    {"name": "ماشین ظرفشویی", "slug": "dishwasher", "children": ["مبله", "رومیزی"]},
    {"name": "جاروبرقی و نظافت", "slug": "vacuum", "children": ["کیسه‌ای", "مخزن‌دار", "بخارشو"]},
    {"name": "لوازم آشپزخانه", "slug": "kitchen", "children": ["چای‌ساز", "قهوه‌ساز", "غذاساز"]},
    {"name": "تهویه مطبوع", "slug": "climate", "children": ["کولر گازی", "تصفیه هوا"]},
]


def site_context(request) -> dict:
    return {
        "site_settings": SiteSettings.get_solo(),
        "footer_link_groups": FooterLink.get_grouped(),
        "site_url": settings.SITE_URL,
        "nav_categories": _SAMPLE_CATEGORIES,
    }
