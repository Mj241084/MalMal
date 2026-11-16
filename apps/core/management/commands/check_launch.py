"""Pre-launch gate (docs/00 §7). ERROR = unsafe or unusable in production; WARNING = incomplete content."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage, staticfiles_storage
from django.core.cache import caches
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.catalog.models import Product
from apps.core.models import SiteSettings, StaticPage
from apps.geo.models import City
from apps.notifications import sms
from apps.orders.shipping import default_method
from apps.payments import gateways
from apps.payments.services import refund_candidates

ERROR, WARNING = "خطا", "هشدار"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
LAUNCH_TEMPLATES = ("order_paid", "order_shipped")
RECOMMENDED_PAGES = {
    "terms": "قوانین و مقررات",
    "returns": "بازگشت کالا",
    "privacy": "حریم خصوصی",
    "about": "درباره‌ی ما",
    "contact": "تماس با ما",
}


def _settings():
    if settings.DEBUG:
        yield ERROR, "DEBUG روشن است"
    if settings.SECRET_KEY.startswith("django-insecure") or len(settings.SECRET_KEY) < 50:
        yield ERROR, "DJANGO_SECRET_KEY پیش‌فرض یا ضعیف است"
    if not set(settings.ALLOWED_HOSTS) - LOCAL_HOSTS:
        yield ERROR, "ALLOWED_HOSTS دامنه‌ی واقعی ندارد"
    site = urlsplit(settings.SITE_URL)
    if site.scheme != "https" or site.hostname in LOCAL_HOSTS:
        yield ERROR, "SITE_URL باید نشانی https واقعی باشد (callback پرداخت و sitemap از آن ساخته می‌شود)"
    if settings.ADMIN_URL.startswith("panel/"):
        yield ERROR, "ADMIN_URL نباید با panel/ شروع شود (با مسیر پنل تداخل دارد)"

    if settings.ADMIN_URL == "admin/":
        yield ERROR, "ADMIN_URL هنوز پیش‌فرض (admin/) است"
    if not (settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE):
        yield ERROR, "کوکی‌های نشست یا CSRF حالت Secure ندارند"


def _services():
    if settings.ZARINPAL_SANDBOX:
        yield ERROR, "ZARINPAL_SANDBOX=true است (پرداخت واقعی نمی‌شود)"
    if not settings.ZARINPAL_MERCHANT_ID:
        yield ERROR, "ZARINPAL_MERCHANT_ID خالی است"
    if not any(g.code != "fake" for g in gateways.available()):
        yield ERROR, "هیچ درگاه واقعی فعالی نیست (ادمین ← درگاه‌های پرداخت)"
    if settings.SMS_BACKEND == "console":
        yield ERROR, "SMS_BACKEND=console است (کد ورود به مشتری نمی‌رسد)"
    elif not settings.SMSIR_API_KEY or not sms.template_is_configured("otp"):
        yield ERROR, "SMSIR_API_KEY یا SMSIR_TEMPLATE_ID_OTP خالی است (ورود ممکن نیست)"
    for key in LAUNCH_TEMPLATES:
        if not sms.template_id(key):
            yield WARNING, f"شناسه‌ی قالب پیامک «{key}» خالی است ({sms.TEMPLATE_SETTINGS[key]})"
    if default_method() is None:
        yield ERROR, "روش ارسال فعالی نیست (checkout کار نمی‌کند)"
    try:
        for alias in ("default", "ratelimit"):
            caches[alias].set("launch_check", 1, 5)
            if caches[alias].get("launch_check") != 1:
                raise RuntimeError(alias)
    except Exception:
        yield ERROR, "Redis در دسترس نیست (کش و محدودیت نرخ OTP)"
    if not settings.NESHAN_MAP_KEY:
        yield WARNING, "NESHAN_MAP_KEY خالی است (نقشه‌ی آدرس غیرفعال)"
    if not settings.NESHAN_SERVICE_KEY:
        yield WARNING, "NESHAN_SERVICE_KEY خالی است (فهرست استان و شهر فقط از دیتابیس خوانده می‌شود و تازه نمی‌شود)"


def _build():
    if not settings.BACKUP_DIR:
        yield WARNING, "BACKUP_DIR خالی است (پشتیبان شبانه ممکن نیست)"
    executor = MigrationExecutor(connection)
    pending = bool(executor.migration_plan(executor.loader.graph.leaf_nodes()))
    if pending:
        yield ERROR, "مهاجرت‌های اجرانشده هست (migrate)"
    if not (Path(settings.BASE_DIR) / "static" / "css" / "app.css").is_file():
        yield ERROR, "static/css/app.css ساخته نشده (pnpm run build:css)"
    if (
        isinstance(staticfiles_storage, ManifestStaticFilesStorage)
        and not (Path(settings.STATIC_ROOT) / "staticfiles.json").is_file()
    ):
        yield ERROR, "collectstatic اجرا نشده"
    if pending:  # the FTS table does not exist yet; the missing migration above is the real finding
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM product_fts")
        indexed = cursor.fetchone()[0]
    if not indexed and Product.objects.filter(status=Product.STATUS_ACTIVE).exists():
        yield WARNING, "ایندکس جستجو خالی است (rebuild_search)"


def _content():
    if not City.objects.exists():
        yield ERROR, "فهرست استان و شهر خالی است (manage.py sync_geo)"
    for page in StaticPage.objects.filter(is_active=True, needs_review=True):
        yield WARNING, f"صفحه‌ی «{page.title}» نیازمند بازبینی است"
    missing = [
        title
        for slug, title in RECOMMENDED_PAGES.items()
        if not StaticPage.objects.filter(slug=slug, is_active=True).exists()
    ]
    if missing:
        yield WARNING, "صفحه‌ی ثابت فعال ندارید: " + "، ".join(missing)
    site = SiteSettings.get_solo()
    for field, label in (("store_name", "نام فروشگاه"), ("phone", "تلفن"), ("address", "آدرس")):
        if not getattr(site, field):
            yield WARNING, f"تنظیمات سایت: {label} خالی است"
    if not site.logo_light:
        yield WARNING, "لوگوی نهایی بارگذاری نشده (لوگوی موقت نمایش داده می‌شود)"
    if not site.trust_marks_html:
        yield WARNING, "نماد اعتماد (اینماد) ثبت نشده"
    refunds = refund_candidates().count()
    if refunds:
        yield WARNING, f"{refunds} پرداخت تاییدشده نیاز به بازگشت وجه دارد"


def collect():
    for group in (_settings, _services, _build, _content):
        yield from group()


class Command(BaseCommand):
    help = "Pre-launch gate. Exit code 1 on any ERROR (or any WARNING with --strict)."

    def add_arguments(self, parser):
        parser.add_argument("--strict", action="store_true", help="treat warnings as errors")

    def handle(self, *args, strict, **options):
        findings = list(collect())
        for level, text in findings:
            style = self.style.ERROR if level == ERROR else self.style.WARNING
            self.stdout.write(style(f"[{level}] {text}"))
        errors = sum(1 for level, _ in findings if level == ERROR)
        warnings = len(findings) - errors
        if errors or (strict and warnings):
            raise CommandError(f"{errors} خطا، {warnings} هشدار")
        self.stdout.write(self.style.SUCCESS(f"آماده‌ی انتشار ({warnings} هشدار)"))
