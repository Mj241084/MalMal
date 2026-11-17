"""Publishing rules and gallery bookkeeping shared by the panel and the admin (docs/09 module 4)."""

from __future__ import annotations


def publish_checks(product) -> tuple[list[str], list[str]]:
    """(errors, warnings). An error blocks activation; a warning only informs."""
    errors: list[str] = []
    warnings: list[str] = []
    if not (product.title or "").strip():
        errors.append("عنوان محصول خالی است")
    if not product.category_id:
        errors.append("دسته‌بندی انتخاب نشده است")
    prices = product.variants.filter(is_active=True).values_list("price", flat=True)
    if not any(price > 0 for price in prices):
        errors.append("دست‌کم یک تنوع فعال با قیمت بیشتر از صفر لازم است")
    if not product.images.exists():
        warnings.append("محصول تصویر ندارد")
    if not (product.description or "").strip():
        warnings.append("توضیحات خالی است")
    if not product.brand_id:
        warnings.append("برند انتخاب نشده است")
    return errors, warnings


def sync_main_image(product, *, skip_pk: int | None = None) -> bool:
    """D40: the main image is always the first one by order. True when the product row changed.

    `skip_pk` is an image about to be deleted: the product must stop pointing at it first, otherwise
    SET_NULL would change the row behind the tracking and the list cache would stay stale.
    """
    images = product.images.order_by("sort", "pk")
    if skip_pk is not None:
        images = images.exclude(pk=skip_pk)
    first = images.first()
    if product.main_image_id == (first.pk if first else None):
        return False
    product.main_image = first
    product.save(update_fields=["main_image", "updated_at"])
    return True
