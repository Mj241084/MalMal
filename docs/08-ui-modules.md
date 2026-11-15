# ۰۸ — ماژول‌های UI سمت کلاینت (`window.MM`) — نسخه ۰.۴

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
| MM.ui | `ui.js` | `toast(msg, {level, timeout})`، `confirm(str\|opts) → Promise<bool>`، `alert(...)`، `dialog.open/close(id)` | `#mm-dialog` در `base.html`؛ `hx-confirm` + `data-confirm-title/label/cancel/tone`؛ `<form data-confirm>`؛ `[data-dialog-close]` |
| forms | `forms.js` | — (فقط attribute) | `data-fa-digits`، `data-digits-only`، `data-autofocus`، `data-focus-on-swap` |
| theme | `theme.js` | — | `[data-theme-choice]` |
| shell | `shell.js` | `window.malmalSetCartCount(n)` | `[data-cart-count]`، `#search-suggest`، `[data-demo-*]` |
| auth | `auth.js` | `MM.auth.open(next)` | `[data-auth-open]`، `#auth-modal`، `#auth-modal-body` |
| likes | `likes.js` | `MM.likes.loadState(root)` | `[data-like="<id محصول>"]` (دکمه‌ی قلب با `aria-pressed`)، `data-like-seen`، `#social-product[data-product]`؛ مهمان: قلب در `localStorage` (`malmal.like.pending`، ۱۵ دقیقه) می‌ماند و بعد از ورود اعمال می‌شود |
| otp | `otp.js` | `MM.otp.build(input)`، `MM.otp.startTimer(el)` | `[data-otp]` + `data-otp-length`، `data-otp-submit`؛ `[data-otp-timer]` + `data-seconds`، `data-otp-resend` |
| addresses | `addresses.js` | — | `[data-address-add]`، `[data-address-cancel]`، `#address-form-container` |
| cart | `cart.js` | `MM.cart.read()`، `MM.cart.clear()` | `[data-cart-add]`، `[data-cart-label]`، `[data-cart-set]` + `data-variant`/`data-qty`، `[data-cart-items]`، `[data-guest-cart]`، `#cart-content`، `#cart-state`، `#variant-panel[data-variant-id|data-max|data-orderable|data-price]`، `[data-bar-price]`؛ رویداد `cart:changed` از سرور |
| neshan | `neshan.js` | — | `[data-neshan-picker]` (فقط وقتی `NESHAN_MAP_KEY` هست) |
| slider | `slider.js` | — (فقط attribute) | `[data-slider]` + `data-autoplay` (میلی‌ثانیه)، `[data-slider-track]`، `[data-slider-prev]`، `[data-slider-next]`، `[data-slider-dot]` |

## پروتکل توسعه
1. اول این جدول را بخوان. اگر ماژول کارت را می‌کند، همان را صدا بزن.
2. اگر فقط یک گزینه کم است: همان تابع را **سازگار با گذشته** گسترش بده (پارامتر یا attribute اختیاری؛
   رفتار پیش‌فرض عوض نشود)، ردیف جدول را به‌روز کن و نمونه را به `/_styleguide/` اضافه کن.
3. اگر چیز تازه‌ای لازم است: فایل جدید `static/js/mm/<name>.js` با ثبت در `MM.<name>`، ردیف در این جدول،
   تگ `<script defer>` در `base.html` (یا `extra_js` اگر فقط یک صفحه نیاز دارد) و نمونه در styleguide.
4. تغییر ناسازگار فقط با grep روی همه‌ی استفاده‌ها و ثبت در «تغییرات».

## تغییرات
- ۰.۴ — `slider.js` (اسلایدر بنر صفحه‌ی اصلی).
- ۰.۳ — `likes.js`؛ `MM.auth.open(next)` (باز کردن مودال ورود از کد، برای مهمانی که لینکی برای کلیک ندارد).
- ۰.۲ — ردیف `cart`/`cart.js` (سبد مهمان در `localStorage`، افزودن/تغییر تعداد، ادغام هنگام تایید OTP).
- ۰.۱ — ساخت سند؛ تقسیم `app.js` به ماژول‌ها؛ `MM.ui.confirm/alert`؛ `otp.js`.
