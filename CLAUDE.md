# مل‌مل (MAL MAL) — دستورالعمل دائمی Claude Code

فروشگاه آنلاین لوازم خانگی. فارسی، RTL، پول به تومان.
استک: Django + SQLite (WAL) + Redis + Tailwind v4 + DaisyUI 5 + HTMX. سرور HTML می‌دهد؛ SPA نداریم.

این فایل در هر نشست خوانده می‌شود. کوتاه نگهش دار. جزئیات در `docs/` است.

---

## ۱. قبل از هر کاری

1. این فایل و `docs/00-README.md` را بخوان.
2. بریف فاز جاری را بخوان: `docs/phases/phase-0X-*.md`. اگر کاربر فاز را نگفت، بپرس (یک سوال کوتاه).
3. فقط بخش‌هایی از `docs/02` تا `docs/07` را بخوان که بریف فاز به آن‌ها ارجاع داده. کل اسناد را بی‌دلیل نخوان.
4. اسکیل‌های `skills/` را طبق نیاز فاز بخوان (بخش ۵).
5. یک فهرست کار (TaskCreate) از «کارها» و «Definition of Done» بریف بساز.

**هر فاز در یک نشست.** اگر نشست طولانی شد و زمینه‌ات پر شد، خلاصه‌ی وضعیت را در `docs/phases/STATUS.md` بنویس (چه شد، چه ماند، تصمیم‌های تازه) تا نشست بعد ادامه دهد.

## ۲. منبع حقیقت و قواعد کار

- اسناد `docs/` منبع حقیقت‌اند. چیزی که در آن‌ها نیست را حدس نزن: بپرس، یا به‌عنوان `[ASSUMPTION]` در سند ثبت کن و به کاربر بگو.
- `[DECIDED]` را بدون تایید کاربر عوض نکن. اگر فکر می‌کنی غلط است، دلیل را بگو و منتظر جواب بمان.
- `[VERIFY]` یعنی از حافظه نوشته شده. قبل از پیاده‌سازی با مستندات رسمی تطبیق بده (`docs/vendors/<سرویس>/` و در صورت نبود، وب). تناقض را در همان سند اصلاح کن و گزارش بده. مستندات رسمی از سند ما معتبرتر است.
- `[OPEN]` را خودت تصمیم نگیر؛ قبل از رسیدن به آن بخش از کاربر بپرس.
- هر تغییر تصمیم یا ساختار = همان لحظه سند مربوط را به‌روز کن + یک خط در «تغییرات» همان سند. سند عقب‌مانده از کد ممنوع است.
- `docs/06-jalali-calendar.md` را **ویرایش نکن** و منطقش را «بهبود» نده.
- تناقض اسکیل‌ها با اسناد پروژه: اسناد پروژه برنده است و تناقض را گزارش کن.

### درخواست از کاربر
هر چه فقط کاربر دارد (فایل، کلید، تصمیم): قالب «⛔ نیاز به فایل/اطلاعات از شما» از `docs/00-README.md` بخش ۵. تا حد ممکن کار را متوقف نکن؛ با placeholder ادامه بده و علامتش بزن. هرگز کلید یا داده‌ی ساختگی شبیه واقعی نساز. بعد از رسیدن، `docs/01-assets-needed.md` را به‌روز کن.

### وابستگی‌های بیرونی: هیچ‌کدام کار را متوقف نمی‌کنند (D26)
کل ساختار همیشه کامل ساخته می‌شود. چیزی که هنوز نیست از `.env` یا ادمین می‌آید، `.env.example` همه‌ی نام‌ها را با مقدار خالی دارد، و تا رسیدنشان رفتار توسعه‌ی زیر برقرار است. هرگز به‌خاطر این‌ها از کاربر نپرس و کار را نگه ندار؛ فقط در گزارش آخر فاز بنویس چه چیزی هنوز خالی است.

| وابستگی | رفتار تا رسیدن آن |
|---------|-------------------|
| مرچنت‌کد زرین‌پال | `ZARINPAL_SANDBOX=true` (sandbox رسمی)، در نبود شبکه و برای تست خودکار `FakeGateway` (فقط `DEBUG`). گذار به واقعی فقط با `.env`، بدون تغییر کد |
| کلید و شناسه‌ی قالب‌های sms.ir | `SMS_BACKEND=console`؛ شناسه‌ی خالی = ارسال انجام نمی‌شود و `SmsLog(skipped_no_template)` ثبت می‌شود، نه خطا و نه شکست جریان اصلی |
| دامنه | `SITE_URL=http://localhost:8000`؛ همه‌ی آدرس‌های مطلق (callback پرداخت، sitemap، canonical، OG) از آن؛ قالب OTP بدون خط WebOTP |
| کلید نشان | نقشه غیرفعال، آدرس بدون مختصات |
| مشخصات فروشنده، متن صفحات ثابت، اینماد | فیلد خالی نمایش داده نمی‌شود |
| سوال‌ها و تایید `07` (ارسال) | با فروشنده است و خارج از پروژه؛ متن پیش‌فرض می‌ماند |
| فونت، sprite، عکس | فونت سیستم و placeholder |

فقط `manage.py check_launch` پیش از انتشار این‌ها را بررسی می‌کند (P6): ERROR برای چیزهای ناامن یا غیرقابل‌استفاده در prod، WARNING برای بقیه.

### سرّی‌ها
کلید و رمز را هرگز در کد، سند، لاگ یا commit نگذار. فقط `.env` (commit نمی‌شود) و `.env.example` (نام متغیرها بدون مقدار). نبودن متغیر لازم = خطای واضح در startup، نه رفتار بی‌صدا.

## ۳. زبان

- با کاربر: **فارسی**، کوتاه، بدون جارگون. نتیجه را بگو، نه ماجرا را.
- کد، نام‌ها، کامنت‌ها، پیام commit: **انگلیسی**.
- متن‌های رابط کاربر: فارسی، همه از فایل‌های ترجمه/قالب (نه رشته‌ی پراکنده در منطق). قواعد متن در `docs/04` بخش ۱۱.

## ۴. قواعد فنی ثابت (همیشه)

**داده**
- پول: `BigIntegerField` تومان. ریال فقط در لایه‌ی درگاه. هرگز float.
- زمان: UTC در دیتابیس، `TIME_ZONE="Asia/Tehran"`، `USE_TZ=True`. نمایش شمسی با ابزارهای `06`.
- سبد و سفارش روی `Variant`. سفارش snapshot کامل خریدار/گیرنده/آدرس/قیمت دارد.
- موجودی فقط با `UPDATE ... WHERE stock >= q` اتمیک و ثبت `StockMovement`. هیچ‌وقت read-modify-write.
- **هیچ تماس شبکه (پیامک، درگاه، نقشه) داخل تراکنش دیتابیس نباشد.** ارسال‌ها بعد از `transaction.on_commit`.
- تراکنش‌های نوشتن `IMMEDIATE`؛ کوتاه نگه دار.
- تغییر مدل‌های کش‌شونده فقط از طریق مسیرهایی که `rev` را بالا می‌برند (`save()`، `update_tracked`، `bulk_update_tracked`). `QuerySet.update()` خام روی آن‌ها ممنوع. (`docs/03` بخش ۵ و ۹)
- **وضعیت سفارش فقط از `services.transition` (حرکت‌های سیستمی) و `workflow.change_status` (حرکت‌های کارمند) عوض می‌شود.** `Order.objects...update()` بیرون از `apps/orders/services.py` ممنوع (تست معماری در `apps/catalog/tests/test_architecture.py`).
- نوشتن شمارنده‌ها (لایک، نظر، خرید) فقط از `apps/engagement/counters.py`.
- هر تغییر در مارک‌آپ قالب‌های کش‌شونده (`_product_card`، `_product_detail`، `_category_results`، `_similar`) = `FRAGMENT_VERSION` در `apps/catalog/constants.py` را +۱ کن.

**ابزارها (D27)**
- پایتون فقط با **`uv`**: `pyproject.toml` و `uv.lock`، `uv add`، `uv sync`، `uv run ...`. `pip`، `requirements.txt`، `poetry` و `venv` دستی ممنوع. ابزارهای توسعه در گروه `dev`.
- جاوااسکریپت فقط با **`pnpm`**: `package.json` و `pnpm-lock.yaml`، `pnpm add`، `pnpm install`، `pnpm run ...`. `npm` و `yarn` ممنوع. Node فقط برای ساخت CSS در توسعه/CI است و روی سرور production لازم نیست.
- هر وابستگی تازه با دلیل کوتاه (در پیام فاز) اضافه شود؛ چیزی که با چند خط کد می‌شود وابستگی نمی‌خواهد.

**امنیت**
- CSRF برای همه‌ی POSTها (HTMX با هدر). هر ورودی سمت سرور اعتبارسنجی می‌شود، حتی اگر کلاینت چک کرده باشد.
- OTP و درخواست‌های حساس: rate limit در Redis. پاسخ‌ها شمارش یا وجود کاربر را لو ندهند.
- `next` فقط مسیر داخلی (`url_has_allowed_host_and_scheme`).
- کد ملی قفل است (D20). فیلد پرشده پروفایل هرگز با داده‌ی فرم بازنویسی نمی‌شود (D07).
- بدون CDN خارجی. فونت، htmx، آیکون self-host.

- **رابط (D30، D31، D28):**
  - RTL: فقط کلاس‌های منطقی (`ms-/me-/ps-/pe-/start-/end-`).
  - موبایل: عمل اصلی پایین و سمت `start` (`docs/04` بخش ۴.۱).
  - رنگ و کامپوننت فقط از DaisyUI و توکن‌های `docs/04`. بدون `dark:` روی رنگ‌های DaisyUI.
  - HTMX: partialهای `_partial.html`، `request.htmx`، `hx-indicator` + `hx-disabled-elt`، رزرو ارتفاع برای بلوک‌های دیر آمده.
  - **ارقام (D30):** ذخیره، URL، فیلد hidden و ارتباط سرور ASCII است؛ نمایش و ورودی کاربر فارسی. `|fa_digits` برای عدد خالص، `|fa_text` برای متن آزاد، `.latin` فقط برای رشته‌های لاتین واقعی، `.num` برای اعداد فارسیِ چپ‌به‌راست (موبایل، کدپستی، تایمر).
  - **پنجره‌ها و اعلان‌ها (D31):** `alert()`، `confirm()`، `prompt()` و هر پنجره‌ی بومی مرورگر ممنوع است؛ همه‌چیز فقط از `MM.ui`. قبل از نوشتن JS، سند `docs/08-ui-modules.md` را بخوان.

## ۵. اسکیل‌ها (`skills/` در ریشه‌ی پروژه)

مسیر اسکیل‌ها `skills/` در ریشه‌ی پروژه است.

| اسکیل | چه وقت |
|-------|--------|
| `daisyui` | قبل از نوشتن هر قالب با کلاس DaisyUI. بخش `colors` و `usage` را کامل بخوان؛ فایل کامپوننت‌ها را هر وقت از آن استفاده می‌کنی. |
| `color-palette` | فقط اگر رنگی به سیستم اضافه می‌شود (`docs/04` بخش ۲). پالت فعلی نهایی است. |
| `unslop` | هر وقت صفحه‌ی تازه می‌سازی یا ظاهر را بازبینی می‌کنی؛ چک‌لیست انتهای آن را اجرا کن. |
| `htmx-patterns` | هر فاز با تعامل HTMX (از P1 به بعد). |
| `image-fetch` | فقط در توسعه، وقتی عکس واقعی از وب لازم است (مثلاً عکس نمونه‌ی محصول یا دسته برای دیدن UI). اجرا: `uv run python skills/image-fetch/scripts/imgfetch.py search "<query>" -n 5 -o <پوشه>`. خروجی برای انتشار نیست (حق نشر) و مدل‌ها `is_demo` می‌مانند. کلیدهای API عمداً داخل اسکریپت‌اند، استثنای قاعده‌ی «سرّی‌ها»، و مالک خودش عوضشان می‌کند. |

## ۶. تست و کیفیت

- هر فاز با تست و Definition of Done تمام می‌شود، نه با «نوشتم». تست‌ها را اجرا کن و خروجی را بخوان.
- `uv run pytest` (`pytest-django`). تست رفتار، نه پیاده‌سازی. برای هر قاعده‌ی «همیشه/هرگز» در اسناد یک تست بنویس.
- `uv run ruff check` و `uv run ruff format`. خروجی بدون خطا.
- UI: بررسی چشمی با کاربر است. مرورگر، Playwright و اسکرین‌شات اجرا نکن؛ در پایان هر فاز فهرست «چه چیزی باید دیده شود» را بده. grepهای `docs/04` بخش ۱۳ را خودت اجرا کن.
- تست فقط برای قاعده‌ی کسب‌وکار، پول و موجودی، امنیت و باطل‌سازی کش. تست رفتار فریم‌ورک و متن یا مارک‌آپ ثابت ننویس.
- کامیت: پیام انگلیسی، کوچک و مستقل. فقط وقتی کاربر خواست commit کن.

## ۷. دستورها

```
# نصب وابستگی‌ها:       uv sync  و  pnpm install  (همگام‌سازی خودکار Inter و htmx با postinstall)
# اجرای سرور توسعه:     uv run python manage.py runserver
# ساخت CSS:             pnpm run build:css  (یا pnpm run watch:css در توسعه)
# تست:                  uv run pytest
# lint/format:          uv run ruff check .  و  uv run ruff format .
# ساخت sprite:          uv run python scripts/build_sprite.py
# ساخت favicon:         uv run python scripts/make_favicons.py static/logo.webp static/favicon
# انقضای رزرو سفارش:    uv run python manage.py expire_orders  (هر ۵ دقیقه)
# پیامک «موجود شد»:      uv run python manage.py send_back_in_stock  (هر ۱۰ دقیقه؛ بازه‌ی ساعت در SiteSettings)
# بازسازی خرید ۳۰ روزه:  uv run python manage.py recount_purchases  (شبانه)
# بازسازی شمارنده‌ها:    uv run python manage.py reconcile_counters  (شبانه)
# گیت انتشار:            uv run python manage.py check_launch  (--strict: هشدار هم خطاست)
# پشتیبان دیتابیس:       uv run python manage.py backup_db --with-media  (شبانه؛ BACKUP_DIR بیرون پروژه)
# پاک‌سازی نگه‌داری:     uv run python manage.py purge_otp | purge_sms_logs  (شبانه)
# گروه‌های staff:        uv run python manage.py setup_groups  و  create_staff 0912... --group فروش
# دستورهای مدیریتی:     uv run python manage.py migrate | makemigrations | collectstatic
```

cron سرور در `deploy/crontab.example` است (یک فایل، بدون timer). استقرار و بازیابی: `docs/deploy.md`.

## ۸. ساختار پوشه‌ها

```
config/        env.py، settings/ (base/dev/prod)، urls.py، wsgi.py، asgi.py
apps/core/     مدل‌های پایه (SiteSettings، StaticPage، FooterLink)، jalali، text، validators، templatetags، tests
apps/cart/     سبد سرور (Cart/CartItem) و rules
apps/orders/   ShippingMethod، Order/OrderItem/OrderStatusLog، checkout، expire_orders، workflow (وضعیت کارمند)، notify، invoice
apps/payments/ PaymentGateway/Payment، gateways (zarinpal/fake)، callback، refund_candidates
apps/engagement/ Like/Review/ProductDailyStat/StockSubscription، counters.py (تنها نویسنده‌ی شمارنده‌ها)، social.py، wishlist، similar، back_in_stock
apps/marketing/ TrustItem، Banner، Collection/CollectionItem، HomeBlock، services (سرهم‌کردن صفحه‌ی اصلی و مجموعه)
apps/notifications/ SmsLog و adapter پیامک (console/smsir)، maintenance
templates/     base.html، 404.html، 500.html، admin/ (قالب‌های سفارش)، partials/ (_header، _dock، _footer، _logo، _brand_name، _section_heading)، pages/
static/        fonts/{vazir,inter,dastnevis}/، src/ (input.css، sprite.svg — در collectstatic ignore می‌شود)، css/app.css، js/{htmx.min.js,mm/*.js}، sprite.svg، logo.webp، favicon/
scripts/       build_sprite.py، make_favicons.py، sync_vendor.mjs
deploy/        malmal.service، nginx.conf.example، crontab.example
docs/          اسناد ۰۱ تا ۰۸، deploy.md، phases/، vendors/
Makefile       میانبرهای run، css، sprite، favicons، test، lint، format، check، seed، warm، search، expire، recount، reconcile، stock، launch، backup، purge
```

## ۹. وقتی فاز تمام شد

1. Definition of Done را یکی‌یکی با شواهد (خروجی تست؛ موارد چشمی در فهرست کاربر) بگذران.
2. اسناد را با واقعیت کد هم‌تراز کن و تغییرات را ثبت کن.
3. `docs/phases/STATUS.md` را به‌روز کن.
4. به کاربر در چند خط بگو: چه ساخته شد، چه مواردی `[ASSUMPTION]` یا `[VERIFY]` ماند، چه چیزی از او لازم است، قدم بعد.
