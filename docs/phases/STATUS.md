# وضعیت فازها

این فایل را Claude Code در پایان هر نشست به‌روز می‌کند تا نشست بعد بداند کجا هستیم.

| فاز | وضعیت | یادداشت |
|-----|-------|---------|
| P0 اسکلت | ✅ تمام‌شده | Django 5.2.19، Tailwind v4.3.5 + DaisyUI 5.7.50، HTMX 2.0.11، Vazirmatn NL + Inter Latin + Dastnevis (`font-brand`)، sprite بهینه، ابزارهای شمسی `06` و تست‌ها، `core` مدل‌ها/ادمین/قالب پایه/styleguide، تنظیمات تست ایزوله (`config.settings.test`)، ۴۷ تست پاس، بررسی Playwright در دو تم و عرض ۳۲۰/۱۲۸۰ |
| P1 کاتالوگ | ✅ تمام‌شده | اپ `catalog` (Brand/Category/Product/Variant/ProductImage/Spec*/StockMovement) + اپ `search` (FTS5)، درخت materialized-path با کوئری بازه، کش نسخه‌دار با گروه‌های LIST/DETAIL/COUNTER/STRUCTURAL و single-flight، صفحه‌ی دسته/محصول/برند/جستجو با HTMX، پیشنهاد زنده، JSON-LD، تصاویر WebP چنداندازه، `seed_demo`/`warm_cache`/`rebuild_search`؛ ۸۳ تست پاس، ruff پاک |
| P2 حساب کاربری | ✅ تمام‌شده | احراز هویت با پیامک (OTP ۴ رقمی)، مدل اختصاصی کاربر با شناسه‌ی موبایل ۰۹، قفل کد ملی پس از ثبت، خروج از همه‌ی دستگاه‌ها، مدیریت آدرس‌ها با آدرس پیش‌فرض یکتا، دیتاست ۳۱ استان و ۴۷۶ شهر ایران، پیوند کوتاه بدون جدول `apps/core/shortlinks.py` (`r/<kind><pk base36>` مثل `r/p3a7` — D32)، ویجت‌های ارقام فارسی `FaDigitsInput`/`FaTextInput`/`FaTextarea` و فیلتر `fa_text` (D30)، ماژول‌های کلاینت `static/js/mm/` و دیالوگ/اعلان غیربومی `MM.ui` (`docs/08-ui-modules.md` — D31) و جعبه‌های ۴ رقمی `MM.otp`، نگهداری وضعیت مرحله‌ی کد در نشست سرور (`otp_pending` و `otp_cancel`)، پاک‌سازی داده‌های قدیمی (`purge_otp_challenges` و `purge_sms_logs` — D33)، چک استقرار `notifications.E001`، هدرهای `private` و `ETag` به‌ازای بیننده در کاتالوگ، پراکسی امن reverse geocode نشان و picker نقشه بدون افشای کلید سرویس |
| P3 checkout | ⏳ | |
| P4 تعامل | ⏳ | |
| P5 صفحه‌ی اصلی | ⏳ | |
| P6 انتشار | ⏳ | |

## تصمیم‌های تازه و موارد باز بین نشست‌ها
- فونت کاربر `Vazirmatn[wght].woff2` است (متغیر ۱۰۰ تا ۹۰۰، بدون لاتین، دارای ارقام فارسی `۰-۹`) و در `@font-face` با `font-weight: 400 500` استفاده شد.
- فونت برند `static/fonts/dastnevis/dastnevis.woff2` (تک‌وزن ۴۰۰، `--font-brand`) فقط برای نام نمایشی «مل‌مل» از طریق `{% brand_name %}` / `_brand_name.html` استفاده می‌شود و به دلیل نداشتن گلیف `U+200C` روی نیم‌فاصله به دو `<span class="font-brand-seg">` شکسته می‌شود.
- تست‌ها از `config.settings.test` با پیشوند Redis مجزا (`mm:test`) استفاده می‌کنند تا کش dev (`mm:v1`) آلوده نشود.
- در کارت محصول روی کاشی سفید (`bg-white`)، دکمه‌ی قلب دارای پس‌زمینه‌ی `bg-base-100 border` شد تا در تم تاریک کنتراست کامل حفظ شود.
- هم‌خوانی کبیسه‌ی کلاینت (`Intl.DateTimeFormat`) و سرور (`jdatetime`) برای سال‌های ۱۳۸۰ تا ۱۴۵۰ صددرصد یکسان بود.
- متغیرهای `.env` (مثل `DJANGO_SECRET_KEY`، `REDIS_URL` و کلیدهای بیرونی) در محیط محلی کاربر باید طبق `.env.example` ساخته شوند؛ فعلاً `dev.py` با مقدار پیش‌فرض توسعه و `redis://127.0.0.1:6379/1` کار می‌کند.
- **P1:** `bm25` در SQLite به تعداد ستون‌ها وزن می‌خواهد؛ ستون `UNINDEXED` وزن ۰ گرفت (`bm25(product_fts, 0, 10, 5, 3, 8, 1)`).
- **P1:** `StockMovement.order_item_id` موقتاً عدد است؛ در P3 با ساخته شدن اپ `orders` به FK تبدیل می‌شود.
- **P1:** `_snapshot_tracked` مقادیر را از `__dict__` می‌خواند تا نمونه‌های `only()/defer()` باعث `refresh_from_db` بازگشتی نشوند.
- **P1:** نتایج لیست دسته به‌صورت HTML رندرشده با کلید `c:{id}:{subtree_rev}:list:{sort}:{filters_hash}:{page}` کش می‌شود؛ به همین دلیل partialهای کش‌شده نباید به `request` وابسته باشند (querystring صفحه‌بندی از `ProductFilter.querystring()` می‌آید).
- **P1:** دیتای نمونه با `manage.py seed_demo` ساخته می‌شود (۱۲ محصول، ۴ درخت دسته، عکس placeholder) و با `seed_demo --clear` پاک می‌شود؛ در `DEBUG=False` بدون `--force` اجرا نمی‌شود.
- **P1 باقی‌مانده برای P3/P4:** دکمه‌ی «افزودن به سبد» و قلب علاقه‌مندی عمداً `disabled` هستند؛ بلوک محصولات مشابه و متن اجتماعی رندر نمی‌شوند.
- **P1 (اصلاحات پیش از بستن):** ناحیه‌ی شست (D28) در نوار چسبان صفحه‌ی محصول اعمال شد (دکمه `start`، قیمت `end`، قیمت ناشکستنی). `Variant.max_per_order` به null/blank تغییر کرد و `max_orderable` اضافه شد (D29). اپ `marketing` با `TrustItem` ساخته شد (۴ ردیف placeholder در مهاجرت داده) و متن ارسال از `SiteSettings.shipping_note` می‌آید؛ گارانتی محصول به تب مشخصات رفت. `trust_rev` بخشی از کلید کش جزئیات محصول است. اصلاحات ظاهری: breadcrumb موبایل بدون اسکرول افقی با truncate، شمارنده‌ی سبد در صفر پنهان (`invisible`)، ردیف‌های فیلتر برند ۳۶px با عدد چسبیده، اسپینر مرتب‌سازی از لبه‌ی گرید برداشته شد.
- **P1 (فونت برند):** بررسی `fontTools` نشان داد `dastnevis.woff2` گلیف `U+200C` و `U+200D` ندارد؛ پس شکستن نام به دو `span.font-brand-seg` با `margin-inline-start: 0.12em` (پیاده‌سازی `{% brand_name %}`) راه‌حل درست است و نیم‌فاصله هرگز به فونت نمی‌رسد. تایید بصری نهایی با کاربر است.
- **P2 (اصلاحی P2-ب، D30 تا D33):** مدل/جدول `ShortLink` حذف شد (`core/0005_remove_shortlink`) و پیوند کوتاه پیامک بدون جدول با `apps/core/shortlinks.py` (`short_link_param("p", pk)` → `r/p3a7`) پیاده‌سازی شد (D32). تفکیک کامل ارقام نمایشی فارسی و داده‌ی سروری ASCII با ویجت‌های `FaDigitsInput`/`FaTextInput`/`FaTextarea`، `to_fa_text` و `.num`/`.latin` انجام شد (D30). پنجره‌های بومی مرورگر با ماژول‌های `static/js/mm/` (`MM.ui`، `MM.otp`، `MM.fmt` و `#mm-dialog`) و مستند `docs/08-ui-modules.md` جایگزین شدند (D31). وضعیت مرحله‌ی کد OTP به‌جای `sessionStorage` و `/auth/otp/resume/` در نشست سرور (`otp_pending` + `POST /auth/otp/cancel/`) نگه‌داری می‌شود. توابع نگهداری و اکشن ادمین `purge_otp_challenges` (۱ روز پس از انقضا) و `purge_sms_logs` (۹۰ روز) اضافه شدند (D33). چک استقرار `notifications.E001` برای `SMS_BACKEND=console` ثبت شد و صفحات کاتالوگ هدر `Cache-Control: private` و `ETag` به‌ازای بیننده گرفتند.
- **P2 (نقشه):** رجیستری npm نشان (`npm.neshan.org`) در دسترس نبود؛ طبق بریف SDK رسمی نقشه فقط در حضور `NESHAN_MAP_KEY` از CDN رسمی بارگذاری می‌شود.
- **P6 (یادداشت کارهای آینده):** تایمر/کران دوره‌ای P6 باید `purge_otp_challenges` و `purge_sms_logs` را صدا بزند؛ `check_launch` روی چک استقرار `notifications.E001` (`SMS_BACKEND=console`) تکیه دارد و آن را هم‌سطح ERROR می‌بیند.
- **بسته‌شده:** خط قاعده‌ی موبایل D28 («موبایل: عمل اصلی پایین و سمت `start` — `docs/04` بخش ۴.۱») به بخش ۴ `CLAUDE.md` اضافه شد.
