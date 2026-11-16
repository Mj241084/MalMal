# ۰۸ — ماژول‌های UI سمت کلاینت (`window.MM`) — نسخه ۰.۸

هر سشن قبل از نوشتن JS این سند را می‌خواند. هر تغییر در ماژول‌ها = به‌روزرسانی همین سند در همان تغییر
(تست `test_every_mm_module_is_documented` فایل‌های بدون ردیف را رد می‌کند).

## قواعد (D31)
1. `alert()`، `confirm()`، `prompt()` و `hx-confirm` با رفتار بومی ممنوع‌اند. `hx-confirm` فقط چون
   `ui.js` آن را به دیالوگ ما وصل می‌کند مجاز است.
2. JS inline ممنوع است (بدون `onclick`). رفتار با attribute `data-*` و ماژول وصل می‌شود.
3. هر مقدار `initializer` باید idempotent باشد و با `MM.init(name, fn)` ثبت شود (روی swapهای HTMX هم اجرا می‌شود).
4. متن‌های رابط فارسی و بی‌نقطه‌ی پایانی (`04` بخش ۱۱).

## ماژول‌ها
| ماژول | فایل | API عمومی | قرارداد HTML |
|-------|------|-----------|--------------|
| MM.fmt، MM.init، MM.each | `core.js` | `fmt.faDigits(s)`، `fmt.enDigits(s)`، `init(name, fn)`، `each(root, sel, fn)` | — |
| MM.ui | `ui.js` | `toast(msg, {level, timeout})`، `confirm(str\|opts) → Promise<bool>`، `alert(...)`، `dialog.open/close(id)` | `#mm-dialog` در `base.html`؛ `hx-confirm` + `data-confirm-title/label/cancel/tone`؛ `<form data-confirm>`؛ `[data-dialog-close]`؛ `[data-print]` (چاپ صفحه، مثل فاکتور) |
| forms | `forms.js` | — (فقط attribute) | `data-fa-digits`، `data-digits-only`، `data-autofocus`، `data-focus-on-swap`؛ در `htmx:configRequest` مقدار فیلدهای `[data-fa-digits][name]` به ارقام ASCII تبدیل می‌شود (URL و سرور فقط ASCII می‌بینند) |
| theme | `theme.js` | — | `[data-theme-choice]` |
| shell | `shell.js` | `window.malmalSetCartCount(n)` | `[data-cart-count]`، `#search-suggest` (پنل پیشنهاد با `htmx:afterSwap` و `MM.init` هم‌زمان sync می‌شود)، `[data-rail-scroll="±1"]` + `data-rail="<id track>"` (فلش ریل، جهت با `direction` واقعی)، `[data-demo-*]`؛ `details.dropdown` با کلیک بیرون و Escape بسته می‌شود |
| auth | `auth.js` | `MM.auth.open(next)` | `[data-auth-open]`، `#auth-modal`، `#auth-modal-body` |
| likes | `likes.js` | `MM.likes.loadState(root)` | `[data-like="<id محصول>"]` (دکمه‌ی قلب با `aria-pressed`)، `data-like-seen`، `#social-product[data-product]`؛ مهمان: قلب در `localStorage` (`malmal.like.pending`، ۱۵ دقیقه) می‌ماند و بعد از ورود اعمال می‌شود |
| otp | `otp.js` | `MM.otp.build(input)`، `MM.otp.startTimer(el)` | `[data-otp]` + `data-otp-length`، `data-otp-submit`؛ `[data-otp-timer]` + `data-seconds`، `data-otp-resend` |
| addresses | `addresses.js` | — | `[data-address-add]`، `[data-address-cancel]`، `#address-form-container` |
| cart | `cart.js` | `MM.cart.read()`، `MM.cart.clear()` | `[data-cart-add]`، `[data-cart-idle]`، `[data-cart-active]`، `[data-cart-step="1\|-1"]`، `[data-cart-qty]`، `[data-cart-minus]`، `[data-cart-trash]`، `[data-cart-set]` با `data-variant`/`data-qty`، `[data-cart-items]`، `[data-guest-cart]`، `#cart-content`، `#cart-state`، `#variant-panel[data-variant-id\|data-variants\|data-max\|data-orderable\|data-price]`، `[data-bar-price]`؛ رویداد `cart:changed` از سرور (برای خط سبد `variant` و `qty` هم دارد)؛ برای کاربر واردشده از `GET /cart/state/` و `POST /cart/line/` استفاده می‌شود |
| gallery | `gallery.js` | — (فقط attribute) | `[data-gallery]`، `[data-gallery-track]`، `[data-gallery-slide]`، `[data-gallery-prev\|next\|zoom\|counter\|thumb]`، `img[data-full]`، و `#gallery-lightbox[data-lightbox]` با `[data-lb-stage\|image\|counter\|prev\|next\|zoom-in\|zoom-out]` |
| neshan | `neshan.js` | — | `[data-neshan-picker]` (فقط وقتی `NESHAN_MAP_KEY` هست) |
| slider | `slider.js` | — (فقط attribute) | `[data-slider]` + `data-autoplay` (میلی‌ثانیه)، `[data-slider-track]`، `[data-slider-prev]`، `[data-slider-next]`، `[data-slider-dot]` |

## ماژول‌های پنل (برنامه‌ریزی‌شده — P9/P11)
اسکریپت‌های پنل فقط در `templates/panel/base.html` بارگذاری می‌شوند، نه در `base.html` فروشگاه (`09` بخش ۲.۳، `10` بخش ۱۰). هر فاز هنگام ساخت فایل، ردیف را قطعی می‌کند (رفع «برنامه‌ریزی‌شده»). تا آن موقع فایلی وجود ندارد و `test_every_mm_module_is_documented` چیزی از آن‌ها نمی‌خواهد.

| ماژول | فایل | API عمومی | قرارداد HTML | وضعیت |
|-------|------|-----------|--------------|-------|
| panel | `panel.js` | — (فقط attribute و رویداد) | پل toast برای `HX-Trigger: {"mm:toast": {...}}` به `MM.ui.toast`؛ `[data-copy]` (کپی در کلیپ‌بورد)؛ `[data-toman-hint]` (نمایش زنده‌ی «۱٬۲۵۰٬۰۰۰ تومان»)؛ `[data-discount-from]` (٪ تخفیف زنده) | برنامه‌ریزی‌شده — P9 |
| upload | `upload.js` | — (فقط attribute) | `[data-dropzone]` (drop ← `input.files` ← رویداد `change`)؛ ارسال نوبتی حداکثر ۳ فایل؛ نوار پیشرفت | برنامه‌ریزی‌شده — P11 |
| richtext | `richtext.js` | بسته به D46 `[OPEN]` | بسته به D46؛ اگر textarea ساده بماند این فایل ساخته نمی‌شود | برنامه‌ریزی‌شده — P11 (مشروط به D46) |

همه با `MM.init(name, fn)` ثبت می‌شوند و idempotent‌اند (قاعده‌ی ۳ بالا). دیالوگ مشترک `#mm-dialog` از P9 در partial `partials/_mm_dialog.html` است و هر دو base (فروشگاه و پنل) آن را include می‌کنند؛ قرارداد `MM.ui` عوض نمی‌شود.

## پروتکل توسعه
1. اول این جدول را بخوان. اگر ماژول کارت را می‌کند، همان را صدا بزن.
2. اگر فقط یک گزینه کم است: همان تابع را **سازگار با گذشته** گسترش بده (پارامتر یا attribute اختیاری؛
   رفتار پیش‌فرض عوض نشود)، ردیف جدول را به‌روز کن و نمونه را به `/_styleguide/` اضافه کن.
3. اگر چیز تازه‌ای لازم است: فایل جدید `static/js/mm/<name>.js` با ثبت در `MM.<name>`، ردیف در این جدول،
   تگ `<script defer>` در `base.html` (یا `extra_js` اگر فقط یک صفحه نیاز دارد) و نمونه در styleguide.
4. تغییر ناسازگار فقط با grep روی همه‌ی استفاده‌ها و ثبت در «تغییرات».

## تغییرات
- ۰.۸ — بخش «ماژول‌های پنل»: ردیف‌های برنامه‌ریزی‌شده‌ی `panel.js` (P9)، `upload.js` و `richtext.js` (P11)، و استخراج `#mm-dialog` به `partials/_mm_dialog.html` (بدون تغییر رفتار).
- ۰.۷ — stepper سبد در صفحه‌ی محصول، گالری با فلش و لایت‌باکس زوم‌دار (`gallery.js`).
- ۰.۶ — P7: `shell.js` پنل پیشنهاد جستجو را بعد از swap سینک می‌کند، `details.dropdown` را با کلیک بیرون/Escape می‌بندد و فلش ریل `[data-rail-scroll]` گرفت؛ `forms.js` پارامترهای HTMX را ASCII می‌کند؛ `cart.js` قفل دکمه را بعد از خطای شبکه باز می‌کند و `syncing` را با `htmx:responseError`/`sendError` ریست می‌کند؛ `likes.js` بعد از لایک معلق، متن اجتماعی صفحه‌ی محصول را دوباره می‌گیرد.
- ۰.۵ — `[data-print]` در `ui.js` (دکمه‌ی چاپ فاکتور، بدون JS درون‌خطی).
- ۰.۴ — `slider.js` (اسلایدر بنر صفحه‌ی اصلی).
- ۰.۳ — `likes.js`؛ `MM.auth.open(next)` (باز کردن مودال ورود از کد، برای مهمانی که لینکی برای کلیک ندارد).
- ۰.۲ — ردیف `cart`/`cart.js` (سبد مهمان در `localStorage`، افزودن/تغییر تعداد، ادغام هنگام تایید OTP).
- ۰.۱ — ساخت سند؛ تقسیم `app.js` به ماژول‌ها؛ `MM.ui.confirm/alert`؛ `otp.js`.
