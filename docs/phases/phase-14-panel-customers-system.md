# فاز P14 — مشتریان، تنظیمات و سیستم

**هدف:** کامل‌کردن بخش‌های مدیریتی.

## مطالعه
- `docs/09-panel-spec.md` ماژول‌های ۱۱ تا ۱۴
- `apps/accounts/*`، `apps/core/management/commands/check_launch.py`، `docs/deploy.md`

## کارها
1. مشتریان (لیست، جزئیات، تغییر کد ملی با ممیزی، فعال/غیرفعال). provider جستجو. گسترش `setup_groups` (`accounts.view_user` برای فروش).
2. تنظیمات (تب‌ها، `ShippingMethod`، `PaymentGateway`، فیلدهای superuser-only).
3. سیستم: پیامک، همکاران، ممیزی، آمادگی انتشار، وضعیت پشتیبان.
4. `accounts.services.create_staff_user` و اتصال دستور `create_staff` به آن (خروجی دستور بدون تغییر).
5. `check_launch.collect_detailed()` (خروجی `collect()` و تست‌های موجود بدون تغییر).

## خارج از این فاز
ویرایش آزاد نام/ایمیل مشتری، ویرایشگر گروه/مجوز در رابط، ورود دو مرحله‌ای.

## تست‌ها
- ساخت staff از شماره‌ی مشتری رد می‌شود؛ superuser ساخته نمی‌شود؛ خودغیرفعال‌سازی و آخرین superuser رد می‌شود؛ ریست رمز نشست‌ها را باطل می‌کند؛ بخش سیستم برای غیر superuser ۴۰۳.
- تغییر کد ملی فقط با مجوز، با اعتبارسنجی و ممیزی.
- اعتبارسنجی‌های تنظیمات (ساعت‌ها، OTP، آخرین روش/درگاه).
- `check_launch` CLI بدون تغییر.

## Definition of Done
- [ ] خروجی دستور `create_staff` و `check_launch` (CLI) نسبت به قبل تغییر نکرده است.
- [ ] `[OPEN]` سوال ۴ (گروه چهارم) از کاربر پرسیده و جوابش در `09` ثبت شده است.

### مشترک همه‌ی فازهای پنل
- [ ] `uv run pytest` و `uv run ruff check .` و `uv run ruff format .` بدون خطا (خروجی خوانده شود).
- [ ] grepهای `04` بخش ۱۳ روی `templates/` (شامل `templates/panel/`) و `static/src/` صفر نتیجه می‌دهند.
- [ ] `pnpm run build:css` اجرا شده و `static/css/app.css` commit شده است.
- [ ] `uv run python scripts/build_sprite.py` اجرا شده و هیچ آیکونی ناموجود نیست.
- [ ] اسناد `09`، `10`، `08` و `03` با واقعیت کد هم‌تراز و «تغییرات» هر کدام به‌روز است.
- [ ] `docs/phases/STATUS.md` به‌روز است.
- [ ] فهرست «چه چیزی باید دیده شود» برای کاربر داده شده است (دو تم، عرض ۳۲۰ و ۱۲۸۰). مرورگر و Playwright اجرا نمی‌شود (`CLAUDE.md` بخش ۶).
