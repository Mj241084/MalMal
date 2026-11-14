# ۰۸ — ماژول‌های UI سمت کلاینت (`window.MM`) — نسخه ۰.۱

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
| auth | `auth.js` | — | `[data-auth-open]`، `#auth-modal`، `#auth-modal-body` |
| otp | `otp.js` | `MM.otp.build(input)`، `MM.otp.startTimer(el)` | `[data-otp]` + `data-otp-length`، `data-otp-submit`؛ `[data-otp-timer]` + `data-seconds`، `data-otp-resend` |
| addresses | `addresses.js` | — | `[data-address-add]`، `[data-address-cancel]`، `#address-form-container` |
| neshan | `neshan.js` | — | `[data-neshan-picker]` (فقط وقتی `NESHAN_MAP_KEY` هست) |

## پروتکل توسعه
1. اول این جدول را بخوان. اگر ماژول کارت را می‌کند، همان را صدا بزن.
2. اگر فقط یک گزینه کم است: همان تابع را **سازگار با گذشته** گسترش بده (پارامتر یا attribute اختیاری؛
   رفتار پیش‌فرض عوض نشود)، ردیف جدول را به‌روز کن و نمونه را به `/_styleguide/` اضافه کن.
3. اگر چیز تازه‌ای لازم است: فایل جدید `static/js/mm/<name>.js` با ثبت در `MM.<name>`، ردیف در این جدول،
   تگ `<script defer>` در `base.html` (یا `extra_js` اگر فقط یک صفحه نیاز دارد) و نمونه در styleguide.
4. تغییر ناسازگار فقط با grep روی همه‌ی استفاده‌ها و ثبت در «تغییرات».

## تغییرات
- ۰.۱ — ساخت سند؛ تقسیم `app.js` به ماژول‌ها؛ `MM.ui.confirm/alert`؛ `otp.js`.
