# کار: صفحه‌ی «راهنما» در پنل (فقط مدیر کل)

فقط همین کار را انجام بده. هر چیز بیرون از این بریف ممنوع است.

## مطالعه (فقط این‌ها)
- CLAUDE.md
- docs/10-panel-ui.md بخش ۲ و ۱۲
- docs/04-design-system.md بخش ۱۳ (فقط grepها)
اسناد و اسکیل‌های دیگر را نخوان. مرورگر و Playwright اجرا نکن.

## تغییرات مجاز (دقیقاً همین‌ها)

1. apps/panel/nav.py
   بلافاصله بعد از NavItem مربوط به "system" این را اضافه کن:
   NavItem("guide", "راهنما", "panel:guide", icon="book-open", group="admin", superuser=True)
   - اگر "book-open" در static/src/sprite.svg نبود، به‌جایش "file-text" بگذار و در گزارش بنویس.
   - هیچ گروه ناوبری تازه نساز. هیچ آیتم دیگری را جابه‌جا نکن.

2. apps/panel/views/guide.py (فایل تازه)
   فقط یک view به این شکل:
   - `from __future__ import annotations`
   - importها: render، require_GET، panel_view (از apps.panel.permissions)
   - @panel_view(superuser=True) بیرونی‌ترین دکوراتور، بعد @require_GET
   - def guide(request): return render(request, "panel/guide.html")
   - بدون context، بدون کوئری، بدون import دیگر.

3. apps/panel/urls.py
   - guide را به importهای `from .views import (...)` به ترتیب الفبا اضافه کن (بعد از dashboard).
   - در انتهای urlpatterns اضافه کن: path("guide/", guide.guide, name="guide"),

4. templates/panel/guide.html (فایل تازه)
   - محتوایش دقیقاً همان متنی است که کاربر همراه این بریف داده است. کلمه‌ای از آن را عوض نکن.
   - فقط اگر یکی از grepهای docs/04 بخش ۱۳ یا رندر قالب خطا داد، کمترین اصلاح ممکن را در همین فایل انجام بده و در گزارش دقیقاً بنویس چه چیزی و چرا.
   - ممنوع در این فایل: <strong>، <b>، font-bold، font-semibold، italic، کلاس‌های فیزیکی RTL (ml- mr- pl- pr- left- right- text-left text-right)، dark:، گرادیان و سایه‌ی رنگی، رنگ هگز، style درون‌خطی، script، ایموجی، alert/confirm/prompt.
   - ارقام نمایشی همه فارسی هستند. هیچ رقم ASCII در متن نباید باشد (توکن‌های لاتین مثل SKU داخل class="latin").

5. بازسازی خروجی‌ها
   - uv run python scripts/build_sprite.py (باید با کد ۰ تمام شود و book-open در static/sprite.svg باشد)
   - pnpm run build:css
   - بعد از build:css بررسی کن این کلاس‌ها در static/css/app.css هستند: list-disc، scroll-mt-20، gap-y-1. اگر نبود، input.css را دست نزن؛ فقط گزارش کن.
   - فایل‌های ساخته‌شده را با دست ویرایش نکن.

6. اسناد (هر مورد فقط یک خط)
   - docs/10-panel-ui.md: در فهرست گروه‌های ناوبری (بخش ۲) «راهنما (فقط مدیر کل)» را کنار «مدیریت» اضافه کن و در «تغییرات» یک خط بنویس («۰.۲ — صفحه‌ی راهنما»).
   - docs/09-panel-spec.md: فقط یک خط در بخش «تغییرات»: «راهنما: /panel/guide/، فقط مدیر کل؛ قالب ایستا است و هر فازی که رفتار پنل را عوض کند باید templates/panel/guide.html را هم به‌روز کند».
   - docs/phases/STATUS.md: یک ردیف تازه برای این کار.

## ممنوع
- دست‌زدن به مدل، مهاجرت، setup_groups، JS، view و قالب دیگر، تنظیمات، providerهای جستجو، بج‌ها، داشبورد.
- نوشتن تست تازه (ماتریس apps/panel/tests/test_p15.py و test_access.py این مسیر را پوشش می‌دهند).
- افزودن وابستگی، commit، باز کردن مرورگر.
- «بهبود» متن یا ساختار guide.html.
- اصلاح هر خطای نامرتبط که در حین اجرا دیدی (فقط گزارش کن).

## اجرا و تایید
- uv run pytest apps/panel apps/core/tests/test_ui_rules.py -q  ← سپس uv run pytest کامل
- uv run ruff check .
- uv run ruff format --check . ← اگر فقط فایل‌های همین کار نیاز به format داشتند، فقط همان‌ها را format کن. اگر فایل دیگری هم نشان داده شد، دست نزن و گزارش کن.
- grepهای docs/04 بخش ۱۳ را روی templates/panel/guide.html اجرا کن.
- اگر هر مرحله شکست خورد، متوقف شو و گزارش کن. با تغییر فایل‌های دیگر دور نزن.

## گزارش پایانی (کوتاه، فارسی)
۱. فهرست فایل‌های تغییر‌کرده (باید دقیقاً با فهرست بالا یکی باشد؛ هر تفاوت را توضیح بده)
۲. خروجی تست، ruff و grepها (عدد)
۳. هر انحراف از بریف (مثلاً آیکون جایگزین) با دلیل
۴. فهرست «چه چیزی باید دیده شود» برای کاربر:
   - مدیر کل: لینک «راهنما» بعد از «سیستم» در سایدبار؛ صفحه در دو تم و عرض ۳۲۰ و ۱۲۸۰ بدون اسکرول افقی؛ لینک‌های فهرست بالا به بخش درست می‌روند و عنوان بخش زیر هدر چسبان نمی‌ماند؛ جدول‌ها در موبایل داخل قاب خودشان اسکرول می‌شوند
   - کاربر گروه «فروش» یا «محتوا»: لینک راهنما در منو نیست و باز کردن مستقیم /panel/guide/ صفحه‌ی ۴۰۳ می‌دهد
