# فاز P9 — پوسته‌ی پنل، ورود، مجوز، ممیزی و داشبورد اولیه

**هدف:** `/panel/` با ورود امن، ناوبری مبتنی بر مجوز، اجزای مشترک و داشبورد اولیه.

## مطالعه
- `docs/09-panel-spec.md` بخش‌های ۲.۲ تا ۲.۵ و ۲.۸ (و ۲.۱۱ برای تطبیق با کد)
- `docs/10-panel-ui.md` کامل
- `docs/04-design-system.md` (کامل) و `docs/08-ui-modules.md`
- کد: `apps/orders/workflow.py`، `apps/payments/services.py`، `apps/catalog/{models,stock,cache,images}.py`، `apps/marketing/{models,services,forms}.py`، `apps/accounts/{admin.py,management/commands/setup_groups.py,management/commands/create_staff.py}`، `apps/core/management/commands/check_launch.py`، `apps/core/{html,seo}.py`، `scripts/build_sprite.py`، `apps/catalog/tests/test_architecture.py`، `apps/core/tests/test_ui_rules.py`
- اسکیل‌ها: `htmx-patterns`، `daisyui` (drawer، navbar، menu، table، tabs، modal، toast)، `unslop`

## کارها
1. **تطبیق با کد:** هر ردیف جدول `09` بخش ۲.۱۱ را با کد واقعی بسنج. `09` را اصلاح کن (کد برنده است) و تناقض‌ها را در گزارش پایانی فاز بنویس. این کار پیش از هر کد دیگری انجام می‌شود.
2. اسکلت اپ، ثبت در `INSTALLED_APPS`، `path("panel/", include(...))`، `middleware.py` (D44)، افزودن `/panel/` به `PRIVATE_PATHS`.
3. `auth.py`: ورود/خروج/تغییر رمز/خروج از همه (بخش ۲.۴)، صفحه‌ی ورود مینیمال. rate limit، تایم‌اوت، `next` امن، ریدایرکت HTMX.
4. `permissions.py`، `nav.py`، صفحه‌های ۴۰۳/۴۰۴ پنلی، صفحه‌ی «بدون دسترسی».
5. `audit.py` روی `LogEntry`. `htmx.py`، `fields.py`.
6. قالب‌ها: `templates/panel/base.html` + سایدبار، نوار بالا، پیام‌ها. استخراج `partials/_mm_dialog.html` از `base.html` (بدون تغییر رفتار). partialهای مشترک: صفحه‌بندی، نوار فیلتر، نقطه‌ی وضعیت، حالت خالی، اسکلت جدول. `panel_tags` (`jdate`، `status_dot`، `thumb_url`).
7. `static/js/mm/panel.js` و ردیفش در `docs/08`.
8. زیرساخت رجیستری جستجو و بج‌ها (اندپوینت‌ها بدون provider).
9. داشبورد اولیه: ۴ کارت عددی و هشدار بازگشت وجه، با لینک **موقت** به changelistهای ادمین (علامت `[TEMP]`؛ فازهای بعد جایگزین می‌کنند).
10. `scripts/build_sprite.py`: اسکن `apps/panel/nav.py` + تست وجود آیکون‌ها.
11. `check_launch`: خطا اگر `ADMIN_URL` با `panel/` شروع شود.
12. تست‌ها: ورود/rate limit/تایم‌اوت/`next`/مشتری و staff بی‌مجوز، تست متا (ناشناس ← ورود، بی‌مجوز ← ۴۰۳)، هدرها، تست معماری (هیچ import از `apps.panel` بیرون)، ارقام فارسی.
13. اسناد: `09`/`10`/`02`/`03`/`04`/`08`/`CLAUDE.md`/`deploy.md`/`00`.

## خارج از این فاز
هر صفحه‌ی کاری (سفارش، محصول و...).

## Definition of Done
- [ ] ورود با staff کار می‌کند، مشتری نمی‌تواند وارد شود، پس از ۱۲ ساعت خروج، تغییر رمز نشست‌های دیگر را باطل می‌کند.
- [ ] جدول `09` بخش ۲.۱۱ با کد تطبیق داده شده و تناقض‌ها در گزارش آمده‌اند.
- [ ] هیچ لینک `[TEMP]` بی‌علامت در داشبورد نمانده است.

### مشترک همه‌ی فازهای پنل
- [ ] `uv run pytest` و `uv run ruff check .` و `uv run ruff format .` بدون خطا (خروجی خوانده شود).
- [ ] grepهای `04` بخش ۱۳ روی `templates/` (شامل `templates/panel/`) و `static/src/` صفر نتیجه می‌دهند.
- [ ] `pnpm run build:css` اجرا شده و `static/css/app.css` commit شده است.
- [ ] `uv run python scripts/build_sprite.py` اجرا شده و هیچ آیکونی ناموجود نیست.
- [ ] اسناد `09`، `10`، `08` و `03` با واقعیت کد هم‌تراز و «تغییرات» هر کدام به‌روز است.
- [ ] `docs/phases/STATUS.md` به‌روز است.
- [ ] فهرست «چه چیزی باید دیده شود» برای کاربر داده شده است (دو تم، عرض ۳۲۰ و ۱۲۸۰). مرورگر و Playwright اجرا نمی‌شود (`CLAUDE.md` بخش ۶).
