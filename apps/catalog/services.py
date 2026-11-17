"""Catalog write rules shared by the panel and the admin (docs/09 modules 4 to 6).

Never imports the panel (D35). Every write goes through save()/delete(), so cache revisions, the FTS row and the
aggregates stay honest. Partial saves use update_fields on purpose: a full save of a stale instance would overwrite
`stock` or the counters that other requests changed in the meantime.
"""

from __future__ import annotations

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max

from apps.catalog import publishing, stock
from apps.catalog.cache import invalidate_category, invalidate_menu, touch_product
from apps.catalog.constants import LEVEL_DETAIL
from apps.catalog.images import validate_upload
from apps.catalog.models import (
    Product,
    ProductImage,
    ProductSpecValue,
    SpecAttribute,
    StockMovement,
    Variant,
)
from apps.core.jalali import to_fa_digits
from apps.core.text import normalize_fa

MAX_IMAGES = 12
IMAGE_MAX_BYTES = 5 * 1024 * 1024
MIN_SIDE = 800
VARIANT_FIELDS = ["title", "sku", "options", "price", "compare_at_price", "max_per_order", "is_active", "updated_at"]
_PRODUCT_COLUMNS = {field.name for field in Product._meta.concrete_fields}


class CatalogError(Exception):
    """A refusal whose message is safe to show to staff."""


class PublishError(CatalogError):
    def __init__(self, errors: list[str]):
        super().__init__("؛ ".join(errors))
        self.errors = errors


def _note(reason: str, by) -> str:
    return f"{reason} — {by.mobile}" if by is not None else reason


def _guard_active(product: Product) -> None:
    """An active product must always keep a sellable variant."""
    if product.status == Product.STATUS_ACTIVE:
        errors, _ = publishing.publish_checks(product)
        if errors:
            raise PublishError(errors)


# --- products --------------------------------------------------------------


def create_draft(title: str, category, brand=None) -> Product:
    return Product.objects.create(title=title, category=category, brand=brand, status=Product.STATUS_DRAFT)


def save_basics(form) -> bool:
    """ModelForm save that writes only the changed columns (counters and aggregates stay untouched)."""
    fields = [name for name in form.changed_data if name in _PRODUCT_COLUMNS]
    if not fields:
        return False
    product = form.save(commit=False)
    product.save(update_fields=[*fields, "updated_at"])
    return True


def set_status(product: Product, status: str) -> None:
    if status == product.status:
        return
    if status == Product.STATUS_ACTIVE:
        errors, _ = publishing.publish_checks(product)
        if errors:
            raise PublishError(errors)
    product.status = status
    product.save(update_fields=["status", "updated_at"])


def delete_block_reason(product: Product) -> str:
    from apps.orders.models import OrderItem  # lazy: orders imports catalog

    if product.status != Product.STATUS_DRAFT:
        return "فقط پیش‌نویس حذف می‌شود؛ محصول فعال را بایگانی کنید"
    if product.purchase_count_total or OrderItem.objects.filter(product=product).exists():
        return "این محصول سابقه‌ی سفارش دارد؛ بایگانی کنید"
    if StockMovement.objects.filter(variant__product=product).exists():
        return "این محصول گردش موجودی دارد؛ بایگانی کنید"
    return ""


def delete_product(product: Product) -> None:
    reason = delete_block_reason(product)
    if reason:
        raise CatalogError(reason)
    with transaction.atomic():
        product.delete()  # the search app drops the FTS row on post_delete


# --- variants --------------------------------------------------------------


def suggest_sku(product: Product) -> str:
    base, sku, n = f"SKU-{product.pk}", f"SKU-{product.pk}", 2
    while Variant.objects.filter(sku=sku).exists():
        sku, n = f"{base}-{n}", n + 1
    return sku


def variant_initial(variant: Variant) -> dict:
    options = variant.options if isinstance(variant.options, dict) else {}
    return {
        "title": variant.title,
        "sku": variant.sku,
        "price": variant.price,
        "compare_at_price": variant.compare_at_price,
        "max_per_order": variant.max_per_order,
        "is_active": variant.is_active,
        "color": options.get("color", ""),
        "model": options.get("model", ""),
    }


def new_variant_initial(product: Product) -> dict:
    return {
        "title": "" if product.variants.exists() else "پیش‌فرض",
        "sku": suggest_sku(product),
        "is_active": True,
    }


def save_variant(product: Product, form, *, variant: Variant | None = None, by=None) -> Variant:
    """Create or edit one variant. A new variant's opening stock goes through the ledger (D43)."""
    creating = variant is None
    with transaction.atomic():
        if creating:
            top = product.variants.aggregate(top=Max("sort"))["top"]
            variant = Variant(product=product, sort=0 if top is None else top + 1)
        else:
            variant.refresh_from_db(fields=["stock"])  # the write lock is held: no false «back in stock»
        form.apply_to(variant)
        if creating:
            variant.save()
            quantity = form.cleaned_data.get("initial_stock") or 0
            if quantity:
                stock.increment(
                    variant.pk, quantity, reason=StockMovement.REASON_MANUAL, note=_note("موجودی اولیه", by)
                )
                stock.refresh_products([product.pk])
        else:
            variant.save(update_fields=VARIANT_FIELDS)
        _guard_active(product)
    return variant


def apply_quick_prices(variants: list[Variant], form) -> None:
    with transaction.atomic():
        for variant in variants:
            price = form.cleaned_data[f"price_{variant.pk}"]
            compare = form.cleaned_data[f"compare_{variant.pk}"]
            if (variant.price, variant.compare_at_price) != (price, compare):
                variant.refresh_from_db(fields=["stock"])
                variant.price, variant.compare_at_price = price, compare
                variant.save(update_fields=["price", "compare_at_price", "updated_at"])


def delete_variant(variant: Variant) -> None:
    if variant.stock_movements.exists():
        raise CatalogError("این تنوع گردش موجودی دارد و حذف نمی‌شود؛ غیرفعالش کنید")
    product = variant.product
    with transaction.atomic():
        variant.delete()
        _guard_active(product)  # raising rolls the delete back


def adjust_stock(variant_id: int, delta: int, *, reason: str, by, expected_stock: int | None = None) -> int:
    """Staff stock change (D43). Raises stock.StockConflict. Returns the new stock."""
    with transaction.atomic():
        return stock.adjust_manual(variant_id, delta, note=_note(reason, by), expected_stock=expected_stock)


# --- images ----------------------------------------------------------------


def add_images(product: Product, files) -> tuple[int, list[str], list[str]]:
    """Validate and store uploads. Returns (added, errors, warnings). The main image follows the first one (D40)."""
    added, errors, warnings = 0, [], []
    room = MAX_IMAGES - product.images.count()
    for file in files:
        name = f"«{file.name[:40]}»"
        if room <= 0:
            errors.append(f"سقف {to_fa_digits(MAX_IMAGES)} تصویر پر است")
            break
        try:
            extension, width, height = validate_upload(file, max_bytes=IMAGE_MAX_BYTES, label="تصویر")
        except ValidationError as exc:
            errors.append(f"{name}: {exc.messages[0]}")
            continue
        top = product.images.aggregate(top=Max("sort"))["top"]
        file.name = f"{uuid4().hex[:12]}.{extension}"
        ProductImage.objects.create(product=product, image=file, sort=0 if top is None else top + 1)
        if min(width, height) < MIN_SIDE:
            warnings.append(f"{name}: کمتر از {to_fa_digits(MIN_SIDE)} پیکسل است و در بزرگ‌نمایی نرم دیده می‌شود")
        added += 1
        room -= 1
    if added:
        publishing.sync_main_image(product)
    return added, errors, warnings


def set_image_alt(image: ProductImage, alt: str) -> None:
    image.alt = normalize_fa(alt)[:200]
    image.save(update_fields=["alt", "updated_at"])


def delete_image(product: Product, image: ProductImage) -> None:
    with transaction.atomic():
        publishing.sync_main_image(product, skip_pk=image.pk)  # first stop pointing at it (D40)
        image.delete()


# --- specifications --------------------------------------------------------


def spec_suggestions(attributes) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    for attribute in attributes:
        if attribute.type not in (SpecAttribute.TYPE_TEXT, SpecAttribute.TYPE_CHOICE):
            continue
        rows = (
            ProductSpecValue.objects.filter(attribute=attribute)
            .exclude(value_text="")
            .values("value_text")
            .annotate(n=Count("pk"))
            .order_by("-n", "value_text")[:8]
        )
        result[attribute.pk] = [row["value_text"] for row in rows]
    return result


def save_specs(product: Product, values: dict, desired: dict) -> int:
    """Write only what changed (every ProductSpecValue save bumps the product rev). Returns the number of changes."""
    changed = 0
    with transaction.atomic():
        for attribute_id, wanted in desired.items():
            current = values.get(attribute_id)
            if wanted is None:
                if current is not None:
                    current.delete()
                    changed += 1
                continue
            text, number = wanted
            if current is None:
                ProductSpecValue.objects.create(
                    product=product, attribute_id=attribute_id, value_text=text, value_number=number
                )
                changed += 1
            elif (current.value_text, current.value_number) != (text, number):
                current.value_text, current.value_number = text, number
                current.save()
                changed += 1
    return changed


def save_spec_attribute(form, category) -> SpecAttribute:
    with transaction.atomic():
        attribute = form.save(commit=False)
        creating = attribute.pk is None
        attribute.category = category
        attribute.save()
        if not creating and {"name", "unit"} & set(form.changed_data):
            ids = list(attribute.values.values_list("product_id", flat=True).distinct())
            transaction.on_commit(lambda: [touch_product(i, LEVEL_DETAIL) for i in ids], robust=True)
    return attribute


def delete_spec_attribute(attribute: SpecAttribute) -> None:
    ids = list(attribute.values.values_list("product_id", flat=True).distinct())
    with transaction.atomic():
        attribute.delete()  # cascades the values without calling their delete(): bump the products ourselves
        transaction.on_commit(lambda: [touch_product(i) for i in ids], robust=True)


# --- categories and brands -------------------------------------------------


def category_delete_block(category) -> str:
    if category.children.exists():
        return "این دسته زیرمجموعه دارد؛ ابتدا آن‌ها را جابه‌جا یا حذف کنید"
    if category.products.exists():
        return "این دسته محصول دارد؛ به‌جای حذف، غیرفعالش کنید"
    return ""


def delete_category(category) -> None:
    reason = category_delete_block(category)
    if reason:
        raise CatalogError(reason)
    parent_id = category.parent_id
    with transaction.atomic():
        category.delete()
        transaction.on_commit(lambda: invalidate_category(parent_id) if parent_id else invalidate_menu(), robust=True)
