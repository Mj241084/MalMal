"""Catalog forms of the panel (docs/09 modules 4 to 6). Digits are shown Persian and stored ASCII (D30)."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q
from django.utils.html import linebreaks
from django.utils.text import slugify

from apps.catalog.images import validate_upload
from apps.catalog.models import Brand, Category, Product, SpecAttribute, Variant
from apps.catalog.specs import number_text
from apps.catalog.tree import subtree_upper_bound
from apps.core.forms import FieldErrorAttrsMixin
from apps.core.html import sanitize_html
from apps.core.text import normalize_digits, normalize_fa
from apps.core.widgets import FaDigitsInput, FaTextarea, FaTextInput
from apps.panel.fields import FaIntegerField, TomanField

LOGO_MAX_BYTES = 2 * 1024 * 1024
SKU_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SEPARATORS = re.compile(r"[\s,٬،_]")
FILE_ATTRS = {"class": "file-input w-full", "accept": "image/png,image/jpeg,image/webp"}
CHECKBOX = {"class": "checkbox checkbox-sm"}


def category_label(category) -> str:
    return f"{'— ' * category.depth}{category.name}"


def multiline(text: str) -> str:
    """Normalize per line so paragraphs survive (normalize_fa collapses all whitespace)."""
    lines = [normalize_fa(line) for line in (text or "").splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def rich_text(value: str) -> str:
    """Product description: plain text becomes paragraphs, everything goes through the whitelist sanitizer."""
    text = (value or "").strip()
    if text and "<" not in text:
        text = linebreaks(text, autoescape=True)
    return sanitize_html(text)


def clean_slug_value(form, raw, max_length: int) -> str:
    raw = (raw or "").strip()
    if not raw:
        return form.instance.slug  # empty: keep the current one; the model builds a slug on first save
    slug = slugify(raw, allow_unicode=True)[:max_length]
    if not slug:
        raise ValidationError("نشانی معتبر نیست")
    return slug


# --- products ---------------------------------------------------------------


class ProductCreateForm(FieldErrorAttrsMixin, forms.Form):
    title = forms.CharField(
        label="عنوان", max_length=255, widget=FaTextInput(attrs={"class": "input w-full", "data-autofocus": "1"})
    )
    category = forms.ModelChoiceField(
        label="دسته‌بندی",
        queryset=Category.objects.none(),
        empty_label="انتخاب دسته",
        widget=forms.Select(attrs={"class": "select w-full"}),
    )
    brand = forms.ModelChoiceField(
        label="برند (اختیاری)",
        queryset=Brand.objects.none(),
        required=False,
        empty_label="بدون برند",
        widget=forms.Select(attrs={"class": "select w-full"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("path")
        self.fields["category"].label_from_instance = category_label
        self.fields["brand"].queryset = Brand.objects.filter(is_active=True).order_by("name_fa")

    def clean_title(self) -> str:
        return normalize_fa(self.cleaned_data["title"])


class ProductBasicsForm(FieldErrorAttrsMixin, forms.ModelForm):
    slug = forms.CharField(
        label="نشانی",
        required=False,
        max_length=280,
        widget=forms.TextInput(attrs={"class": "input w-full text-end latin", "dir": "ltr"}),
        help_text="خالی = ساخت خودکار از عنوان. نشانی قبلی با ریدایرکت ۳۰۱ به نشانی تازه می‌رود",
    )

    class Meta:
        model = Product
        fields = [
            "title",
            "category",
            "brand",
            "short_description",
            "description",
            "warranty_text",
            "slug",
            "seo_title",
            "seo_description",
        ]
        labels = {
            "title": "عنوان",
            "category": "دسته‌بندی",
            "brand": "برند",
            "short_description": "توضیح کوتاه",
            "description": "توضیحات",
            "warranty_text": "گارانتی",
            "seo_title": "عنوان سئو",
            "seo_description": "توضیحات سئو",
        }
        help_texts = {
            "description": "متن ساده پاراگراف می‌شود. HTML مجاز: p، br، ul، ol، li، strong، em، h2، h3، h4، a، blockquote",
        }
        widgets = {
            "title": FaTextInput(attrs={"class": "input w-full"}),
            "category": forms.Select(attrs={"class": "select w-full"}),
            "brand": forms.Select(attrs={"class": "select w-full"}),
            "short_description": FaTextarea(attrs={"class": "textarea w-full", "rows": 2}),
            "description": forms.Textarea(attrs={"class": "textarea w-full", "rows": 10}),
            "warranty_text": FaTextInput(attrs={"class": "input w-full"}),
            "seo_title": FaTextInput(attrs={"class": "input w-full"}),
            "seo_description": FaTextarea(attrs={"class": "textarea w-full", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        category, brand = self.fields["category"], self.fields["brand"]
        category.queryset = Category.objects.filter(Q(is_active=True) | Q(pk=self.instance.category_id)).order_by(
            "path"
        )
        category.label_from_instance = category_label
        category.empty_label = "انتخاب دسته"
        brand.queryset = Brand.objects.filter(Q(is_active=True) | Q(pk=self.instance.brand_id)).order_by("name_fa")
        brand.empty_label = "بدون برند"

    def clean_title(self) -> str:
        return normalize_fa(self.cleaned_data["title"])

    def clean_short_description(self) -> str:
        return multiline(self.cleaned_data["short_description"])

    def clean_description(self) -> str:
        return rich_text(self.cleaned_data["description"])

    def clean_warranty_text(self) -> str:
        return normalize_fa(self.cleaned_data["warranty_text"])

    def clean_seo_title(self) -> str:
        return normalize_fa(self.cleaned_data["seo_title"])

    def clean_seo_description(self) -> str:
        return multiline(self.cleaned_data["seo_description"])

    def clean_slug(self) -> str:
        return clean_slug_value(self, self.cleaned_data.get("slug"), 280)


class VariantForm(FieldErrorAttrsMixin, forms.Form):
    title = forms.CharField(label="عنوان تنوع", max_length=200, widget=FaTextInput(attrs={"class": "input w-full"}))
    sku = forms.CharField(
        label="کد کالا (SKU)",
        max_length=64,
        widget=forms.TextInput(attrs={"class": "input w-full text-end latin", "dir": "ltr", "autocomplete": "off"}),
    )
    price = TomanField(label="قیمت (تومان)")
    compare_at_price = TomanField(label="قیمت قبل از تخفیف", required=False)
    max_per_order = FaIntegerField(label="حداکثر در هر سفارش", required=False, min_value=0, max_value=999)
    is_active = forms.BooleanField(label="فعال", required=False, widget=forms.CheckboxInput(attrs=CHECKBOX))
    color = forms.CharField(
        label="رنگ", required=False, max_length=60, widget=FaTextInput(attrs={"class": "input w-full"})
    )
    model = forms.CharField(
        label="مدل", required=False, max_length=60, widget=FaTextInput(attrs={"class": "input w-full"})
    )
    initial_stock = FaIntegerField(label="موجودی اولیه", required=False, min_value=0, max_value=100000)

    def __init__(self, *args, product, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        self.instance = instance
        self.fields["compare_at_price"].widget.attrs["data-discount-from"] = "1"
        if instance is not None:
            del self.fields["initial_stock"]  # stock changes later go through the stock ledger (P12)

    def clean_sku(self) -> str:
        sku = normalize_digits(self.cleaned_data["sku"]).strip()
        if not SKU_RE.match(sku):
            raise ValidationError("کد کالا فقط حرف لاتین، عدد، نقطه، خط تیره و زیرخط دارد")
        clash = Variant.objects.filter(sku=sku)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise ValidationError("این کد کالا برای تنوع دیگری ثبت شده است")
        return sku

    def clean(self):
        cleaned = super().clean()
        price, compare = cleaned.get("price"), cleaned.get("compare_at_price")
        if not compare:
            cleaned["compare_at_price"] = None  # empty or 0 means no discount
        elif price is not None and compare < price:
            self.add_error("compare_at_price", "قیمت قبل از تخفیف نمی‌تواند کمتر از قیمت فروش باشد")
        if not cleaned.get("max_per_order"):
            cleaned["max_per_order"] = None  # empty or 0 means up to the stock (D29)
        return cleaned

    def apply_to(self, variant: Variant) -> None:
        data = self.cleaned_data
        variant.title = normalize_fa(data["title"])
        variant.sku = data["sku"]
        variant.price = data["price"]
        variant.compare_at_price = data["compare_at_price"]
        variant.max_per_order = data["max_per_order"]
        variant.is_active = data["is_active"]
        options = dict(variant.options) if isinstance(variant.options, dict) else {}
        for key in ("color", "model"):  # other option keys are left alone
            value = normalize_fa(data.get(key) or "")
            if value:
                options[key] = value
            else:
                options.pop(key, None)
        variant.options = options


class QuickPriceForm(FieldErrorAttrsMixin, forms.Form):
    """Prices of every variant of one product, edited in the list row."""

    def __init__(self, *args, variants, **kwargs):
        super().__init__(*args, **kwargs)
        self.variants = variants
        for variant in variants:
            self.fields[f"price_{variant.pk}"] = TomanField(label="قیمت", initial=variant.price)
            self.fields[f"compare_{variant.pk}"] = TomanField(
                label="قبل از تخفیف", required=False, initial=variant.compare_at_price
            )

    def clean(self):
        cleaned = super().clean()
        for variant in self.variants:
            price = cleaned.get(f"price_{variant.pk}")
            compare = cleaned.get(f"compare_{variant.pk}") or None
            cleaned[f"compare_{variant.pk}"] = compare
            if compare is not None and price is not None and compare < price:
                self.add_error(f"compare_{variant.pk}", "قیمت قبل از تخفیف نمی‌تواند کمتر از قیمت فروش باشد")
        return cleaned


# Shown under each specification field so the editor knows what kind of value the attribute takes.
SPEC_TYPE_HINTS = {
    SpecAttribute.TYPE_TEXT: "نوع: متنی",
    SpecAttribute.TYPE_NUMBER: "نوع: عددی (مثلاً ۱۲ یا ۱۲٫۵)",
    SpecAttribute.TYPE_BOOL: "نوع: بله/خیر",
    SpecAttribute.TYPE_CHOICE: "نوع: انتخابی",
}


class SpecNumberField(forms.Field):
    """Persian or Arabic digits, «٬» thousands and «٫» decimals in; a Decimal with two places out."""

    def to_python(self, value):
        if value in self.empty_values:
            return None
        text = _SEPARATORS.sub("", normalize_digits(str(value))).replace("٫", ".")
        if not re.fullmatch(r"-?\d+(\.\d+)?", text):  # no letters, no «1e5», no «NaN»
            raise ValidationError("عدد معتبر وارد کنید")
        try:
            number = Decimal(text)
        except InvalidOperation:
            raise ValidationError("عدد معتبر وارد کنید") from None
        if not number.is_finite() or abs(number) >= Decimal("1e10"):
            raise ValidationError("عدد بیش از حد بزرگ است")
        return number.quantize(Decimal("0.01"))


class SpecsForm(FieldErrorAttrsMixin, forms.Form):
    """One field per applicable attribute. D41: a number fills both value_number and value_text."""

    def __init__(self, *args, attributes, values=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.attributes = list(attributes)
        existing = values or {}
        for attribute in self.attributes:
            label = f"{attribute.name} ({attribute.unit})" if attribute.unit else attribute.name
            if attribute.type == SpecAttribute.TYPE_BOOL:
                field = forms.ChoiceField(
                    label=label,
                    required=False,
                    choices=[("", "نامشخص"), ("1", "بله"), ("0", "خیر")],
                    widget=forms.Select(attrs={"class": "select w-full"}),
                )
            elif attribute.type == SpecAttribute.TYPE_NUMBER:
                field = SpecNumberField(
                    label=label,
                    required=False,
                    widget=FaDigitsInput(
                        attrs={"class": "input w-full text-end num", "inputmode": "decimal", "data-number-only": "1"}
                    ),
                )
            else:
                field = forms.CharField(
                    label=label,
                    required=False,
                    max_length=255,
                    widget=FaTextInput(attrs={"class": "input w-full", "list": f"spec-list-{attribute.pk}"}),
                )
            field.help_text = SPEC_TYPE_HINTS.get(attribute.type, "")
            saved = existing.get(attribute.pk)
            if saved is not None:
                if attribute.type == SpecAttribute.TYPE_BOOL:
                    field.initial = "1" if saved.value_number == 1 else "0"
                elif attribute.type == SpecAttribute.TYPE_NUMBER and saved.value_number is not None:
                    field.initial = number_text(saved.value_number)
                else:
                    field.initial = saved.value_text
            self.fields[f"spec_{attribute.pk}"] = field

    def desired(self) -> dict[int, tuple[str, Decimal | None] | None]:
        """attribute id -> (value_text, value_number), or None when the field is empty (the value is removed)."""
        result: dict[int, tuple[str, Decimal | None] | None] = {}
        for attribute in self.attributes:
            value = self.cleaned_data.get(f"spec_{attribute.pk}")
            if attribute.type == SpecAttribute.TYPE_BOOL:
                result[attribute.pk] = (
                    None if value in (None, "") else (("بله", Decimal(1)) if value == "1" else ("خیر", Decimal(0)))
                )
            elif attribute.type == SpecAttribute.TYPE_NUMBER:
                result[attribute.pk] = None if value is None else (number_text(value), value)
            else:
                text = normalize_fa(value or "")
                result[attribute.pk] = (text, None) if text else None
        return result


# --- categories, specification attributes, brands -------------------------------


class CategoryForm(FieldErrorAttrsMixin, forms.ModelForm):
    slug = forms.CharField(
        label="نشانی",
        required=False,
        max_length=180,
        widget=forms.TextInput(attrs={"class": "input w-full text-end latin", "dir": "ltr"}),
        help_text="خالی = ساخت خودکار از نام",
    )
    featured_order = FaIntegerField(label="ترتیب در دسته‌های برتر", min_value=0, max_value=9999)
    menu_order = FaIntegerField(label="ترتیب در منو", min_value=0, max_value=9999)
    logo_clear = forms.BooleanField(required=False, label="حذف لوگوی فعلی", widget=forms.CheckboxInput(attrs=CHECKBOX))

    class Meta:
        model = Category
        fields = [
            "parent",
            "name",
            "slug",
            "logo",
            "description",
            "is_featured",
            "featured_order",
            "show_in_menu",
            "menu_order",
            "is_active",
            "spec_inherit",
        ]
        labels = {
            "parent": "دسته‌ی والد",
            "name": "نام",
            "logo": "لوگو",
            "description": "توضیح",
            "is_featured": "دسته‌ی برتر",
            "show_in_menu": "نمایش در منو",
            "is_active": "فعال",
            "spec_inherit": "ارث‌بری مشخصات از والد",
        }
        widgets = {
            "parent": forms.Select(attrs={"class": "select w-full"}),
            "name": FaTextInput(attrs={"class": "input w-full"}),
            "logo": forms.FileInput(attrs=FILE_ATTRS),
            "description": FaTextarea(attrs={"class": "textarea w-full", "rows": 3}),
            "is_featured": forms.CheckboxInput(attrs=CHECKBOX),
            "show_in_menu": forms.CheckboxInput(attrs=CHECKBOX),
            "is_active": forms.CheckboxInput(attrs=CHECKBOX),
            "spec_inherit": forms.CheckboxInput(attrs=CHECKBOX),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parents = Category.objects.order_by("path")
        if self.instance.pk and self.instance.path:  # a category cannot move under itself or its own subtree
            parents = parents.exclude(path__gte=self.instance.path, path__lt=subtree_upper_bound(self.instance.path))
        self.fields["parent"].queryset = parents
        self.fields["parent"].label_from_instance = category_label
        self.fields["parent"].empty_label = "بدون والد (دسته‌ی ریشه)"

    def clean_name(self) -> str:
        return normalize_fa(self.cleaned_data["name"])

    def clean_description(self) -> str:
        return multiline(self.cleaned_data["description"])

    def clean_slug(self) -> str:
        return clean_slug_value(self, self.cleaned_data.get("slug"), 180)

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if isinstance(logo, UploadedFile):
            validate_upload(logo, max_bytes=LOGO_MAX_BYTES, label="لوگو")
        return logo


class SpecAttributeForm(FieldErrorAttrsMixin, forms.ModelForm):
    sort = FaIntegerField(label="ترتیب", min_value=0, max_value=9999)

    class Meta:
        model = SpecAttribute
        fields = ["name", "type", "unit", "is_filterable", "sort"]
        labels = {"name": "نام", "type": "نوع", "unit": "واحد", "is_filterable": "قابل فیلتر"}
        widgets = {
            "name": FaTextInput(attrs={"class": "input w-full"}),
            "type": forms.Select(attrs={"class": "select w-full"}),
            "unit": FaTextInput(attrs={"class": "input w-full"}),
            "is_filterable": forms.CheckboxInput(attrs=CHECKBOX),
        }

    def clean_name(self) -> str:
        return normalize_fa(self.cleaned_data["name"])

    def clean_unit(self) -> str:
        return normalize_fa(self.cleaned_data["unit"])

    def clean_type(self) -> str:
        new_type = self.cleaned_data["type"]
        if self.instance.pk and new_type != self.instance.type and self.instance.values.exists():
            raise ValidationError("برای مشخصه‌ای که مقدار ثبت‌شده دارد، نوع قابل تغییر نیست")
        return new_type


class BrandForm(FieldErrorAttrsMixin, forms.ModelForm):
    slug = forms.CharField(
        label="نشانی",
        required=False,
        max_length=140,
        widget=forms.TextInput(attrs={"class": "input w-full text-end latin", "dir": "ltr"}),
        help_text="خالی = ساخت خودکار از نام",
    )
    logo_clear = forms.BooleanField(required=False, label="حذف لوگوی فعلی", widget=forms.CheckboxInput(attrs=CHECKBOX))

    class Meta:
        model = Brand
        fields = ["name_fa", "name_en", "slug", "logo", "aliases", "is_active"]
        labels = {"name_fa": "نام فارسی", "name_en": "نام لاتین", "logo": "لوگو", "is_active": "فعال"}
        widgets = {
            "name_fa": FaTextInput(attrs={"class": "input w-full"}),
            "name_en": forms.TextInput(attrs={"class": "input w-full text-end latin", "dir": "ltr"}),
            "logo": forms.FileInput(attrs=FILE_ATTRS),
            "aliases": FaTextInput(attrs={"class": "input w-full"}),
            "is_active": forms.CheckboxInput(attrs=CHECKBOX),
        }

    def clean_name_fa(self) -> str:
        return normalize_fa(self.cleaned_data["name_fa"])

    def clean_aliases(self) -> str:
        return normalize_fa(self.cleaned_data["aliases"])

    def clean_slug(self) -> str:
        return clean_slug_value(self, self.cleaned_data.get("slug"), 140)

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if isinstance(logo, UploadedFile):
            validate_upload(logo, max_bytes=LOGO_MAX_BYTES, label="لوگو")
        return logo
