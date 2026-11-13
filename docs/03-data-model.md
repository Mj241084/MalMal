# ۰۳ — مدل داده، ایندکس، کش و جستجو — نسخه ۰.۳

مرجع جریان‌ها: `02-spec.md`. نام فیلدها انگلیسی‌اند. همه‌ی مدل‌ها `created_at/updated_at` دارند مگر ذکر شود.
پول: `BigIntegerField` به **تومان**. زمان: UTC.

---

## ۱. تنظیمات SQLite و Django

- `journal_mode=WAL`، `synchronous=NORMAL`، `busy_timeout=5000`، `foreign_keys=ON`.
- `OPTIONS["transaction_mode"] = "IMMEDIATE"` — تاییدشده در Django 5.2.19 (تراکنش‌های نوشتن با `BEGIN IMMEDIATE` شروع می‌شوند).
- SQLite `select_for_update` را نادیده می‌گیرد. هم‌زمانی با تراکنش‌های `IMMEDIATE` و به‌روزرسانی‌های اتمیک شرطی (`UPDATE ... WHERE`) تامین می‌شود.
- FTS5 در SQLite هنگام startup در `CoreConfig.ready()` (`verify_sqlite_fts5`) بررسی می‌شود و اگر در بیلد پایتون نبود خطای واضح `ImproperlyConfigured` می‌دهد.
- نوشتن‌ها کوتاه: هیچ تماس شبکه (پیامک، درگاه) داخل تراکنش نباشد.
- پشتیبان: `sqlite3 .backup` شبانه به مسیر خارج از پوشه‌ی پروژه (فاز P6).

---

## ۲. اپ‌ها

| اپ | مسئولیت |
|----|---------|
| `core` | SiteSettings، StaticPage، FooterLink، ابزارهای مشترک (نرمال‌سازی فارسی، قالب‌تگ آیکون، شمسی) |
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

**OTPChallenge** (یک ردیف فعال برای هر شماره)
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
**Province**: `name`, `slug`, `sort`. **City**: `province` FK, `name`, `slug`. ایندکس `(province, name)`. داده با `import_geo` از دیتاست.

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
- `price`, `compare_at_price` null، `stock` int ≥ 0، `weight_g`، `max_per_order`، `is_active`, `sort`
- محصول ساده: دقیقاً یک variant پیش‌فرض (در ادمین به‌طور خودکار ساخته می‌شود).
- ایندکس: `(product, is_active)`, `sku`.
- تغییر `price/stock/is_active` ← `Product.refresh_aggregates()` (بخش ۵).

**ProductImage**: `product`, `variant` null, `image`, `alt`, `sort`. چند اندازه‌ی WebP تولید می‌شود.

**SpecAttribute**: `category` FK (اعمال برای کل زیردرخت), `name`, `type` (`text/number/bool/choice`), `unit`, `is_filterable`, `sort`.
**ProductSpecValue**: `product`, `attribute`, `value_text`, `value_number` null. ایندکس `(attribute, value_number)`, `(attribute, value_text)`, `(product, attribute)` unique.

**StockMovement** (دفتر): `variant`, `delta`, `reason` (`order/cancel/expire/manual/return`), `order_item` null, `note`. فقط افزودنی (append-only).

### marketing
**Banner**: `title`, `alt`, `image_desktop`, `image_mobile`, `placement` (`home_hero/home_strip/...`), `target_type` (`none/product/category/collection/url`), `target_product|target_category|target_collection` FK null، `target_url`, `starts_at`, `ends_at` (ذخیره UTC؛ در ادمین با ویجت تقویم شمسی طبق `06`)، `sort`, `is_active`. اعتبارسنجی: دقیقاً یک مقصد متناسب با `target_type`.

**Collection**: `title`, `slug`, `description`, `cover`, `mode` (`manual/rule`), `is_active`, `starts_at`, `ends_at` (ویجت شمسی مثل Banner), `seo_*`.
- قاعده‌ای: `categories` M2M، `brands` M2M، `min_discount_pct`، `min_price`، `max_price`، `only_in_stock`، `sort_by`، `limit`.
- دستی: **CollectionItem** (`collection`, `product`, `sort`).
- `rev` (کش).

**HomeBlock**: `kind` (`hero/categories/product_rail/collection_rail/banner_strip/brands/trust`), `title`, `collection` FK null, `category` FK null, `rail_source` (`best_selling/newest/discounted`), `limit`, `sort`, `is_active`.

**TrustItem** (مزیت‌های فروشگاه، بلوک `trust`): `icon` (نام نماد در sprite)، `title`، `subtitle`، `is_placeholder` bool (seed اولیه `True`)، `sort`، `is_active`. در ادمین ردیف placeholder با نشان هشدار؛ `manage.py check_launch` تا وقتی placeholder فعال است هشدار می‌دهد.

### core
**SiteSettings** (singleton): نام، لوگو (روشن/تاریک)، تلفن، آدرس، ساعات کاری، لینک‌های اجتماعی، آستانه‌ی ارسال رایگان، آستانه‌ی «موجودی کم»، پارامترهای OTP، ساعت مجاز ارسال «موجود شد» (پیش‌فرض ۸ تا ۲۱)، `trust_marks_html` (قطعه‌ی HTML نماد اعتماد/اینماد؛ فقط ادمین؛ خالی = نمایش داده نمی‌شود).
- **مشخصات فروشنده (برای فاکتور، C7):** `legal_name`، `economic_code`، `national_id` (شناسه‌ی ملی)، `registration_no`، `legal_address`، `legal_postal_code`، `legal_phone`. خالی مجاز؛ فاکتور فیلدهای خالی را نشان نمی‌دهد.
**StaticPage**: `slug`, `title`, `body`, `is_active`, `needs_review` bool (پیش‌فرض `False`؛ متن پیش‌نویسی مثل صفحه‌ی ارسال `True` می‌شود و فروشنده در ادمین خاموشش می‌کند؛ `check_launch` هشدار می‌دهد). **FooterLink**: `group`, `title`, `url`, `sort`.

### cart
**Cart**: `user` OneToOne. **CartItem**: `cart`, `variant`, `qty`. unique `(cart, variant)`. قیمت ذخیره نمی‌شود.

### orders
**Order**
- `number` unique (غیرترتیبی)، `user` FK، `status`
- مبالغ: `items_total`, `shipping_cost`, `discount_total`, `payable`
- **snapshot خریدار:** `buyer_name`, `buyer_mobile`, `buyer_national_code`, `buyer_email`
- **snapshot گیرنده و آدرس:** `recipient_name`, `recipient_mobile`, `province_name`, `city_name`, `address_text`, `plate`, `unit`, `postal_code`, `lat`, `lng`
- `shipping_method` FK null + `shipping_method_title` + `shipping_payment_mode` (snapshot)، `customer_note`
- `tracking_code` (خالی مجاز؛ برای روش‌های `has_tracking` هنگام تغییر به `shipped` اجباری)
- `placed_at`, `paid_at`, `reserved_until`, `cancelled_at`, `cancel_reason`
- ایندکس: `(user, -placed_at)`, `(status, reserved_until)`, `number`.

**OrderItem**: `order`, `variant` FK(SET_NULL), snapshot: `product_title`, `variant_title`, `sku`, `unit_price`, `qty`, `image_path`، `warranty_text`.
**OrderStatusLog**: `order`, `from_status`, `to_status`, `by_user` null, `note`, `created_at`.
**ShippingMethod**: `title`, `code`, `base_cost`, `per_kg_cost`, `free_over` null, `eta_min_days`, `eta_max_days`, `provinces` M2M (خالی = همه)، `has_tracking` bool (با کد رهگیری؟)، `payment_mode` (`prepaid` = کرایه در سایت، `collect` = پس‌کرایه؛ تیپاکس v1: `collect`)، `max_weight_g` null (سقف وزن مرسوله/قلم؛ null = بدون سقف)، `is_active`, `sort`.

### payments
**PaymentGateway**: `code` (`zarinpal`), `title`, `logo`, `is_active`, `sort`, `min_amount`, `max_amount`. اسرار درگاه فقط در env.
**Payment**: `order`, `gateway_code`, `amount`, `authority`, `ref_id`, `card_pan_masked`, `status` (`initiated/redirected/verified/failed/cancelled`), `request_payload`/`verify_payload` (JSON، بدون اسرار), `verified_at`, `ip`. unique `(gateway_code, authority)`.

### engagement
**Like**: `user`, `product`, `created_at`. unique `(user, product)`، ایندکس `(product)`.
**Review**: `user`, `product`, `rating` 1–5, `body`, `status`, `is_verified_buyer`, `moderated_by`, `moderated_at`, `admin_reply`. unique `(user, product)`، ایندکس `(product, status, -created_at)`.
**ProductDailyStat**: `product`, `date`, `purchases`, `views`. unique `(product, date)`. برای محاسبه‌ی ۳۰ روزه‌ی غلتان.
**StockSubscription** `[DECIDED]` (فاز P6): `user`, `variant`, `notified_at` null، `created_at`. unique `(user, variant)` برای اشتراک **باز** (`notified_at IS NULL`)؛ بعد از ارسال پیامک `notified_at` ثبت و اشتراک بسته می‌شود و کاربر می‌تواند دوباره مشترک شود. ایندکس `(variant, notified_at)`. جزئیات در `02` بخش ۱۳.

### notifications
**SmsLog**: `mobile`, `kind` (کلید قالب در `05`)، `provider_message_id`, `status`, `error`, `created_at`. بدون مقدار کد OTP.

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
به‌جای حذف کلیدها، `rev` بالا می‌رود و کلید قدیمی خودش منقضی می‌شود:
- `mm:v1:p:{id}:{rev}:detail` — بدنه‌ی HTML جزئیات محصول (بدون بخش شخصی)
- `mm:v1:p:{id}:{rev}:card` — کارت محصول
- `mm:v1:c:{id}:{subtree_rev}:list:{sort}:{filters_hash}:{page}` — لیست دسته (شامل زیردرخت)
- `mm:v1:p:{id}:{rev}:{cat_subtree_rev}:similar` — مشابه‌ها
- `mm:v1:col:{id}:{rev}:{subtree...}` — مجموعه
- `mm:v1:home:{epoch}` — بلوک‌های صفحه‌ی اصلی. `epoch` یک شمارنده‌ی سراسری در Redis (`INCR`) است.
- `mm:v1:menu:{epoch}` — منو و دسته‌های برتر
- `mm:v1:social:{product_id}` — شمارنده‌های لایک/خرید (TTL کوتاه، ۶۰ ثانیه)

`rev` و `subtree_rev` ستون **DB** هستند (نه Redis) تا اگر Redis پاک شد، نسخه‌ها برنگردند و کلید قدیمی با محتوای جدید اشتباه نخورد.

### دسته‌بندی فیلدها (جدول تصمیم)

| گروه | فیلدها | اثر |
|------|--------|-----|
| **LIST** (در لیست/کارت/جستجو دیده می‌شود) | `title`, `slug`, `brand`, `category`, `status`, `main_image`, `min_price`, `max_price`, `compare_at_min`, `discount_pct`, `in_stock` | `product.rev++` + `subtree_rev++` برای **همه‌ی اجداد** دسته‌ی جدید و **قدیم** + بازسازی FTS + `epoch++` اگر محصول در بلوک‌های سراسری باشد |
| **DETAIL** (فقط جزئیات) | `description`, `short_description`, `warranty_text`, مشخصات، تصاویر ثانویه، `seo_*` | فقط `product.rev++` |
| **COUNTER** | `like_count`, `review_count`, `rating_*`, `purchase_*`, `view_count` | **هیچ باطل‌سازی**. فقط `F()` و TTL کوتاه |
| **STRUCTURAL** | تغییر دسته (نام/والد/لوگو/ترتیب/منو)، بنر، Collection، HomeBlock، SiteSettings، FooterLink | `epoch++` و `rev/subtree_rev` مناسب |

### تشخیص تغییر
- در `from_db` مقادیر اولیه‌ی فیلدهای دسته‌بندی‌شده نگه داشته می‌شود (`_loaded_values`).
- در `save()` اختلاف محاسبه می‌شود و **سطح باطل‌سازی** (بیشترین سطح بین فیلدهای تغییرکرده) تعیین می‌شود. اگر هیچ فیلد LIST/DETAIL عوض نشده (مثلاً فقط COUNTER) هیچ کاری نمی‌شود.
- همه‌ی باطل‌سازی‌ها داخل `transaction.on_commit(...)` اجرا می‌شوند تا هیچ کلیدی قبل از commit و با داده‌ی قدیمی دوباره ساخته نشود.
- `rev++` با `F()` و `UPDATE` اتمیک.

### تغییر Variant
۱. `Variant.save()/delete()` ← `Product.refresh_aggregates()` (min/max/discount/in_stock/total_stock محاسبه، و فقط اگر مقدار عوض شد ذخیره می‌شود).
۲. اگر فیلد LIST عوض شد، سطح LIST بالا اعمال می‌شود. در غیر این صورت هیچ.
۳. **فروش عادی** (کم شدن موجودی) `rev` را عوض نمی‌کند، مگر موجودی از **صفر عبور کند** یا از آستانه‌ی «کم‌موجود» پایین‌تر برود (`in_stock` یا `low_stock` عوض شود).

### به‌روزرسانی‌های دسته‌جمعی
`QuerySet.update()` و `bulk_update()` سیگنال ندارند. قواعد:
- متد `ProductQuerySet.update_tracked(**fields)` و `bulk_update_tracked` که همان منطق را روی ردیف‌های تاثیرپذیر اجرا می‌کند.
- ادمین actions فقط از این متدها استفاده کنند.
- `update()` خام روی Product/Variant/Category در بقیه‌ی کد ممنوع است (تست معماری با grep/CI).

### Rebuild و جلوگیری از stampede
- حذف همراه با ساخت **lazy**: اولین درخواست بعد از تغییر کلید را می‌سازد، با قفل تک‌پرواز (`cache.add("lock:"+key, 1, 10)`)؛ درخواست‌های همزمان یا stale را می‌خوانند یا چند ده ms صبر می‌کنند.
- **Warm فعال** بعد از تغییر محصولات پربازدید (۲۰۰ تا بر اساس `purchase_count_30d + view_count`) و بعد از ایمپورت‌های بزرگ، با دستور `manage.py warm_cache` (cron/systemd timer). `[ASSUMPTION]` v1 بدون Celery. اگر لازم شد صف سبک (huey روی Redis یا `django.tasks`) بررسی شود.
- TTL امنیتی روی همه‌ی کلیدها (مثلاً ۲۴ ساعت) تا کلیدهای قدیمی جمع شوند.

### HTTP caching
`ETag`/`Last-Modified` برای جزئیات محصول و دسته بر پایه‌ی `rev`. بخش‌های شخصی با `Cache-Control: private, no-store` و بدون ETag مشترک.

### Rebuild دوره‌ای (cron)
| دستور | زمان | کار |
|-------|------|-----|
| `expire_orders` | هر ۵ دقیقه | سفارش‌های منقضی‌شده، برگرداندن موجودی |
| `recount_purchases` | شبانه | `purchase_count_30d` از `ProductDailyStat` + حذف ردیف‌های قدیمی‌تر از ۹۰ روز |
| `reconcile_counters` | شبانه | بازمحاسبه‌ی `like_count/review_count/rating_*` و اصلاح drift |
| `warm_cache` | بعد از `recount` | پیش‌ساخت پربازدیدها |

---

## ۶. شمارنده‌ها و متن‌های اجتماعی

**نوشتن:** با `F()` هنگام رویداد، داخل همان تراکنش:
- لایک/آن‌لایک: `Product.like_count ± 1` + ردیف `Like`.
- نظر تاییدشده/رد: `review_count`, `rating_sum` (و `rating_avg` محاسبه).
- پرداخت موفق: `purchase_count_total += qty` و `ProductDailyStat.purchases += qty` (upsert).

**خواندن (بدون join):** شمارنده‌ها از ستون‌های خود Product می‌آیند (ارزان). برای کاهش فشار در لیست‌ها از کش `social:{id}` استفاده می‌شود.

**بخش شخصی (lazy، `Cache-Control: private`):**
- صفحه‌ی محصول: `hx-get="/social/product/<id>/" hx-trigger="load"` ← partial با متن اجتماعی و وضعیت قلب.
- سبد/checkout: `hx-get="/social/cart/" hx-trigger="load"`.
- **قلب کارت‌ها:** یک درخواست دسته‌ای برای شناسه‌های صفحه (`hx-get="/likes/state/?ids=1,2,3" hx-trigger="load"`) که پاسخ آن HTML با `hx-swap-oob` برای قلب‌های لایک‌شده است. هیچ درخواستی به‌ازای هر کارت نیست.
- قلب: `hx-post="/likes/toggle/<id>/"` با پاسخ partial دکمه + به‌روزرسانی متن اجتماعی (OOB).

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

- بدون جدول. محاسبه‌ی lazy و کش با کلید `p:{id}:{rev}:{cat_subtree_rev}:similar`.
- امتیاز: هم‌دسته‌ی برگ (+۵)، هم‌برند (+۲)، نزدیکی قیمت (±۳۰٪ → +۲)، مقدار مشترک مشخصات فیلترپذیر (+۱ به‌ازای هر مورد). فقط `active` و `in_stock`. ۱۲ نتیجه.
- لود با `hx-trigger="revealed"`.

---

## ۹. مدل‌های تحت‌نظر برای ادمین

هر مدل باید `list_display`، `search_fields`، `list_filter` و `ordering` معنادار داشته باشد. Inlineها: Product ← Variant, ProductImage, ProductSpecValue؛ Order ← OrderItem (فقط‌خواندنی)، OrderStatusLog؛ Collection ← CollectionItem. مدل‌های حساس (Payment, StockMovement, OTPChallenge, SmsLog) فقط‌خواندنی.

---

## ۱۰. نکات پایان

- هر مهاجرت بزرگ داده‌ای (path دسته‌ها، FTS) قابل اجرای مجدد و idempotent باشد.
- تست‌ها حداقل: ترتیب و idempotency سینک سبد، callback پرداخت تکراری، رقابت دو سفارش روی آخرین موجودی، قفل OTP، سطح باطل‌سازی کش برای هر گروه فیلد، کوئری زیردرخت (`1/5/` در برابر `1/50/`).

---

## ۱۱. تغییرات

- ۰.۳.۱ (P0) — تایید `transaction_mode="IMMEDIATE"`، FTS5 startup check و `RedisCache` روی Django 5.2.19.

