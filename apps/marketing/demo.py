"""Obviously-fake marketing rows for development. Removed together with `seed_demo --clear`."""

from __future__ import annotations

import io

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw

from apps.catalog.models import Category, Product
from apps.marketing.models import Banner, Collection, CollectionItem

TONES = [(238, 233, 223), (247, 244, 238), (239, 233, 223)]
HERO_SIZES = ((1440, 480), (800, 600))
STRIP_SIZES = ((1440, 180), (800, 267))


def _image(width: int, height: int, label: str, index: int) -> ContentFile:
    image = Image.new("RGB", (width, height), TONES[index % len(TONES)])
    draw = ImageDraw.Draw(image)
    draw.rectangle([16, 16, width - 17, height - 17], outline=(190, 182, 170), width=2)
    draw.text((32, height - 40), f"DEMO {label}", fill=(120, 112, 100))
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=80)
    return ContentFile(buffer.getvalue())


def _banner(title: str, placement: str, sizes, index: int, **target) -> None:
    banner = Banner(
        title=f"نمونه — {title}", alt=f"نمونه {title}", placement=placement, sort=index, is_demo=True, **target
    )
    (dw, dh), (mw, mh) = sizes
    banner.image_desktop.save(f"demo-{placement}-{index}-d.webp", _image(dw, dh, title, index), save=False)
    banner.image_mobile.save(f"demo-{placement}-{index}-m.webp", _image(mw, mh, title, index), save=False)
    banner.save()


def seed_marketing() -> None:
    if Banner.objects.filter(is_demo=True).exists():
        return
    products = list(Product.objects.filter(is_demo=True, status=Product.STATUS_ACTIVE).order_by("pk"))
    roots = list(Category.objects.filter(is_demo=True, parent__isnull=True).order_by("menu_order"))

    manual = Collection.objects.create(title="نمونه: انتخاب فروشگاه", mode=Collection.MODE_MANUAL, is_demo=True)
    for position, product in enumerate(products[:6]):
        CollectionItem.objects.create(collection=manual, product=product, sort=position)
    rule = Collection.objects.create(
        title="نمونه: تخفیف‌دارها",
        mode=Collection.MODE_RULE,
        min_discount_pct=1,
        only_in_stock=True,
        sort_by="discount",
        is_demo=True,
    )

    hero = Banner.PLACEMENT_HERO
    _banner("اسلاید اول", hero, HERO_SIZES, 0, target_type=Banner.TARGET_COLLECTION, target_collection=manual)
    if roots:
        _banner("اسلاید دوم", hero, HERO_SIZES, 1, target_type=Banner.TARGET_CATEGORY, target_category=roots[0])
    _banner("اسلاید سوم", hero, HERO_SIZES, 2)
    _banner(
        "نوار", Banner.PLACEMENT_STRIP, STRIP_SIZES, 0, target_type=Banner.TARGET_COLLECTION, target_collection=rule
    )


def clear_marketing() -> None:
    Banner.objects.filter(is_demo=True).delete()
    Collection.objects.filter(is_demo=True).delete()
