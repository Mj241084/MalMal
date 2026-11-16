"""Catalog models: brands, category tree, products, variants, specs, stock ledger."""

from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse

from apps.catalog.constants import (
    CATEGORY_STRUCTURAL,
    LEVEL_DETAIL,
    LEVEL_LIST,
    TRACKED_DETAIL,
    TRACKED_LIST,
    VARIANT_DETAIL_FIELDS,
)
from apps.core.models import TimeStampedModel


def _list_snapshot(product) -> tuple:
    """Aggregate fields that make a product move between LIST-level caches."""
    return (product.min_price, product.max_price, product.compare_at_min, product.discount_pct, product.in_stock)


class Brand(TimeStampedModel):
    """Manufacturer / brand with search aliases (fa + en)."""

    name_fa = models.CharField(max_length=120, verbose_name="نام فارسی")
    name_en = models.CharField(max_length=120, blank=True, verbose_name="نام لاتین")
    slug = models.SlugField(max_length=140, unique=True, allow_unicode=True, verbose_name="نشانی")
    logo = models.ImageField(upload_to="brands/", blank=True, verbose_name="لوگو")
    aliases = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="نام‌های دیگر",
        help_text="با کاما جدا کنید؛ برای جستجو استفاده می‌شود (مثلاً «سامسونگ، Samsung»).",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"
        ordering = ["name_fa"]

    def __str__(self) -> str:
        return self.name_fa

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            from apps.catalog.utils import unique_slug

            self.slug = unique_slug(self, self.name_fa or self.name_en)
        super().save(*args, **kwargs)

    def alias_list(self) -> list[str]:
        return [part.strip() for part in (self.aliases or "").split(",") if part.strip()]


class CategoryQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Category(TimeStampedModel):
    """Category tree stored as a materialized path (``"1/5/12/"``)."""

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
        verbose_name="دسته والد",
    )
    name = models.CharField(max_length=160, verbose_name="نام")
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True, verbose_name="نشانی")
    logo = models.ImageField(upload_to="categories/", blank=True, verbose_name="لوگو")
    description = models.TextField(blank=True, verbose_name="توضیح")
    path = models.CharField(max_length=400, blank=True, db_index=True, verbose_name="مسیر")
    depth = models.PositiveSmallIntegerField(default=0, verbose_name="عمق")
    is_featured = models.BooleanField(default=False, verbose_name="دسته برتر")
    featured_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب برتر")
    show_in_menu = models.BooleanField(default=True, verbose_name="نمایش در منو")
    menu_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب منو")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    spec_inherit = models.BooleanField(default=True, verbose_name="ارث‌بری مشخصات از والد")
    rev = models.PositiveIntegerField(default=0, verbose_name="نسخه")
    subtree_rev = models.PositiveIntegerField(default=0, verbose_name="نسخه زیردرخت")

    objects = CategoryQuerySet.as_manager()

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ["path"]
        indexes = [
            models.Index(fields=["path"], name="cat_path_idx"),
            models.Index(fields=["parent", "menu_order"], name="cat_parent_menu_idx"),
            models.Index(fields=["is_featured", "featured_order"], name="cat_featured_idx"),
        ]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("catalog:category", args=[self.pk, self.slug])

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        super().clean()
        if self.pk and self.parent_id and self.path and self.parent.path.startswith(self.path):
            raise ValidationError({"parent": "دسته نمی‌تواند زیرمجموعه‌ی خودش باشد."})

    # --- tree helpers ------------------------------------------------------

    def ancestors(self) -> list[Category]:
        from apps.catalog.tree import ancestor_ids

        ids = ancestor_ids(self.path)[:-1]
        if not ids:
            return []
        found = {category.pk: category for category in Category.objects.filter(pk__in=ids)}
        return [found[pk] for pk in ids if pk in found]

    def descendants(self):
        from apps.catalog.tree import subtree_upper_bound

        if not self.path:
            return Category.objects.none()
        return Category.objects.filter(path__gte=self.path, path__lt=subtree_upper_bound(self.path))

    # --- tracking ----------------------------------------------------------

    def _snapshot_tracked(self) -> None:
        # Read from __dict__ so deferred (only()/defer()) instances never trigger a refresh.
        self._tracked_snapshot = {field: self.__dict__.get(field) for field in CATEGORY_STRUCTURAL}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._snapshot_tracked()

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._snapshot_tracked()
        return instance

    def save(self, *args, **kwargs) -> None:
        from apps.catalog.cache import invalidate_category
        from apps.catalog.tree import compute_path, depth_of, move_subtree

        previous = getattr(self, "_tracked_snapshot", {})
        old_path = None
        if self.pk and not self._state.adding:
            old_path = Category.objects.filter(pk=self.pk).values_list("path", flat=True).first()

        if not self.slug:
            from apps.catalog.utils import unique_slug

            self.slug = unique_slug(self, self.name)

        super().save(*args, **kwargs)

        new_path = compute_path(self)
        if new_path != self.path:
            self.path = new_path
            self.depth = depth_of(new_path)
            Category.objects.filter(pk=self.pk).update(path=self.path, depth=self.depth)

        if old_path and old_path != self.path:
            move_subtree(self, old_path)

        changed = {field for field in CATEGORY_STRUCTURAL if previous.get(field) != self.__dict__.get(field)}
        moved = bool(old_path and old_path != self.path)
        self._snapshot_tracked()

        if changed or moved:
            category_id = self.pk
            moved_from = old_path if moved else None
            transaction.on_commit(lambda: invalidate_category(category_id, moved_from))


class ProductQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Product.STATUS_ACTIVE)

    def with_list_relations(self):
        return self.select_related("brand", "category", "main_image")

    def update_tracked(self, **fields):
        """``update()`` replacement that keeps cache revisions and the FTS index honest."""
        objects = list(self)
        for obj in objects:
            for field, value in fields.items():
                setattr(obj, field, value)
            obj.save()
        return len(objects)

    def bulk_update_tracked(self, objs, fields):
        """Bulk variant of ``update_tracked``; each row is saved through the tracking path."""
        count = 0
        for obj in objs:
            obj.save(update_fields=list(fields))
            count += 1
        return count


class Product(TimeStampedModel):
    """Sellable product. Price and stock aggregates are denormalized from variants."""

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "پیش‌نویس"),
        (STATUS_ACTIVE, "فعال"),
        (STATUS_ARCHIVED, "بایگانی"),
    ]

    title = models.CharField(max_length=255, verbose_name="عنوان")
    slug = models.SlugField(max_length=280, unique=True, allow_unicode=True, verbose_name="نشانی")
    brand = models.ForeignKey(
        Brand, null=True, blank=True, on_delete=models.SET_NULL, related_name="products", verbose_name="برند"
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="دسته‌بندی")
    category_path = models.CharField(max_length=400, blank=True, db_index=True, verbose_name="مسیر دسته")

    short_description = models.TextField(blank=True, verbose_name="توضیح کوتاه")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    warranty_text = models.CharField(max_length=200, blank=True, verbose_name="گارانتی")

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name="وضعیت")

    min_price = models.BigIntegerField(default=0, verbose_name="کمترین قیمت")
    max_price = models.BigIntegerField(default=0, verbose_name="بیشترین قیمت")
    compare_at_min = models.BigIntegerField(null=True, blank=True, verbose_name="کمترین قیمت قبل از تخفیف")
    discount_pct = models.PositiveSmallIntegerField(default=0, verbose_name="درصد تخفیف")
    in_stock = models.BooleanField(default=False, verbose_name="موجود")
    total_stock = models.IntegerField(default=0, verbose_name="جمع موجودی")

    like_count = models.PositiveIntegerField(default=0, verbose_name="تعداد لایک")
    review_count = models.PositiveIntegerField(default=0, verbose_name="تعداد نظر")
    rating_sum = models.PositiveIntegerField(default=0, verbose_name="جمع امتیازها")
    rating_avg = models.DecimalField(
        max_digits=2, decimal_places=1, default=Decimal("0.0"), verbose_name="میانگین امتیاز"
    )
    purchase_count_30d = models.PositiveIntegerField(default=0, verbose_name="خرید ۳۰ روز")
    purchase_count_total = models.PositiveIntegerField(default=0, verbose_name="خرید کل")
    view_count = models.PositiveIntegerField(default=0, verbose_name="بازدید")

    rev = models.PositiveIntegerField(default=0, verbose_name="نسخه")
    search_text = models.TextField(blank=True, verbose_name="متن جستجو")

    seo_title = models.CharField(max_length=200, blank=True, verbose_name="عنوان سئو")
    seo_description = models.CharField(max_length=320, blank=True, verbose_name="توضیحات سئو")
    main_image = models.ForeignKey(
        "catalog.ProductImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="تصویر اصلی",
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category_path"], name="prod_cat_path_idx"),
            models.Index(fields=["status", "-created_at"], name="prod_status_created_idx"),
            models.Index(fields=["status", "min_price"], name="prod_status_price_idx"),
            models.Index(fields=["status", "-purchase_count_30d"], name="prod_status_purchase_idx"),
            models.Index(fields=["status", "-like_count"], name="prod_status_like_idx"),
            models.Index(fields=["brand", "status"], name="prod_brand_status_idx"),
            models.Index(fields=["status", "-discount_pct"], name="prod_status_discount_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("catalog:product", args=[self.pk, self.slug])

    @property
    def is_active(self) -> bool:
        return self.status == self.STATUS_ACTIVE

    @property
    def is_discounted(self) -> bool:
        return bool(self.compare_at_min and self.compare_at_min > self.min_price)

    # --- aggregates --------------------------------------------------------

    def refresh_aggregates(self, *, save: bool = True) -> bool:
        """Recompute price/stock aggregates from active variants. Saves only on change."""
        rows = list(self.variants.filter(is_active=True).values_list("price", "compare_at_price", "stock"))
        min_price = min((r[0] for r in rows), default=0)
        max_price = max((r[0] for r in rows), default=0)
        total_stock = sum(r[2] for r in rows)
        # The discount badge belongs to the cheapest variant, not to any variant that happens to be discounted.
        cheapest_compare = max((r[1] for r in rows if r[0] == min_price and r[1]), default=None)
        compare_at_min = cheapest_compare if cheapest_compare and cheapest_compare > min_price else None

        discount_pct = 0
        if compare_at_min:
            discount_pct = round((compare_at_min - min_price) * 100 / compare_at_min)

        changed = (
            self.min_price != min_price
            or self.max_price != max_price
            or self.compare_at_min != compare_at_min
            or self.discount_pct != discount_pct
            or self.in_stock != (total_stock > 0)
            or self.total_stock != total_stock
        )
        if not changed:
            return False
        if not save:
            return True

        self.min_price = min_price
        self.max_price = max_price
        self.compare_at_min = compare_at_min
        self.discount_pct = discount_pct
        self.in_stock = total_stock > 0
        self.total_stock = total_stock
        self.save(
            update_fields=[
                "min_price",
                "max_price",
                "compare_at_min",
                "discount_pct",
                "in_stock",
                "total_stock",
                "updated_at",
            ]
        )
        return True

    # --- tracking ----------------------------------------------------------

    def _snapshot_tracked(self) -> None:
        # Read from __dict__ so deferred (only()/defer()) instances never trigger a refresh.
        fields = TRACKED_LIST | TRACKED_DETAIL
        self._tracked_snapshot = {field: self.__dict__.get(field) for field in fields}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._snapshot_tracked()

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._snapshot_tracked()
        return instance

    def save(self, *args, **kwargs) -> None:
        from apps.catalog.cache import invalidate_product
        from apps.catalog.search_text import build_search_text

        previous = getattr(self, "_tracked_snapshot", {})
        changed = {field for field in TRACKED_LIST | TRACKED_DETAIL if previous.get(field) != self.__dict__.get(field)}

        if not self.slug:
            from apps.catalog.utils import unique_slug

            self.slug = unique_slug(self, self.title)
            changed.add("slug")

        if changed & TRACKED_LIST:
            self.search_text = build_search_text(self)
            changed.add("search_text")

        path_changed = False
        if self.category_id:
            category_path = Category.objects.filter(pk=self.category_id).values_list("path", flat=True).first()
            if category_path and category_path != self.category_path:
                self.category_path = category_path
                path_changed = True

        if kwargs.get("update_fields") is not None:
            # Computed columns are written above, so a partial save must carry them along or the row goes stale.
            touched = {"slug"} & changed
            if "search_text" in changed:
                touched.add("search_text")
            if path_changed:
                touched.add("category_path")
            kwargs["update_fields"] = [*kwargs["update_fields"], *(touched - set(kwargs["update_fields"]))]

        super().save(*args, **kwargs)
        self._snapshot_tracked()

        level = None
        if changed & TRACKED_LIST:
            level = LEVEL_LIST
        elif changed & TRACKED_DETAIL:
            level = LEVEL_DETAIL

        if level:
            product_id = self.pk
            old_category_id = previous.get("category_id")
            new_category_id = self.category_id
            transaction.on_commit(lambda: invalidate_product(product_id, level, old_category_id, new_category_id))


class Variant(TimeStampedModel):
    """Purchasable SKU. Cart and orders reference variants, never products (D16)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants", verbose_name="محصول")
    sku = models.CharField(max_length=64, unique=True, verbose_name="کد کالا (SKU)")
    title = models.CharField(max_length=200, verbose_name="عنوان")
    options = models.JSONField(default=dict, blank=True, verbose_name="گزینه‌ها")
    price = models.BigIntegerField(validators=[MinValueValidator(0)], verbose_name="قیمت (تومان)")
    compare_at_price = models.BigIntegerField(null=True, blank=True, verbose_name="قیمت قبل از تخفیف")
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="موجودی")
    max_per_order = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=None,
        verbose_name="حداکثر تعداد در هر سفارش",
        help_text="خالی یا ۰ = تا سقف موجودی.",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "تنوع (variant)"
        verbose_name_plural = "تنوع‌ها"
        ordering = ["sort", "pk"]
        indexes = [
            models.Index(fields=["product", "is_active"], name="variant_product_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.product.title} — {self.title}"

    @property
    def max_orderable(self) -> int:
        """Largest quantity one customer may order (docs/02 D29).

        Empty/0 ``max_per_order`` means "as many as stock allows"; a zero stock
        always means zero, regardless of the cap.
        """
        if self.stock <= 0:
            return 0
        if not self.max_per_order:
            return self.stock
        return min(self.stock, self.max_per_order)

    @property
    def discount_pct(self) -> int:
        if self.compare_at_price and self.compare_at_price > self.price:
            return round((self.compare_at_price - self.price) * 100 / self.compare_at_price)
        return 0

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if self.compare_at_price is not None and self.compare_at_price < self.price:
            raise ValidationError({"compare_at_price": "قیمت قبل از تخفیف نمی‌تواند کمتر از قیمت فروش باشد."})
        if self.max_per_order is not None and self.max_per_order < 0:
            raise ValidationError({"max_per_order": "حداکثر تعداد نمی‌تواند منفی باشد."})

    def save(self, *args, **kwargs) -> None:
        previous = {}
        if self.pk and not self._state.adding:
            previous = Variant.objects.filter(pk=self.pk).values(*VARIANT_DETAIL_FIELDS, "stock").first() or {}

        super().save(*args, **kwargs)

        product = self.product
        before = _list_snapshot(product)
        product.refresh_aggregates()
        list_moved = before != _list_snapshot(product)  # Product.save already did the LIST invalidation

        if previous.get("stock") == 0 and self.stock > 0 and self.is_active:
            from apps.engagement import back_in_stock

            variant_id = self.pk
            transaction.on_commit(lambda: back_in_stock.mark_due(variant_id))

        changed = {field for field in VARIANT_DETAIL_FIELDS if previous.get(field) != getattr(self, field)}
        if changed and not list_moved:
            from apps.catalog.cache import invalidate_product

            product_id = self.product_id
            transaction.on_commit(lambda: invalidate_product(product_id, LEVEL_DETAIL))

    def delete(self, *args, **kwargs):
        from apps.catalog.cache import touch_product

        product = self.product
        result = super().delete(*args, **kwargs)
        product.refresh_aggregates()
        transaction.on_commit(lambda: touch_product(product.pk, LEVEL_DETAIL), robust=True)
        return result


class ProductImage(TimeStampedModel):
    """Product gallery image with generated WebP renditions."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images", verbose_name="محصول")
    variant = models.ForeignKey(
        Variant, null=True, blank=True, on_delete=models.SET_NULL, related_name="images", verbose_name="تنوع"
    )
    image = models.ImageField(upload_to="products/", verbose_name="تصویر")
    alt = models.CharField(max_length=200, blank=True, verbose_name="متن جایگزین")
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    widths = models.JSONField(default=dict, blank=True, verbose_name="اندازه‌های ساخته‌شده")

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ["sort", "pk"]

    def __str__(self) -> str:
        return self.alt or f"تصویر {self.product_id}"

    def save(self, *args, **kwargs) -> None:
        if self.image and not getattr(self.image, "_committed", True):
            self.widths = {}  # a new file replaced the old one: renditions must be rebuilt
        generating = bool(self.image) and not self.widths
        super().save(*args, **kwargs)
        if generating:
            from apps.catalog.images import generate_webp_sizes

            try:
                self.widths = generate_webp_sizes(self.image)
            except Exception:  # pragma: no cover - a bad file must not block the upload
                import logging

                logging.getLogger(__name__).exception("WebP rendition generation failed for image %s", self.pk)
                self.widths = {}
            else:
                super().save(update_fields=["widths"])

        from apps.catalog.cache import touch_product

        product_id = self.product_id
        transaction.on_commit(lambda: touch_product(product_id, LEVEL_DETAIL), robust=True)

    def delete(self, *args, **kwargs):
        from apps.catalog.cache import touch_product

        product_id = self.product_id
        result = super().delete(*args, **kwargs)
        transaction.on_commit(lambda: touch_product(product_id, LEVEL_DETAIL), robust=True)
        return result

    def srcset(self) -> str:
        from django.conf import settings

        if not self.widths:
            return ""
        return ", ".join(
            f"{settings.MEDIA_URL}{path} {width}w"
            for width, path in sorted(self.widths.items(), key=lambda kv: int(kv[0]))
        )

    def largest(self) -> str:
        from django.conf import settings

        if not self.widths:
            return self.image.url if self.image else ""
        width = max(self.widths, key=int)
        return f"{settings.MEDIA_URL}{self.widths[width]}"


class SpecAttribute(TimeStampedModel):
    """Specification attribute defined on a category and inherited by its subtree."""

    TYPE_TEXT = "text"
    TYPE_NUMBER = "number"
    TYPE_BOOL = "bool"
    TYPE_CHOICE = "choice"
    TYPE_CHOICES = [
        (TYPE_TEXT, "متنی"),
        (TYPE_NUMBER, "عددی"),
        (TYPE_BOOL, "بله/خیر"),
        (TYPE_CHOICE, "انتخابی"),
    ]

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="spec_attributes", verbose_name="دسته‌بندی"
    )
    name = models.CharField(max_length=120, verbose_name="نام")
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_TEXT, verbose_name="نوع")
    unit = models.CharField(max_length=32, blank=True, verbose_name="واحد")
    is_filterable = models.BooleanField(default=False, verbose_name="قابل فیلتر")
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "مشخصه فنی"
        verbose_name_plural = "مشخصات فنی"
        ordering = ["sort", "pk"]

    def __str__(self) -> str:
        return f"{self.name} ({self.category.name})"

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        from apps.catalog.cache import invalidate_category

        category_id = self.category_id
        transaction.on_commit(lambda: invalidate_category(category_id), robust=True)

    def delete(self, *args, **kwargs):
        from apps.catalog.cache import invalidate_category

        category_id = self.category_id
        result = super().delete(*args, **kwargs)
        transaction.on_commit(lambda: invalidate_category(category_id), robust=True)
        return result


class ProductSpecValue(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="spec_values", verbose_name="محصول")
    attribute = models.ForeignKey(SpecAttribute, on_delete=models.CASCADE, related_name="values", verbose_name="مشخصه")
    value_text = models.CharField(max_length=255, blank=True, verbose_name="مقدار متنی")
    value_number = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="مقدار عددی"
    )

    class Meta:
        verbose_name = "مقدار مشخصه"
        verbose_name_plural = "مقادیر مشخصات"
        constraints = [
            models.UniqueConstraint(fields=["product", "attribute"], name="uniq_product_attribute"),
        ]
        indexes = [
            models.Index(fields=["attribute", "value_number"], name="spec_value_number_idx"),
            models.Index(fields=["attribute", "value_text"], name="spec_value_text_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.attribute.name}: {self.value_text or self.value_number}"

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        from apps.catalog.cache import touch_product

        product_id = self.product_id
        transaction.on_commit(lambda: touch_product(product_id, LEVEL_LIST), robust=True)

    def delete(self, *args, **kwargs):
        from apps.catalog.cache import touch_product

        product_id = self.product_id
        result = super().delete(*args, **kwargs)
        transaction.on_commit(lambda: touch_product(product_id, LEVEL_LIST), robust=True)
        return result


class StockMovement(TimeStampedModel):
    """Append-only stock ledger. Never update or delete rows."""

    REASON_ORDER = "order"
    REASON_CANCEL = "cancel"
    REASON_EXPIRE = "expire"
    REASON_MANUAL = "manual"
    REASON_RETURN = "return"
    REASON_CHOICES = [
        (REASON_ORDER, "سفارش"),
        (REASON_CANCEL, "لغو"),
        (REASON_EXPIRE, "انقضای رزرو"),
        (REASON_MANUAL, "دستی"),
        (REASON_RETURN, "مرجوعی"),
    ]

    variant = models.ForeignKey(Variant, on_delete=models.PROTECT, related_name="stock_movements", verbose_name="تنوع")
    delta = models.IntegerField(verbose_name="تغییر")
    reason = models.CharField(max_length=16, choices=REASON_CHOICES, verbose_name="دلیل")
    order_item_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name="قلم سفارش",
        help_text="کلید قلم سفارش؛ در فاز P3 به کلید خارجی تبدیل می‌شود.",
    )
    note = models.CharField(max_length=255, blank=True, verbose_name="یادداشت")

    class Meta:
        verbose_name = "گردش موجودی"
        verbose_name_plural = "گردش موجودی"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["variant", "-created_at"], name="stock_move_variant_idx")]

    def __str__(self) -> str:
        return f"{self.variant_id}: {self.delta:+d} ({self.reason})"

    def save(self, *args, **kwargs) -> None:
        if not self._state.adding:
            raise ValueError("StockMovement is append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - guard
        raise ValueError("StockMovement is append-only.")
