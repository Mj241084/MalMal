"""Marketing and content forms of the panel (docs/09 modules 9 and 10)."""

from __future__ import annotations

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.urls import reverse
from django.utils.text import slugify

from apps.catalog.images import validate_upload
from apps.catalog.models import Brand, Category, Product
from apps.core.forms import FieldErrorAttrsMixin
from apps.core.jalali_admin import EndOfDayJalaliDateTimeField, JalaliDateWidget
from apps.core.jalali_forms import JalaliDateTimeField
from apps.core.models import FooterLink, StaticPage
from apps.core.text import normalize_digits
from apps.core.widgets import FaDigitsInput, FaTextarea, FaTextInput
from apps.marketing.models import MAX_IMAGE_BYTES, Banner, Collection, HomeBlock, TrustItem, is_safe_target
from apps.panel.fields import FaIntegerField, TomanField
from apps.panel.forms_catalog import category_label, clean_slug_value, multiline

# Every name here must also be in scripts/build_sprite.py ALWAYS_INCLUDE: the template scan cannot see icons stored in the DB.
TRUST_ICONS = (
    "truck", "package", "gift", "store", "map-pin", "clock", "rotate-ccw", "shield-check", "badge-check", "lock",
    "credit-card", "wallet", "percent", "tag", "phone", "headphones", "message-circle", "star", "heart",
    "thumbs-up", "zap", "leaf",
)  # fmt: skip

LTR = {"dir": "ltr", "autocomplete": "off"}
FILE = {"accept": "image/png,image/jpeg,image/webp"}
WINDOW_HELP_START = "خالی = از همین حالا. فقط روز انتخاب می‌شود (ساعت ۰۰:۰۰)"
WINDOW_HELP_END = "خالی = بدون پایان. ساعت پایان ۲۳:۵۹ همان روز است"


class PanelForm(FieldErrorAttrsMixin, forms.ModelForm):
    """Daisy classes for widgets that did not get one, and Persian-aware normalization of text columns."""

    normalized: tuple[str, ...] = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if widget.attrs.get("class") or isinstance(
                widget, (forms.CheckboxSelectMultiple, forms.RadioSelect, forms.HiddenInput)
            ):
                continue
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "checkbox checkbox-sm"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "textarea w-full"
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = "file-input w-full"
            elif isinstance(widget, FaDigitsInput):
                widget.attrs["class"] = "input w-full text-end num"
            else:
                widget.attrs["class"] = "input w-full"

    def clean(self):
        cleaned = super().clean()
        for name in self.normalized:
            value = cleaned.get(name)
            if isinstance(value, str):
                cleaned[name] = multiline(value)
        return cleaned

    def _checked_image(self, name: str):
        file = self.cleaned_data.get(name)
        if isinstance(file, UploadedFile):
            validate_upload(file, max_bytes=MAX_IMAGE_BYTES, label="تصویر")
        return file


# --- marketing ---------------------------------------------------------------


class HomeBlockForm(PanelForm):
    normalized = ("title",)
    limit = FaIntegerField(label="تعداد آیتم", min_value=1, max_value=24, initial=12)

    class Meta:
        model = HomeBlock
        fields = ["kind", "title", "rail_source", "category", "collection", "limit", "is_active"]
        labels = {
            "kind": "نوع بلوک",
            "title": "عنوان",
            "rail_source": "منبع ردیف",
            "category": "محدود به دسته",
            "collection": "مجموعه",
            "is_active": "فعال",
        }
        widgets = {"title": FaTextInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        category = self.fields["category"]
        category.queryset = Category.objects.order_by("path")
        category.label_from_instance = category_label
        category.empty_label = "همه‌ی دسته‌ها"
        self.fields["collection"].empty_label = "انتخاب مجموعه"
        category.when = ("kind", "product_rail")
        self.fields["rail_source"].when = ("kind", "product_rail")
        self.fields["collection"].when = ("kind", "collection_rail")
        self.fields["limit"].when = ("kind", "categories,product_rail,collection_rail,brands,trust")


class ProductIdField(forms.ModelChoiceField):
    """The id is typed with Persian digits and posted as typed (D30): normalize before the lookup."""

    def to_python(self, value):
        return super().to_python(normalize_digits(value).strip() if isinstance(value, str) else value)


class BannerForm(PanelForm):
    normalized = ("title", "alt")
    field_order = [
        "title", "placement", "is_active", "image_desktop", "image_mobile", "image_mobile_clear", "alt",
        "target_type", "target_product", "target_category", "target_collection", "target_url", "starts_at", "ends_at",
    ]  # fmt: skip
    # the product is picked by its id (a select of the whole catalog would not scale)
    target_product = ProductIdField(
        label="شناسه‌ی محصول",
        queryset=Product.objects.all(),
        required=False,
        widget=FaDigitsInput(),
        help_text="عدد داخل آدرس صفحه‌ی ویرایش محصول در پنل",
        error_messages={"invalid_choice": "محصولی با این شناسه پیدا نشد"},
    )
    image_mobile_clear = forms.BooleanField(required=False, label="حذف تصویر موبایل فعلی")
    starts_at = JalaliDateTimeField(
        required=False,
        label="شروع نمایش",
        widget=JalaliDateWidget(attrs={"class": "input w-full num"}),
        help_text=WINDOW_HELP_START,
    )
    ends_at = EndOfDayJalaliDateTimeField(
        required=False,
        label="پایان نمایش",
        widget=JalaliDateWidget(attrs={"class": "input w-full num"}),
        help_text=WINDOW_HELP_END,
    )

    class Meta:
        model = Banner
        fields = [
            "title", "placement", "is_active", "image_desktop", "image_mobile", "alt", "target_type",
            "target_product", "target_category", "target_collection", "target_url", "starts_at", "ends_at",
        ]  # fmt: skip
        labels = {
            "title": "عنوان (داخلی)",
            "placement": "جایگاه",
            "is_active": "فعال",
            "image_desktop": "تصویر دسکتاپ",
            "image_mobile": "تصویر موبایل (اختیاری)",
            "alt": "متن جایگزین تصویر",
            "target_type": "نوع مقصد",
            "target_category": "دسته",
            "target_collection": "مجموعه",
            "target_url": "نشانی دلخواه",
        }
        widgets = {
            "title": FaTextInput(),
            "alt": FaTextInput(),
            "image_desktop": forms.FileInput(attrs=FILE),
            "image_mobile": forms.FileInput(attrs=FILE),
            "target_url": forms.TextInput(attrs={**LTR, "class": "input w-full text-end latin"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("image_desktop", "image_mobile"):
            self.fields[name].widget.attrs["data-preview"] = f"#preview-{name}"
        category = self.fields["target_category"]
        category.queryset = Category.objects.order_by("path")
        category.label_from_instance = category_label
        category.empty_label = "انتخاب دسته"
        self.fields["target_collection"].empty_label = "انتخاب مجموعه"
        self.fields["target_product"].when = ("target_type", "product")
        category.when = ("target_type", "category")
        self.fields["target_collection"].when = ("target_type", "collection")
        self.fields["target_url"].when = ("target_type", "url")

    def clean_image_desktop(self):
        return self._checked_image("image_desktop")

    def clean_image_mobile(self):
        return self._checked_image("image_mobile")

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("target_type")
        # a leftover value of a hidden target field must never reach Banner.clean()
        if kind != Banner.TARGET_PRODUCT:
            cleaned["target_product"] = None
            self._errors.pop("target_product", None)
        if kind != Banner.TARGET_CATEGORY:
            cleaned["target_category"] = None
        if kind != Banner.TARGET_COLLECTION:
            cleaned["target_collection"] = None
        if kind != Banner.TARGET_URL:
            cleaned["target_url"] = ""
        return cleaned


class CollectionForm(PanelForm):
    normalized = ("title", "description", "seo_title", "seo_description")
    field_order = [
        "title", "slug", "description", "cover", "cover_clear", "mode", "is_active", "starts_at", "ends_at",
        "categories", "brands", "min_discount_pct", "min_price", "max_price", "only_in_stock", "sort_by",
        "seo_title", "seo_description",
    ]  # fmt: skip
    slug = forms.CharField(
        label="نشانی",
        required=False,
        max_length=180,
        widget=forms.TextInput(attrs={**LTR, "class": "input w-full text-end latin"}),
        help_text="خالی = ساخت خودکار از عنوان",
    )
    cover_clear = forms.BooleanField(required=False, label="حذف کاور فعلی")
    starts_at = JalaliDateTimeField(
        required=False,
        label="شروع نمایش",
        widget=JalaliDateWidget(attrs={"class": "input w-full num"}),
        help_text=WINDOW_HELP_START,
    )
    ends_at = EndOfDayJalaliDateTimeField(
        required=False,
        label="پایان نمایش",
        widget=JalaliDateWidget(attrs={"class": "input w-full num"}),
        help_text=WINDOW_HELP_END,
    )
    categories = forms.ModelMultipleChoiceField(
        label="دسته‌ها", queryset=Category.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )
    brands = forms.ModelMultipleChoiceField(
        label="برندها", queryset=Brand.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )
    min_discount_pct = FaIntegerField(label="حداقل درصد تخفیف", required=False, min_value=1, max_value=99)
    min_price = TomanField(label="حداقل قیمت (تومان)", required=False)
    max_price = TomanField(label="حداکثر قیمت (تومان)", required=False)

    class Meta:
        model = Collection
        fields = [
            "title", "slug", "description", "cover", "mode", "is_active", "starts_at", "ends_at", "categories",
            "brands", "min_discount_pct", "min_price", "max_price", "only_in_stock", "sort_by", "seo_title",
            "seo_description",
        ]  # fmt: skip
        labels = {
            "title": "عنوان",
            "description": "توضیح",
            "cover": "کاور",
            "mode": "حالت",
            "is_active": "فعال",
            "only_in_stock": "فقط کالاهای موجود",
            "sort_by": "مرتب‌سازی پیش‌فرض",
            "seo_title": "عنوان سئو",
            "seo_description": "توضیحات سئو",
        }
        widgets = {
            "title": FaTextInput(),
            "description": FaTextarea(attrs={"rows": 3}),
            "cover": forms.FileInput(attrs=FILE),
            "seo_title": FaTextInput(),
            "seo_description": FaTextarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cover"].widget.attrs["data-preview"] = "#preview-cover"
        categories = self.fields["categories"]
        categories.queryset = Category.objects.order_by("path")
        categories.label_from_instance = category_label
        self.fields["brands"].queryset = Brand.objects.order_by("name_fa")
        for name in (
            "categories", "brands", "min_discount_pct", "min_price", "max_price", "only_in_stock", "sort_by",
        ):  # fmt: skip
            self.fields[name].when = ("mode", "rule")

    def clean_slug(self) -> str:
        return clean_slug_value(self, self.cleaned_data.get("slug"), 180)

    def clean_cover(self):
        return self._checked_image("cover")


class RulePreviewForm(forms.Form):
    """The rule fields of CollectionForm, validated alone for the live product count."""

    categories = forms.ModelMultipleChoiceField(queryset=Category.objects.all(), required=False)
    brands = forms.ModelMultipleChoiceField(queryset=Brand.objects.all(), required=False)
    min_discount_pct = FaIntegerField(required=False, min_value=0, max_value=99)
    min_price = TomanField(required=False)
    max_price = TomanField(required=False)
    only_in_stock = forms.BooleanField(required=False)


class TrustItemForm(PanelForm):
    normalized = ("title", "subtitle")
    icon = forms.ChoiceField(label="آیکون", choices=(), widget=forms.RadioSelect)

    class Meta:
        model = TrustItem
        fields = ["icon", "title", "subtitle", "is_active"]
        labels = {"title": "عنوان", "subtitle": "توضیح کوتاه", "is_active": "فعال"}
        widgets = {"title": FaTextInput(), "subtitle": FaTextInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        names = list(TRUST_ICONS)
        current = self.instance.icon if self.instance.pk else ""
        if current and current not in names:
            names.append(current)  # an icon chosen in the admin earlier stays selectable
        self.fields["icon"].choices = [(name, name) for name in names]
        if not self.instance.pk:
            self.fields["icon"].initial = names[0]


# --- content -----------------------------------------------------------------


class StaticPageForm(PanelForm):
    normalized = ("title", "body", "seo_title", "seo_description")
    field_order = ["title", "slug", "body", "is_active", "needs_review", "seo_title", "seo_description"]
    slug = forms.CharField(
        label="نشانی",
        required=False,
        max_length=120,
        widget=forms.TextInput(attrs={**LTR, "class": "input w-full text-end latin"}),
        help_text="خالی = ساخت خودکار از عنوان. نمونه‌ها: terms، returns، privacy، about، contact. تغییر نشانی لینک‌های قبلی را از کار می‌اندازد",
    )

    class Meta:
        model = StaticPage
        fields = ["title", "slug", "body", "is_active", "needs_review", "seo_title", "seo_description"]
        labels = {
            "title": "عنوان",
            "body": "متن صفحه",
            "is_active": "فعال",
            "needs_review": "نیازمند بازبینی",
            "seo_title": "عنوان سئو",
            "seo_description": "توضیحات سئو",
        }
        widgets = {
            "title": FaTextInput(),
            "body": FaTextarea(attrs={"rows": 14}),
            "seo_title": FaTextInput(),
            "seo_description": FaTextarea(attrs={"rows": 2}),
        }

    def clean_slug(self) -> str:
        raw = (self.cleaned_data.get("slug") or "").strip()
        if not raw and self.instance.pk:
            return self.instance.slug
        slug = slugify(raw or self.cleaned_data.get("title") or "", allow_unicode=True)[:120]
        if not slug:
            raise forms.ValidationError("نشانی معتبر نیست")
        return slug


class FooterLinkForm(PanelForm):
    normalized = ("title",)
    field_order = ["group", "title", "page", "url", "is_active"]
    page = forms.ModelChoiceField(
        label="یا یک صفحه‌ی ثابت", queryset=StaticPage.objects.none(), required=False, empty_label="—"
    )
    url = forms.CharField(
        label="آدرس",
        required=False,
        max_length=300,
        widget=forms.TextInput(attrs={**LTR, "class": "input w-full text-end latin"}),
        help_text="مسیر داخلی (مثل /pages/terms/) یا نشانی https",
    )

    class Meta:
        model = FooterLink
        fields = ["group", "title", "url", "is_active"]
        labels = {"group": "ستون", "title": "عنوان لینک", "is_active": "فعال"}
        widgets = {"title": FaTextInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["page"].queryset = StaticPage.objects.filter(is_active=True).order_by("title")

    def clean(self):
        cleaned = super().clean()
        url = (cleaned.get("url") or "").strip()
        page = cleaned.get("page")
        if not url and page:
            url = reverse("core:static_page", args=[page.slug])
        if not url:
            self.add_error("url", "آدرس را بنویسید یا یک صفحه‌ی ثابت انتخاب کنید")
        elif not is_safe_target(url):
            self.add_error("url", "فقط مسیر داخلی (با /) یا نشانی https مجاز است")
        else:
            cleaned["url"] = url
        return cleaned
