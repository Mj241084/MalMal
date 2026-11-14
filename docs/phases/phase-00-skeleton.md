# فاز P0 — اسکلت پروژه، پوسته‌ی رابط و ابزارهای پایه

**هدف:** پروژه‌ای که اجرا می‌شود، هر دو تم و RTL را درست نشان می‌دهد، پوسته‌ی سایت (هدر، dock، فوتر) دارد و همه‌ی ابزارهای مشترک بعدی (فونت، آیکون، شمسی، فیلترها، تست) آماده و تست‌شده است. هیچ منطق فروشگاهی در این فاز نیست.

## مطالعه
- `docs/00-README.md` (قواعد، پروتکل)، `docs/02-spec.md` بخش ۱، ۸ (هدر، فوتر)، ۱۴؛ تصمیم‌های D10, D11, D17, D19, D25
- `docs/03-data-model.md` بخش ۱، ۲، و `core` در بخش ۳، و «پیکربندی» در بخش ۵
- `docs/04-design-system.md` **کامل**
- `docs/06-jalali-calendar.md` (فقط ابزارهای سمت سرور و تست‌ها؛ انتخابگر JS در P5)
- اسکیل‌ها: `daisyui` (colors، config، navbar، dock، dropdown، drawer، toast)، `unslop` (`tokens.md` و چک‌لیست)، `htmx-patterns`

## بررسی اول (قبل از ساختن)
چک کن کاربر این‌ها را گذاشته است و هر چه نبود را با پروتکل «⛔» بخواه:
- `static/fonts/vazir/` (فایل‌های وزیر WOL؛ بپرس ارقام فارسی دارد یا نه، و وزن ۵۰۰ هست یا نه)
- `static/src/sprite.svg` (sprite کامل lucide؛ فرمت `<symbol id>` را چک کن)
- `static/logo.webp`
- `docs/vendors/` و اسناد `00` تا `07`، `skills/`

نبودن فونت یا sprite کار را متوقف نمی‌کند: با فونت سیستم و چند آیکون موقت ادامه بده و علامت بزن.

## کارها
1. **پروژه‌ی Django.** مدیریت پایتون فقط با `uv` (`pyproject.toml`، `uv.lock`، `.python-version`، گروه `dev` برای pytest، ruff، Pillow، fonttools؛ `pip`/`requirements.txt` ممنوع). پوشه‌ی `config/` (تنظیمات `base/dev/prod`)، اپ‌ها طبق `03` بخش ۲ (فقط `core` در این فاز پر می‌شود؛ بقیه را وقتی لازم شد بساز). نسخه‌ی Django را انتخاب کن (حداقل ۵.۱ برای `transaction_mode`، ترجیحاً آخرین LTS) و انتخاب را در سند ثبت کن `[VERIFY]`.
2. **تنظیمات.**
   - `LANGUAGE_CODE="fa"`، `TIME_ZONE="Asia/Tehran"`، `USE_TZ=True`.
   - SQLite: WAL، `synchronous=NORMAL`، `busy_timeout=5000`، `foreign_keys=ON`، `transaction_mode=IMMEDIATE` `[VERIFY]`؛ چک FTS5 در startup (`03` بخش ۱).
   - نشست `signed_cookies`، `HttpOnly`، `SameSite=Lax`، `Secure` در prod.
   - کش Redis (`RedisCache` داخلی Django) با پیشوند کلید `mm:v1:`؛ DB جدا برای rate limit (`03` بخش ۵ «پیکربندی»).
   - متغیرهای env: همه‌ی نام‌های `docs/01` بخش B در `.env.example` با مقدار خالی و توضیح یک‌خطی (`DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `SITE_URL`, `REDIS_URL`, `ADMIN_URL`, `SMS_BACKEND`, `SMSIR_*`, `NESHAN_*`, `ZARINPAL_*`, `SMS_ADMIN_MOBILES`). فقط نبودن `DJANGO_SECRET_KEY` و `REDIS_URL` در prod خطای startup است؛ بقیه هرگز اجرا را متوقف نمی‌کنند (D26). `.gitignore` شامل `.env`.
   - مسیر ادمین از `ADMIN_URL` (پیش‌فرض dev: `admin/`).
3. **ساخت فرانت.** Tailwind v4 + DaisyUI 5 طبق `04` بخش ۸ (فایل `input.css` همان‌جا آمده؛ نام فایل‌های فونت و `@source` را تنظیم کن). ساخت CSS فقط با `pnpm` (`package.json`، `pnpm-lock.yaml`؛ `npm`/`yarn` ممنوع): Tailwind v4 و DaisyUI از registry؛ `[VERIFY]` با مستندات هر دو. Node فقط برای ساخت در توسعه/CI است؛ CSS ساخته‌شده deploy می‌شود و روی سرور Node لازم نیست. هیچ CDN در زمان اجرا. htmx را self-host کن (نسخه‌ی ثابت، `[VERIFY]` آخرین نسخه‌ی پایدار) و `django-htmx` را وصل کن.
4. **فونت.** Vazir از فایل‌های کاربر. Inter: `unicode-range` فقط حروف و ارقام ASCII؛ فایل Latin-subset را با `pnpm` از بسته‌ی رسمی بگیر (مثلاً `@fontsource/inter`) و در `static/fonts/inter/` بگذار. اگر شبکه نبود، «⛔».
5. **آیکون.** `scripts/build_sprite.py`: از `static/src/sprite.svg` می‌خواند، قالب‌ها را برای `{% icon "name" %}` اسکن می‌کند و sprite بهینه می‌سازد. تگ `{% icon "name" size=18 flip=False %}` (بخش ۶ `04`: stroke ۱٫۵، جهت‌دار → `rtl:-scale-x-100`). نماد ناموجود در DEBUG خطا. `static/src/` در `collectstatic` ignore شود.
6. **favicon و لوگو.** بسته‌ی `favicon-kit` را به `scripts/make_favicons.py` و `static/favicon/` ببر. partial `_logo.html` تنها نقطه‌ی ارجاع لوگو (لوگوی تاریک یا `invert` در تم تاریک، `04` بخش ۸ و ۱۲). `<head>`: favicon، `apple-touch-icon`، `site.webmanifest`، دو `theme-color`، `og-default`؛ مسیر `/favicon.ico` ریدایرکت.
7. **ابزارهای مشترک** (همه با تست):
   - `core/jalali.py`، `core/jalali_forms.py` و تگ‌های `to_jalali`/`fa_digits` طبق `06` (به‌جای `pip install jdatetime` سند: `uv add jdatetime`؛ خود سند `06` عوض نمی‌شود). تست‌های ۹.۱ و بررسی ۹.۲ پاس شود. (انتخابگر JS در P5.)
   - `core/text.py`: `normalize_fa` (ی/ک عربی → فارسی، ارقام فارسی/عربی → انگلیسی، نیم‌فاصله، فاصله‌های اضافه) برای ورودی و جستجو.
   - فیلتر `toman` (`۱٬۲۵۰٬۰۰۰`)، `fa_digits`، اعتبارسنجی کد ملی (رقم کنترل) و موبایل ایران (`09xxxxxxxxx`، با نرمال‌سازی).
8. **مدل‌های `core`.** `SiteSettings` (singleton، کش‌شده، با `trust_marks_html`)، `StaticPage` (با `needs_review`)، `FooterLink` با ادمین. مسیر `/pages/<slug>/`.
9. **قالب پایه.** `base.html`، هدر موبایل و دسکتاپ (دو ردیف)، dock موبایل، فوتر (از `SiteSettings` و `FooterLink`)، `#toasts`، انتخاب تم (`04` بخش ۸) و اسکریپت inline ضد چشمک، پیکربندی HTMX (هدر CSRF، رفتار خطا)، صفحه‌های ۴۰۴ و ۵۰۰. جستجو و سبد در هدر فعلاً ظاهر بدون منطق است؛ دسته‌ها فعلاً از دیتای نمونه.
10. **صفحه‌ی `/_styleguide/`** (فقط `DEBUG`): توکن‌های رنگ، تایپ، دکمه، فیلد، کارت محصول (دیتای ساختگی)، badge/status، toast و skeleton در هر دو تم. با آن چک‌لیست `04` بخش ۱۳ را اجرا کن.
11. **زیرساخت تست و کیفیت.** `pytest-django` و `ruff` با `uv run`؛ دستورهای ساده (Makefile یا مشابه) که `uv`/`pnpm` را صدا می‌زنند. بخش ۷ و ۸ `CLAUDE.md` را پر کن.

## خارج از این فاز
مدل‌های کاتالوگ، کاربر، سبد؛ جستجو؛ پیامک؛ هر منطق فروشگاهی. انتخابگر شمسی JS (P5).

## Definition of Done
- [ ] `runserver` و ساخت CSS بدون خطا؛ صفحه‌ی اصلی خالی با هدر/dock/فوتر در هر دو تم و `۳۲۰`/`۱۲۸۰` درست دیده می‌شود (اسکرین‌شات).
- [ ] grepهای `04` بخش ۱۳ صفر نتیجه.
- [ ] تست‌های `06` (۹.۱) و بررسی کبیسه (۹.۲) پاس؛ تست `normalize_fa`، `toman`، کد ملی، موبایل.
- [ ] sprite: یک آیکون جدید در قالب → اسکریپت آن را می‌گیرد؛ آیکون جهت‌دار در RTL برعکس است؛ نماد ناموجود در DEBUG خطا می‌دهد.
- [ ] فونت: مثال «Samsung ۱۲۳ مدل WM-1450» → حروف و ارقام لاتین Inter، فارسی وزیر (در DevTools تایید شود).
- [ ] تغییر تم (روشن/تاریک/سیستم) ماندگار و بدون چشمک؛ در `localStorage` ناموجود هم کار می‌کند.
- [ ] هیچ منبع خارجی در Network (بررسی شود).
- [ ] نبودن `DJANGO_SECRET_KEY`/`REDIS_URL` در prod با پیام واضح fail می‌کند؛ نبودن هر متغیر دیگر اجرا را متوقف نمی‌کند. `.env.example` شامل همه‌ی نام‌های `docs/01`، `.env` در git نیست.
- [ ] نصب از صفر فقط با `uv sync` و `pnpm install` کار می‌کند؛ `pip`، `npm`، `yarn` و `requirements.txt` در پروژه نیست.
- [ ] `CLAUDE.md` بخش ۷ و ۸ پر؛ `docs/01` به‌روز (A1، A2، A3 دریافت‌شده/پردازش‌شده).
