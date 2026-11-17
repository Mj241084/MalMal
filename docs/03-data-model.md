# ۰۳ — مدل داده، ایندکس، کش و جستجو — نسخه ۰.۳.۱۲

مرجع جریان‌ها: `02-spec.md`. نام فیلدها انگلیسی‌اند. همه‌ی مدل‌ها `created_at/updated_at` دارند مگر ذکر شود.
پول: `BigIntegerField` به **تومان**. زمان: UTC.

---

## ۱. تنظیمات SQLite و Django

- `journal_mode=WAL`، `synchronous=NORMAL`، `busy_timeout=5000`، `foreign_keys=ON`.
- `OPTIONS["transaction_mode"] = "IMMEDIATE"` — تاییدشده در Django 5.2.19 (تراکنش‌های نوشتن با `BEGIN IMMEDIATE` شروع می‌شوند).
- SQLite `select_for_update` را نادیده می‌گیرد. هم‌زمانی با تراکنش‌های `IMMEDIATE` و به‌روزرسانی‌های اتمیک شرطی (`UPDATE ... WHERE`) تامین می‌شود.
- FTS5 در SQLite هنگام startup در `CoreConfig.ready()` (`verify_sqlite_fts5`) بررسی می‌شود و اگر در بیلد پایتون نبود خطای واضح `ImproperlyConfigured` می‌دهد.
- نوشتن‌ها کوتاه: هیچ تماس شبکه (پیامک، درگاه) داخل تراکنش نباشد.
- پشتیبان: `manage.py backup_db --with-media` شبانه (API آنلاین SQLite + کپی `media/`) به مسیر `BACKUP_DIR` بیرون از پوشه‌ی پروژه؛ بررسی `integrity_check` روی کپی و نگه‌داری ۱۴ روز. بازیابی در `docs/deploy.md` بخش ۴.

---

## ۲. اپ‌ها

| اپ | مسئولیت |
|----|---------|
| `core` | SiteSettings، StaticPage، FooterLink، ابزارهای مشترک (نرمال‌سازی فارسی، قالب‌تگ آیکون، شمسی، پیوند کوتاه بدون جدول) |
| `geo` | Province، City |
| `accounts` | User، OTPChallenge، Address |
| `catalog` | Brand، Category، Product، Variant، ProductImage، Spec*، StockMovement |
| `marketing` | Banner، Collection، HomeBlock، TrustItem |
| `cart` | Cart، CartItem |
| `orders` | Order، OrderItem، OrderStatusLog، ShippingMethod |
| `payments` | PaymentGateway، Payment، adapterها |
| `engagement` | Like، Review، ProductDailyStat، StockSubscription |
| `search` | ایندکس FTS5 و منطق جستجو |
| `notifications` | SmsLog، adapter پیامک |
| `panel` | پنل مدیریت اختصاصی (P9 تا P15، `09-panel-spec.md`). **مدل و مهاجرت ندارد**؛ ممیزی روی `django.contrib.admin.LogEntry` (D38) |

---

## ۳. جداول

### accounts
**User** (مدل سفارشی، `USERNAME_FIELD = mobile`)
- `mobile` CharField(11) unique، فقط `09XXXXXXXXX`
- `first_name`, `last_name` (خالی مجاز)
- `national_code` CharField(10) خالی مجاز، اعتبارسنجی الگوریتمی. **قفل (D20):** مشتری فقط وقتی خالی است می‌تواند ثبت کند، بعد از آن فقط ادمین با مجوز `accounts.change_national_code` تغییر می‌دهد (در `save()` و فرم‌ها اعمال شود، نه فقط در UI) و هر تغییر ادمین لاگ می‌شود. unique نیست.
- `email` خالی مجاز؛ یکتا فقط وقتی خالی نیست (`UniqueConstraint(condition=~Q(email=""))`)
- `session_version` PositiveInt default 0
- `is_active`, `is_staff`, `is_superuser`, `date_joined`, `last_login`
- `get_session_auth_hash` شامل `session_version`. کاربران مشتری رمز ندارند.

**OTPChallenge** (یک ردیف فعال برای هر شماره؛ نگه‌داری ۱ روز پس از انقضا طبق D33 و پاک‌سازی از ادمین یا job دوره‌ای P6)
- `mobile` (unique)، `code_hmac`، `expires_at`، `last_sent_at`، `attempts` int، `max_attempts` default 5، `locked_until` null، `consumed_at` null، `ip`
- چالش **فعال**: `consumed_at IS NULL AND expires_at > now AND (locked_until IS NULL OR locked_until < now)`.
- محدودیت نرخ در **Redis** نه DB: `mm:rl:otp:mobile:{m}:h`، `...:d`، `mm:rl:otp:ip:{ip}:h` با `INCR` + `EXPIRE`.

**Address**
- `user` FK، `title`، `recipient_name`، `recipient_mobile`
- `province` FK، `city` FK، `address_text`، `plate`، `unit`، `postal_code` (10 رقم)
- `lat`, `lng` Decimal(9,6) null
- `is_default`، `deleted_at` null (حذف نرم)
- ایندکس: `(user, deleted_at)`. یک آدرس پیش‌فرض برای هر کاربر (constraint شرطی).

### geo
**Province**: `name`, `slug`, `neshan_id` (اختیاری/یکتا), `sort`. **City**: `province` FK, `name`, `slug`, `neshan_id` (یکتا به‌ازای هر استان). ایندکس `(province, name)`. داده از Region API نشان گرفته و در دیتابیس ذخیره می‌شود (`sync_geo` برای همگام‌سازی کامل و کش ۷ روزه برای تازه‌سازی تنبل).

### catalog

**Brand**: `name_fa`, `name_en`, `slug`, `logo`, `aliases` (متن، برای جستجو: «سامسونگ، Samsung»), `is_active`.

**Category** (درخت)
- `parent` FK(self) null، `name`, `slug`, `logo` (SVG/WebP)، `description`
- `path` CharField: مسیر شناسه‌ها `"1/5/12/"`، `depth`
- `is_featured`, `featured_order`, `show_in_menu`, `menu_order`, `is_active`
- `rev` int و `subtree_rev` int (برای کش، بخش ۵)
- `spec_inherit` (فیلدهای مشخصات از والدها به ارث می‌رسد)
- ایندکس: `path`, `(parent, menu_order)`, `(is_featured, featured_order)`
- جابجایی در درخت `path` همه‌ی نوادگان را در یک تراکنش بازمحاسبه می‌کند.

**Product**
- `title`, `slug`, `brand` FK null, `category` FK, `category_path` (کپی denormalized از `category.path`)
- `short_description`, `description` (HTML پاک‌سازی‌شده)، `warranty_text`
- `status` (`draft/active/archived`), `is_active` محاسبه‌ای از status
- **denormalized از variantها:** `min_price`, `max_price`, `compare_at_min` (قیمت قبل از تخفیف), `discount_pct`, `in_stock` bool, `total_stock`
- **شمارنده‌ها:** `like_count`, `review_count`, `rating_sum`, `rating_avg` (محاسبه‌ای، Decimal(2,1)), `purchase_count_30d`, `purchase_count_total`, `view_count`
- `rev` int (کش جزئیات)، `search_text` (نرمال‌شده، منبع FTS)
- `seo_title`, `seo_description`، `main_image` (کپی ارجاع تصویر اول)
- ایندکس‌ها (کاتالوگ کوچک است؛ بیش‌ازحد ایندکس نکن و با `EXPLAIN QUERY PLAN` تایید کن):
  - `(category_path)` برای کوئری زیردرخت (بخش ۴)
  - `(status, -created_at)`
  - `(status, min_price)`
  - `(status, -purchase_count_30d)`
  - `(status, -like_count)`
  - `(brand, status)`
  - `(status, -discount_pct)`

**Variant** (SKU، واحد خرید)
- `product` FK، `sku` unique، `title` (مثلاً «سفید، ۱۲ ماه گارانتی»)، `options` JSON (`{"color":"سفید","model":"..."}`)
- `price`, `compare_at_price` null، `stock` int ≥ 0، `is_active`, `sort`
- `max_per_order` (`PositiveSmallIntegerField`، null/blank): سقف تعداد هر مشتری در هر سفارش. خالی یا ۰ = تا سقف موجودی (D29).
- property `max_orderable`: `0` اگر `stock <= 0`؛ وگرنه `stock` وقتی `max_per_order` خالی/۰ است، در غیر این صورت `min(stock, max_per_order)`. سبد و checkout از همین استفاده می‌کنند.
- محصول ساده: دقیقاً یک variant پیش‌فرض (در ادمین به‌طور خودکار ساخته می‌شود).
- ایندکس: `(product, is_active)`, `sku`.
- تغییر `price/stock/is_active` ← `Product.refresh_aggregates()` (بخش ۵).
- **مجوز `catalog.adjust_stock` (P12، برنامه‌ریزی‌شده):** در `Variant.Meta.permissions`. تغییر دستی موجودی فقط از `stock.adjust_manual` (compare-and-set با `expected_stock` اختیاری، ثبت `StockMovement`، `refresh_products`، و `back_in_stock.mark_due` فقط وقتی موجودی از ۰ به مثبت رفت). جدا از `change_variant` است چون آن مجوز قیمت را هم باز می‌کند (D43، `09` بخش ۲.۵).

**ProductImage**: `product`, `variant` null, `image`, `alt`, `sort`. چند اندازه‌ی WebP تولید می‌شود.

**SpecAttribute**: `category` FK (اعمال برای کل زیردرخت), `name`, `type` (`text/number/bool/choice`), `unit`, `is_filterable`, `sort`.
**ProductSpecValue**: `product`, `attribute`, `value_text`, `value_number` null. ایندکس `(attribute, value_number)`, `(attribute, value_text)`, `(product, attribute)` unique.

**StockMovement** (دفتر): `variant`, `delta`, `reason` (`order/cancel/expire/manual/return`), `order_item` null, `note`. فقط افزودنی (append-only).
  - **قرارداد `note` برای `reason="manual"` (از P12):** `"<دلیل> — <موبایل کارمند>"`. موجودی اولیه‌ی تنوع تازه‌ی ساخته‌شده در پنل هم یک ردیف `manual` می‌گیرد (`09` ماژول ۴ و ۷).

### marketing
**Banner**: `title` (داخلی)، `alt` (**اجباری**)، `image_desktop` (اجباری)، `image_mobile` (**اختیاری**؛ خالی = همان تصویر دسکتاپ)، `placement` (`home_hero/home_strip`), `target_type` (`none/product/category/collection/url`), `target_product|target_category|target_collection` FK null، `target_url`, `starts_at`, `ends_at` (ذخیره UTC؛ در ادمین با ویجت تقویم شمسی طبق `06`)، `sort`, `is_active`. اعتبارسنجی: دقیقاً یک مقصد متناسب با `target_type`؛ `target_url` فقط مسیر داخلی (`/…`) یا `https://…`. قالب تصویر WebP/JPG/PNG، سقف ۱ مگابایت. زمان‌بندی با `ScheduledModel` مشترک است (`clean` پایان بعد از شروع، `is_live(now)`).

**Collection**: `title`, `slug`, `description`, `cover`, `mode` (`manual/rule`), `is_active`, `starts_at`, `ends_at` (ویجت شمسی مثل Banner), `seo_*`.
- قاعده‌ای: `categories` M2M، `brands` M2M، `min_discount_pct`، `min_price`، `max_price`، `only_in_stock`، `sort_by`.
- دستی: **CollectionItem** (`collection`, `product`, `sort`) با unique `(collection, product)`.
- **`rev` و `limit` ندارد** (P5): کلید کش از `epoch` سراسری می‌آید و سقف تعداد فقط روی `HomeBlock.limit` است. `CollectionQuerySet.live(now)` فعال و درون پنجره را برمی‌گرداند.

**HomeBlock**: `kind` (`hero/categories/product_rail/collection_rail/banner_strip/brands/trust`), `title`, `collection` FK null, `category` FK null, `rail_source` (`best_selling/newest/discounted`), `limit` (پیش‌فرض ۱۲، **حداکثر ۲۴**), `sort`, `is_active`. اعتبارسنجی: `collection_rail` بدون مجموعه و `product_rail` بدون منبع خطا؛ فقط **یک** `hero` و **یک** `banner_strip`. مهاجرت داده‌ی `0004_default_home_blocks` ترتیب پیش‌فرض را می‌سازد (هشت بلوک: اسلایدر، دسته‌ها، نوار باریک، سه ریل محصول، برندها، مزیت‌ها).

**TrustItem** (مزیت‌های فروشگاه، بلوک `trust`): `icon` (نام نماد در sprite)، `title`، `subtitle`، `sort`، `is_active`.

### core
**SiteSettings** (singleton): نام، لوگو (روشن/تاریک)، تلفن، آدرس، ساعات کاری، لینک‌های اجتماعی، آستانه‌ی ارسال رایگان، آستانه‌ی «موجودی کم»، پارامترهای OTP، ساعت مجاز ارسال «موجود شد» (پیش‌فرض ۸ تا ۲۱)، `trust_marks_html` (قطعه‌ی HTML نماد اعتماد/اینماد؛ فقط ادمین؛ خالی = نمایش داده نمی‌شود).
- **مشخصات فروشنده (برای فاکتور، C7):** `legal_name`، `economic_code`، `national_id` (شناسه‌ی ملی)، `registration_no`، `legal_address`، `legal_postal_code`، `legal_phone`. خالی مجاز؛ فاکتور فیلدهای خالی را نشان نمی‌دهد.
**StaticPage**: `slug`, `title`, `body`, `is_active`, `needs_review` bool (پیش‌فرض `False`؛ متن پیش‌نویسی مثل صفحه‌ی ارسال `True` می‌شود و فروشنده در ادمین خاموشش می‌کند؛ `check_launch` هشدار می‌دهد). **FooterLink**: `group`, `title`, `url`, `sort`. پیوند کوتاه پیامک بدون جدول است و از `core/shortlinks.py` (`r/<kind><pk base36>`) تولید می‌شود (D32).

### cart
**Cart**: `user` OneToOne. **CartItem**: `cart`, `variant`, `qty`. unique `(cart, variant)`. قیمت ذخیره نمی‌شود. سقف ۳۰ خط در لایه‌ی سرویس اعمال می‌شود.

### orders
**Order** (بدون `placed_at` — همان `created_at`؛ بدون `discount_total` و `customer_note` در v1)
- `number` unique (غیرترتیبی، `ML-` + ۸ رقم)، `user` FK(PROTECT)، `status`
- مبالغ: `items_total`, `shipping_cost`, `payable`
- **snapshot خریدار:** `buyer_name`, `buyer_mobile`, `buyer_national_code`, `buyer_email`
- **snapshot گیرنده و آدرس:** `recipient_name`, `recipient_mobile`, `province_name`, `city_name`, `address_text`, `plate`, `unit`, `postal_code`, `lat`, `lng`
- `shipping_method` FK null + `shipping_method_title` + `shipping_payment_mode` (snapshot)
- `tracking_code` (خالی مجاز؛ برای روش‌های `has_tracking` هنگام تغییر به `shipped` اجباری — P6)
- `reserved_until`, `paid_at`, `cancelled_at`, `cancel_reason`
- ایندکس: `(user, -created_at)`, `(status, reserved_until)`.
- مجوز `orders.manage_order_status`: هر تغییر وضعیت فقط از `apps/orders/workflow.py` (و `services.transition` برای حرکت‌های سیستمی) می‌گذرد؛ `QuerySet.update()` روی `Order` بیرون از `services.py` با تست معماری رد می‌شود.

**OrderItem**: `order`, `product`/`variant` FK(SET_NULL)، snapshot: `product_title`, `variant_title`, `sku`, `unit_price`, `qty`, `image_path`، `warranty_text`.
**OrderStatusLog**: `order`, `from_status`, `to_status`, `by_user` null, `note`, `created_at`.
**ShippingMethod** (فقط فیلدهای v1): `code`, `title`, `product_note`, `checkout_note`, `has_tracking`, `payment_mode` (`prepaid`/`collect`؛ تیپاکس v1: `collect`), `is_active`, `sort`. `base_cost`/`per_kg_cost`/`free_over`/`eta_*`/`provinces` وقتی روش دوم آمد اضافه می‌شوند. ذخیره/حذفش `trust_rev` را بالا می‌برد تا کش جزئیات محصول (متن ارسال) به‌روز شود.
- **موجودی:** هنگام ساخت سفارش با `reason="order"` اتمیک کم می‌شود و `StockMovement` ثبت می‌شود؛ پرداخت موفق حرکت جدیدی ثبت نمی‌کند (`sale` نداریم). `StockMovement.order_item_id` عدد ساده می‌ماند (بدون FK، برای جلوگیری از وابستگی چرخه‌ای مهاجرت‌ها).

### payments
**PaymentGateway**: `code` (`zarinpal` و ردیف `fake` فقط برای DEBUG), `title`, `logo`, `is_active`, `sort`, `min_amount`, `max_amount`. اسرار درگاه فقط در env.
**Payment**: `order`, `gateway_code`, `amount`, `authority`, `ref_id`, `card_pan_masked`, `status` (`initiated/redirected/verifying/verified/failed/cancelled`), `request_payload`/`verify_payload` (JSON، بدون اسرار), `verified_at`, `ip`. unique `(gateway_code, authority)` وقتی `authority` خالی نیست. `VERIFY_STALE` = ۲ دقیقه (claim گیرکرده با `expire_orders` آزاد می‌شود).

### engagement
**Like**: `user`, `product`, `created_at`. unique `(user, product)`، ایندکس `(product)`.
**Review**: `user`, `product`, `rating` 1–5, `body`, `status`, `is_verified_buyer`, `moderated_by`, `moderated_at`, `rejection_reason` (داخلی، متن آزاد کوتاه), `admin_reply`. بدون `title` (P4). unique `(user, product)`، `CheckConstraint` برای `rating` بین ۱ و ۵، ایندکس `(product, status, -created_at)`.
**ProductDailyStat**: `product`, `date`, `purchases`. **بدون `views`** (P4). unique `(product, date)`. برای محاسبه‌ی ۳۰ روزه‌ی غلتان.
**StockSubscription** `[DECIDED]` (فاز P6): `user`, `variant`, `restocked_at` null، `notified_at` null، `created_at`. unique `(user, variant)` فقط برای اشتراک **باز** (`notified_at IS NULL`)؛ ایندکس `(variant, notified_at)`. `restocked_at` را تنها موجودشدن واقعی (مسیر `Variant.save()`) می‌گذارد، نه برگشت موجودی از انقضا/لغو رزرو؛ دستور `send_back_in_stock` بعد از ارسال `notified_at` را ثبت می‌کند و اشتراک بسته می‌شود. جزئیات در `02` بخش ۱۳.

### notifications
**SmsLog**: `mobile`, `kind` (کلید قالب در `05`)، `provider_message_id`, `status`, `error`, `created_at`. بدون مقدار کد OTP. نگه‌داری ۹۰ روز طبق D33 و پاک‌سازی از ادمین یا job دوره‌ای P6.

---

## ۴. کوئری زیردرخت دسته (بدون join)

محصولات دسته‌ی `C` و همه‌ی نوادگانش، با `path` مثل `"1/5/"`:

```python
Product.objects.filter(
    category_path__gte=C.path,
    category_path__lt=C.path[:-1] + "0",  # '/' = 0x2F، کاراکتر بعدی '0' = 0x30
)
```

- برای `path="1/5/"` بازه‌ی `["1/5/", "1/5/0")` است. هم خود دسته و هم `"1/5/12/"` را می‌گیرد، ولی `"1/50/"` را نه.
- روی ایندکس `category_path` اجرا می‌شود. از `startswith` استفاده نشود (در SQLite با `LIKE` ایندکس را به‌طور پیش‌فرض نمی‌گیرد).
- `[VERIFY]` با `EXPLAIN QUERY PLAN` ببین از ایندکس استفاده می‌کند.

---

## ۵. کش (Redis) و الگوریتم باطل‌سازی هوشمند

### پیکربندی
- Redis با `django.core.cache.backends.redis.RedisCache` (تاییدشده در Django 5.2.19 با `redis`). پیشوند کلیدها `mm:v1:`. DB جدا برای rate limit (`mm:rl:`).
- سیاست حافظه: `allkeys-lru` برای کش. داده‌ی ماندگار (rate limit) اگر پاک شد، فقط رفتار موقت از دست می‌رود و مشکلی ایجاد نمی‌کند.
- **هرگز** `LocMemCache` (با چند worker ناسازگار می‌شود).

### ایده‌ی اصلی: کلید دارای نسخه (versioned key)
به‌جای حذف کلیدها، `rev` بالا می‌رود و کلید قدیمی خودش منقضی می‌شود. `v{n}` همان `FRAGMENT_VERSION` در `apps/catalog/constants.py` است و هر تغییر مارک‌آپ قالب‌های کش‌شونده آن را +۱ می‌کند (P4):
- `mm:v1:p:{id}:{rev}:t{trust_rev}:v{n}:detail` — بدنه‌ی HTML جزئیات محصول (بدون بخش شخصی)
- `mm:v1:p:{id}:{rev}:v{n}:card` — کارت محصول
- `mm:v1:c:{id}:{subtree_rev}:v{n}:list:{sort}:{filters_hash}:{page}` — لیست دسته (شامل زیردرخت)
- `mm:v1:p:{id}:{rev}:{base_subtree_rev}:v{n}:similar` — مشابه‌ها (`base` = والدِ دسته‌ی محصول؛ برای دسته‌ی ریشه خودش)
- `mm:v1:col:{id}:{epoch}:v{n}:list:{sort}:{filters_hash}:{page}` — نتایج صفحه‌ی مجموعه (P5: بدون `rev`، با `epoch`)
- `mm:v1:home:data:{epoch}:v{n}` — داده‌ی مشترک صفحه‌ی اصلی (بلوک‌ها، بنرها، دسته‌ها، برندها). `epoch` یک شمارنده‌ی سراسری در Redis (`INCR`) است.
- `mm:v1:home:rail:{epoch}:{block_id}:v{n}` — HTML هر ریل صفحه‌ی اصلی (P5)
- `mm:v1:menu:{epoch}` — منو و دسته‌های برتر

**پنجره‌ی زمانی داخل داده‌ی کش‌شده است (P5):** `starts_at/ends_at` بنر و مجموعه جزو کلید نیستند؛ در داده‌ی کش‌شده ذخیره می‌شوند و در هر درخواست با `now` سنجیده می‌شوند. پس نمایش دقیقاً سر وقت شروع/تمام می‌شود بدون `INCR` یا کران. TTL همه‌ی کلیدهای P5، ۱۵ دقیقه است (شمارنده‌ها `epoch` را تکان نمی‌دهند) `[ASSUMPTION]`.

**کش `social:{id}` ساخته نشد** (P4): شمارنده‌ها ستون خود `Product` هستند و خواندن با pk به‌اندازه‌ی Redis ارزان است.

`rev` و `subtree_rev` ستون **DB** هستند (نه Redis) تا اگر Redis پاک شد، نسخه‌ها برنگردند و کلید قدیمی با محتوای جدید اشتباه نخورد.

**شمارنده‌های `epoch` و `trust_rev` بدون TTL (P7):** این دو کلید با `cache.add(key, int(time.time()), None)` ساخته می‌شوند و هرگز منقضی نمی‌شوند؛ مقدار اولیه `timestamp` است تا اگر کلید به هر دلیلی گم شود (flush یا eviction)، شمارنده از یک عدد بزرگ‌تر ادامه دهد و کلیدهای نسخه‌ی قدیمی دوباره معتبر نشوند. `read_epoch()` در `apps/core/cache.py` تنها خواننده‌ی این کلیدهاست (`current_epoch()` و `trust_revision()`).

### دسته‌بندی فیلدها (جدول تصمیم)

| گروه | فیلدها | اثر |
|------|--------|-----|
| **LIST** (در لیست/کارت/جستجو دیده می‌شود) | `title`, `slug`, `brand`, `category`, `status`, `main_image`, `min_price`, `max_price`, `compare_at_min`, `discount_pct`, `in_stock` | `product.rev++` + `subtree_rev++` برای **همه‌ی اجداد** دسته‌ی جدید و **قدیم** + بازسازی FTS + `epoch++` اگر محصول در بلوک‌های سراسری باشد |
| **DETAIL** (فقط جزئیات) | `description`, `short_description`, `warranty_text`, مشخصات، تصاویر ثانویه، `seo_*` | فقط `product.rev++` |
| **COUNTER** | `like_count`, `review_count`, `rating_*`, `purchase_*`, `view_count` | **هیچ باطل‌سازی**. فقط `F()` (P4: همه‌ی نوشتن‌ها از `apps/engagement/counters.py`) |
| **STRUCTURAL** | تغییر دسته (نام/والد/لوگو/ترتیب/منو)، بنر، Collection، CollectionItem، HomeBlock، Brand، SiteSettings، FooterLink | `epoch++` و `rev/subtree_rev` مناسب |

### تشخیص تغییر
- در `from_db` مقادیر اولیه‌ی فیلدهای دسته‌بندی‌شده نگه داشته می‌شود (`_loaded_values`).
- در `save()` اختلاف محاسبه می‌شود و **سطح باطل‌سازی** (بیشترین سطح بین فیلدهای تغییرکرده) تعیین می‌شود. اگر هیچ فیلد LIST/DETAIL عوض نشده (مثلاً فقط COUNTER) هیچ کاری نمی‌شود.
- همه‌ی باطل‌سازی‌ها داخل `transaction.on_commit(...)` اجرا می‌شوند تا هیچ کلیدی قبل از commit و با داده‌ی قدیمی دوباره ساخته نشود.
- `rev++` با `F()` و `UPDATE` اتمیک.

### تغییر Variant
۱. `Variant.save()/delete()` ← `Product.refresh_aggregates()` (min/max/discount/in_stock/total_stock محاسبه، و فقط اگر مقدار عوض شد ذخیره می‌شود).
۲. اگر فیلد DETAIL عوض شد **و** `refresh_aggregates` خودش سطح LIST را بالا برده باشد، rev دوباره بالا نمی‌رود (تا یک تغییر دو بار باطل‌سازی نکند). فیلدهای DETAIL تنوع (P7): `title`, `options`, `max_per_order`, `price`, `compare_at_price`, `is_active`, `sort`.
۳. **فروش عادی** (کم شدن موجودی) `rev` را عوض نمی‌کند، مگر موجودی از **صفر عبور کند**، **در بازه‌ی کم‌موجودی یا سقف سفارش باشد** (شرط `min(stock-before, stock-after) <= max(low_stock_threshold, max_per_order)`) یا `in_stock` عوض شود. تغییر قیمت یک تنوع میانی از ادمین، `rev` جزئیات و (اگر aggregate عوض شود) سطح LIST را بالا می‌برد.
۴. تخفیف کارت از **ارزان‌ترین** تنوع محاسبه می‌شود (`compare_at_min` فقط از تنوع‌هایی که قیمتشان برابر `min_price` است)؛ پس یک تنوع گران‌تر با تخفیف، بج تخفیف را روشن نمی‌کند.

### باطل‌سازی تغییرات بیرون از `Product.save` (P7)
دو دستیار در `apps/catalog/cache.py`:
- `touch_product(product_id, level=LEVEL_LIST)` — برای تغییرهایی که خودشان `Product.save` را صدا نمی‌زنند: مشخصات (`ProductSpecValue`)، تصاویر (`ProductImage`)، حذف تنوع، اکشن‌های ادمین و حرکت موجودی. دسته‌ی محصول را می‌خواند و زنجیره‌ی اجداد را بالا می‌برد.
- `invalidate_category(category_id, old_path=None)` — تغییر ساختاری دسته؛ زنجیره‌ی **جدید و قدیم** (پس از جابه‌جایی) و `epoch` منو را بالا می‌برد. `Category.save` مسیر قدیم را پاس می‌دهد.

hookهای مدل که خودشان باطل می‌کنند: `ProductImage.save/delete` (سطح DETAIL)، `ProductSpecValue.save/delete` (سطح LIST، چون فیلترها و facets عوض می‌شوند)، `SpecAttribute.save/delete` (`invalidate_category`)، `Category.save` (ساختاری)، و `BrandAdmin.save_model` ← `invalidate_brand` که `search_text` همه‌ی محصولات برند را بازمی‌سازد و سطح LIST را بالا می‌برد. اکشن «بازگشت وجه» هم فقط وضعیت پرداخت را عوض می‌کند (بدون کش). از P10 این اکشن و پنل هر دو به `payments.services.record_refund` وصل می‌شوند که برای سفارش لغو/منقضی/تحویل‌شده وضعیت سفارش را هم از `workflow.change_status` می‌گذراند (D42).

### به‌روزرسانی‌های دسته‌جمعی
`QuerySet.update()` و `bulk_update()` سیگنال ندارند. قواعد:
- متد `ProductQuerySet.update_tracked(**fields)` و `bulk_update_tracked` که همان منطق را روی ردیف‌های تاثیرپذیر اجرا می‌کند.
- ادمین actions فقط از این متدها استفاده کنند.
- `update()` خام روی Product/Variant/Category در بقیه‌ی کد ممنوع است (تست معماری با grep/CI). **COUNTER:** تنها استثنای ثبت‌شده `apps/catalog/stock.py` و `apps/engagement/counters.py` است (`ALLOWED_FILES` در تست معماری).

### Rebuild و جلوگیری از stampede
- حذف همراه با ساخت **lazy**: اولین درخواست بعد از تغییر کلید را می‌سازد، با قفل تک‌پرواز (`cache.add("lock:"+key, 1, 10)`)؛ درخواست‌های همزمان یا stale را می‌خوانند یا چند ده ms صبر می‌کنند.
- **Warm فعال** بعد از تغییر محصولات پربازدید (۲۰۰ تا بر اساس `purchase_count_30d + view_count`) و بعد از ایمپورت‌های بزرگ، با دستور `manage.py warm_cache` (cron/systemd timer). `[ASSUMPTION]` v1 بدون Celery. اگر لازم شد صف سبک (huey روی Redis یا `django.tasks`) بررسی شود.
- TTL امنیتی روی همه‌ی کلیدها (مثلاً ۲۴ ساعت) تا کلیدهای قدیمی جمع شوند.

### HTTP caching
`ETag`/`Last-Modified` برای جزئیات محصول و دسته بر پایه‌ی `rev`. بخش‌های شخصی با `Cache-Control: private, no-store` و بدون ETag مشترک.

**اجزای ETag صفحه‌ی محصول (P7):** `"{product_id}-{rev}-{review_count}-{rating_sum}-u{viewer}-c{cart_count}-e{epoch}-t{trust_rev}-v{FRAGMENT_VERSION}"` — شمارنده‌ی سبد، منو (`epoch`)، مزیت‌های فروشگاه (`trust_rev`) و نسخه‌ی قطعه (`FRAGMENT_VERSION`) در بدنه‌ی صفحه دیده می‌شوند، پس باید در تگ باشند؛ وگرنه مرورگر با ۳۰۴ نسخه‌ی کهنه را نشان می‌دهد.

### Rebuild دوره‌ای (cron)
| دستور | زمان | کار |
|-------|------|-----|
| `expire_orders` | هر ۵ دقیقه | سفارش‌های منقضی‌شده، برگرداندن موجودی |
| `send_back_in_stock` | هر ۱۰ دقیقه | پیامک «موجود شد» برای variantهایی که واقعاً موجود شده‌اند (فقط در بازه‌ی ساعت مجاز) |
| `recount_purchases` | شبانه | `purchase_count_30d` از `ProductDailyStat` + حذف ردیف‌های قدیمی‌تر از ۹۰ روز |
| `reconcile_counters` | شبانه | بازمحاسبه‌ی `like_count/review_count/rating_*` و اصلاح drift |
| `warm_cache` | بعد از `recount` | پیش‌ساخت پربازدیدها |
| `purge_otp` | شبانه | حذف چالش‌های OTP منقضی‌شده‌ی قدیمی‌تر از یک روز (D33) |
| `purge_sms_logs` | شبانه | حذف `SmsLog` قدیمی‌تر از ۹۰ روز (D33) |
| `backup_db` | شبانه | پشتیبان consistent با API آنلاین SQLite در `BACKUP_DIR` + کپی `media/` با `--with-media` (خط crontab) + بررسی سلامت + نگه‌داری ۱۴ روز |

فایل cron نمونه: `deploy/crontab.example` (D-P6 §11). هیچ‌کدام timer جدا ندارند.

---

## ۶. شمارنده‌ها و متن‌های اجتماعی

**نوشتن:** با `F()` هنگام رویداد، داخل همان تراکنش، **همه از `apps/engagement/counters.py`** (P4):
- لایک/آن‌لایک: سیگنال `post_save`/`post_delete` روی `Like` → `like_count ± 1` با `Greatest(..., 0)` (هرگز منفی نمی‌شود).
- نظر: سیگنال `post_save`/`post_delete` روی `Review` → `reconcile([product_id])` که `review_count`، `rating_sum` و `rating_avg` را از **ردیف‌های تاییدشده بازمحاسبه** می‌کند (نه افزایشی؛ هر مسیر ادمین/حذف/cascade درست می‌ماند).
- پرداخت موفق: `purchase_count_total += qty`، `purchase_count_30d += qty` و `ProductDailyStat.purchases += qty` (upsert) — `counters.add_purchases`، صدازدهنده از `payments.services._finalize` داخل تراکنش.
- سیگنال‌های `apps.py` با `weak=False` وصل می‌شوند؛ بدون آن receiverهای محلی `ready()` جمع می‌شوند و شمارنده‌ها بی‌صدا از کار می‌افتند.

**خواندن (بدون join):** شمارنده‌ها از ستون‌های خود Product می‌آیند (ارزان). کش `social:{id}` وجود ندارد (P4).

**بخش شخصی (lazy، `Cache-Control: private`):**
- صفحه‌ی محصول: `GET /social/product/<id>/` با `hx-trigger="load"` ← partial با متن اجتماعی و خلاصه‌ی امتیاز (ستاره + میانگین).
- سبد: متن اجتماعی **داخل خود صفحه** رندر می‌شود (`social.cart_notes`، یک کوئری برای لایک‌های بیننده). مسیر `/social/cart/` وجود ندارد و checkout متن اجتماعی ندارد.
- **قلب کارت‌ها:** `likes.js` بعد از هر بارگذاری یا هر swap یک درخواست دسته‌ای `GET /likes/state/?ids=1,2,3` (حداکثر ۶۰ شناسه در هر درخواست، یک کوئری) می‌فرستد؛ پاسخ HTML با `hx-swap-oob="outerHTML:[data-like='ID']"` است. هیچ درخواستی به‌ازای هر کارت نیست.
- قلب: `POST /likes/<id>/` با `state=1|0` (وضعیت مطلق، نه toggle) با پاسخ partial دکمه + به‌روزرسانی متن اجتماعی (OOB).

---

## ۷. جستجو (FTS5)

```sql
CREATE VIRTUAL TABLE product_fts USING fts5(
  product_id UNINDEXED,
  title, brand, category, model_codes, tokens,
  tokenize='unicode61 remove_diacritics 2',
  prefix='2 3 4'
);
```
جدول معمولی FTS5 (نه contentless) است تا حذف و درج ردیف در همه‌ی نسخه‌های SQLite کار کند. کاتالوگ کوچک است و حجم اضافه مهم نیست.
`[VERIFY]` ساختار و مهاجرت FTS5 در Django (migration با `RunSQL`، بدون `CREATE VIRTUAL TABLE` در ORM).

### نرمال‌سازی (تابع مشترک `core.text.normalize_fa`)
هم موقع ایندکس هم موقع جستجو:
- `ي`→`ی`، `ك`→`ک`، حذف اعراب، کشیده، نیم‌فاصله→فاصله، `ة`→`ه`
- ارقام فارسی/عربی→انگلیسی
- lower-case لاتین
- کد مدل: نسخه‌ی اصلی + نسخه‌ی بدون خط‌تیره/فاصله (`WM-1234` و `WM1234`)
- alias برند: `Brand.aliases` به `brand` و `tokens` اضافه می‌شود.

### به‌روزرسانی ایندکس
فقط وقتی فیلد LIST یا `search_text` عوض شد، داخل `on_commit`: حذف و درج ردیف همان محصول. بازسازی کامل: `manage.py rebuild_search`.

### جستجو
- امتیازدهی `bm25(product_fts, 10, 5, 3, 8, 1)` (وزن عنوان و کد مدل بیشتر).
- پیشوند برای عبارت آخر (`term*`).
- فقط محصولات `active`. اگر نتیجه‌ای نبود، fallback به `LIKE` روی `title` نرمال‌شده.
- نتیجه‌ی suggest با TTL کوتاه (۶۰ ثانیه) در Redis کش شود، کلید شامل `epoch` کاتالوگ.

---

## ۸. محصولات مشابه

- بدون جدول. محاسبه‌ی lazy و کش با کلید `p:{id}:{rev}:{base_subtree_rev}:v{n}:similar` (TTL ۶ ساعت).
- امتیاز: هم‌دسته‌ی برگ (+۵)، هم‌برند (+۲)، نزدیکی قیمت (±۳۰٪ → +۲)، مقدار مشترک مشخصات فیلترپذیر (+۱ به‌ازای هر مورد). فقط `active` و `in_stock`. ۱۲ نتیجه.
- استخر کاندید: زیردرخت **والدِ** دسته‌ی محصول (هم‌دسته‌ها و خواهر/برادرها)، سقف ۳۰۰ محصول به ترتیب `-purchase_count_30d`.
- مسیر `/similar/<id>/` (عمداً با `similar/` شروع می‌شود تا با `p/<id>/<slug>/` تداخل نکند) و لود با `hx-trigger="revealed"` + `hx-swap="outerHTML"`؛ پاسخ خالی یعنی ریل حذف می‌شود.
- `subtree_rev` دسته‌ی پایه در کلید است، پس هر تغییر محصول در استخر کلید را عوض می‌کند.

---

## ۹. مدل‌های تحت‌نظر برای ادمین

هر مدل باید `list_display`، `search_fields`، `list_filter` و `ordering` معنادار داشته باشد. Inlineها: Product ← Variant, ProductImage, ProductSpecValue؛ Order ← OrderItem (فقط‌خواندنی)، OrderStatusLog؛ Collection ← CollectionItem. مدل‌های حساس (Payment, StockMovement, OTPChallenge, SmsLog) فقط‌خواندنی.

---

## ۱۰. نکات پایان

- هر مهاجرت بزرگ داده‌ای (path دسته‌ها، FTS) قابل اجرای مجدد و idempotent باشد.
- تست‌ها حداقل: ترتیب و idempotency سینک سبد، callback پرداخت تکراری، رقابت دو سفارش روی آخرین موجودی، قفل OTP، سطح باطل‌سازی کش برای هر گروه فیلد، کوئری زیردرخت (`1/5/` در برابر `1/50/`).

---

## ۱۱. تغییرات

- ۰.۳.۱۴ (P13) — بدون مدل و مهاجرت؛ `marketing.services.rule_queryset` و `banner_target_dead` اضافه شد و `collection_products` به `rule_queryset` واگذار می‌کند.
- ۰.۳.۱۲ (پنل، برنامه‌ریزی) — اپ `panel` در جدول اپ‌ها (بدون مدل و مهاجرت؛ ممیزی روی `LogEntry`)، مجوز `catalog.adjust_stock` روی `Variant.Meta.permissions` (P12)، قرارداد `StockMovement.note` برای حرکت دستی، و اتصال اکشن بازگشت وجه به `record_refund` (P10). عنوان سند با تاریخچه (۰.۳.۱۱) هم‌تراز شد؛ قبلاً ۰.۳.۹ مانده بود. هیچ‌کدام تا اجرای فاز مربوط در کد نیست.
- ۰.۳.۱۱ (P8 اصلاحی) — حذف `is_demo` از مدل‌های کاتالوگ و بازاریابی، حذف `is_placeholder` از `TrustItem`، حذف `weight_g` و `max_weight_g`، و افزودن `neshan_id` روی `Province`/`City` برای همگام‌سازی با Region API نشان (`sync_geo` و کش ۷ روزه).
- ۰.۳.۱۰ (P7) — شمارنده‌های `epoch`/`trust_rev` بدون TTL و با مقدار اولیه‌ی `timestamp` (`read_epoch`) تا پس از flush یا eviction کلید کهنه دوباره معتبر نشود. باطل‌سازی تازه: `touch_product` برای مشخصات/تصاویر/حذف تنوع/ادمین، `invalidate_category(old_path)` برای زنجیره‌ی مبدأ پس از جابه‌جایی، `invalidate_brand` با بازسازی `search_text`، و hookهای `ProductImage`/`ProductSpecValue`/`SpecAttribute`. `VARIANT_DETAIL_FIELDS` شامل `price`/`compare_at_price`/`is_active`/`sort` شد و قاعده‌ی «موجودی در بازه‌ی کم‌موجودی یا سقف، rev را بالا می‌برد» در `apps/catalog/stock.py` آمد. `Product.refresh_aggregates` تخفیف را فقط از ارزان‌ترین تنوع می‌گیرد و `Variant.discount_pct` اضافه شد. `Product.save(update_fields=…)` فیلدهای محاسبه‌شده (`search_text`، `slug`، `category_path`) را هم می‌نویسد. `FRAGMENT_VERSION` به ۳ رفت و اجزای ETag صفحه‌ی محصول کامل شد.
- ۰.۳.۹ (P6) — `StockSubscription.restocked_at` اضافه شد (فعال‌سازی «موجود شد» فقط با موجودشدن واقعی)، `Order.Meta.permissions` مجوز `orders.manage_order_status` گرفت و `PAID_STATES` در `apps/orders/models.py` تعریف شد (به‌جای تکرار در `engagement/services.py`). `django.contrib.sitemaps` به اپ‌ها و `sitemap.xml`/`robots.txt` به `config/urls.py` اضافه شد (`apps/core/seo.py`). `BACKUP_DIR` در تنظیمات پایه و `STORAGES`/HSTS/`CSRF_TRUSTED_ORIGINS`/`LOGGING` در `prod.py`. دستورهای دوره‌ای جدید در جدول بخش ۵؛ فایل `deploy/crontab.example` مرجع است.
- ۰.۳.۸ (P5) — جدول `marketing` با کد واقعی هم‌تراز شد: `Banner.alt` اجباری و `image_mobile` اختیاری، `Collection` بدون `rev` و `limit` (و `CollectionQuerySet.live`)، `HomeBlock.limit` تا ۲۴ و قید یکتایی `hero`/`banner_strip`. کلید کش مجموعه به `col:{id}:{epoch}:v{n}:list:{sort}:{filters_hash}:{page}` تغییر کرد و کلید ریل `home:rail:{epoch}:{block_id}:v{n}` اضافه شد؛ پنجره‌ی زمانی داخل داده‌ی کش‌شده و در هر درخواست سنجیده می‌شود. `Brand` هم به لیست STRUCTURAL اضافه شد (لوگویش در بلوک برندها دیده می‌شود).

- ۰.۳.۷ (P4) — اپ `engagement` ساخته شد (`Like`، `Review`، `ProductDailyStat`)؛ `Review` بدون عنوان، با `rejection_reason` داخلی و `CheckConstraint` امتیاز ۱ تا ۵؛ `ProductDailyStat` بدون `views`. همه‌ی نوشتن‌های COUNTER در `apps/engagement/counters.py` (`add_likes`، `add_purchases`، `reconcile`، `recount_purchases`) و `add_purchases` از `stock.py` حذف شد. `FRAGMENT_VERSION` وارد کلیدهای `detail`/`card`/`list`/`similar` شد و کلید مشابه‌ها `p:{id}:{rev}:{base_subtree_rev}:v{n}:similar` است. کش `social:{id}` ساخته نشد؛ قلب‌ها با `GET /likes/state/` و متن اجتماعی با `GET /social/product/<id>/`. ETag صفحه‌ی محصول `review_count`/`rating_sum` را هم دارد.
- ۰.۳.۶ (P3) — اپ‌های `cart`/`orders`/`payments` با کد واقعی هم‌تراز شدند: `Order` بدون `placed_at`/`discount_total`/`customer_note`، `ShippingMethod` فقط فیلدهای v1، `Payment.status` شامل `verifying`، `PaymentGateway` طبق کد. موجودی هنگام ساخت سفارش با `reason="order"` کم می‌شود و پرداخت حرکت جدیدی ثبت نمی‌کند؛ `StockMovement.order_item_id` عددی ماند. مهاجرت‌های داده: روش ارسال `tipax` و درگاه‌های `zarinpal`/`fake`.
- ۰.۳.۵ (اصلاحی P2-ب) — حذف مدل `ShortLink` از `core` (جایگزینی با کدهای بدون جدول `r/<kind><pk base36>`، D32) و افزودن یادداشت نگه‌داری داده روی `OTPChallenge` (۱ روز پس از انقضا) و `SmsLog` (۹۰ روز) طبق D33.
- ۰.۳.۴ (اصلاح P2) — افزودن مدل `ShortLink` (کد یکتا، مسیر مقصد یکتا) در اپ `core` برای پیوندهای کوتاه پیامک sms.ir (`#LINK#`).
- ۰.۳.۳ (P1) — `Variant.max_per_order` به `null=True/blank=True` تغییر کرد (خالی/۰ = تا سقف موجودی) و property `max_orderable` اضافه شد (D29). تغییر فیلدهای DETAIL هر variant (`title`، `options`، `max_per_order`، `weight_g`) حالا `Product.rev` را بالا می‌برد تا کش جزئیات به‌روز شود. `TrustItem` (اپ `marketing`) با چهار ردیف `is_placeholder=True` در مهاجرت داده ساخته می‌شود و `trust_rev` بخشی از کلید کش جزئیات محصول است.
- ۰.۳.۲ (P1) — `bm25` در SQLite به تعداد ستون‌ها وزن می‌خواهد؛ ستون `UNINDEXED` با وزن ۰ و وزن‌های سند به‌صورت `bm25(product_fts, 0, 10, 5, 3, 8, 1)` اعمال شد. `StockMovement.order_item` در P1 موقتاً `order_item_id` عددی است (اپ `orders` در P3 ساخته می‌شود و آن‌وقت به FK تبدیل می‌شود). تصاویر: چند اندازه‌ی WebP (۴۰۰/۸۰۰/۱۲۰۰) هنگام آپلود در `ProductImage.save()` ساخته و در `widths` ذخیره می‌شود؛ `srcset` از همان. کش: TTLهای امنیتی `detail/card` ۱۲ ساعت، لیست دسته ۶ ساعت، منو ۲۴ ساعت، suggest ۶۰ ثانیه. `search_text` از عنوان، برند (fa/en/aliases)، زنجیره‌ی دسته، SKU و گزینه‌های variant ساخته می‌شود. حذف محصول با سیگنال `post_delete` ردیف FTS را پاک می‌کند.
- ۰.۳.۱ (P0) — تایید `transaction_mode="IMMEDIATE"`، FTS5 startup check و `RedisCache` روی Django 5.2.19.

