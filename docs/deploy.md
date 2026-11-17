# استقرار مل‌مل — نسخه ۰.۲

این سند مرحله‌به‌مرحله است: از سرور خالی تا سرویس در حال اجرا، و بعد از آن بروزرسانی و پشتیبان/بازیابی.
فایل‌های همراه: `deploy/malmal.service`، `deploy/nginx.conf.example`، `deploy/crontab.example`.

مسیرها و دامنه در نمونه‌ها `example.ir` و `/srv/malmal` هستند؛ پیش از اجرا با مقادیر واقعی عوض کنید.

---

## ۱. پیش‌نیاز سرور

- Ubuntu 22.04/24.04 (یا هر توزیع با `systemd`، `nginx` و `redis`).
- بسته‌ها: `nginx`، `redis-server`، `git`، `rsync`، `certbot` (با `python3-certbot-nginx`).
- کاربر بدون دسترسی `sudo` برای اجرای سرویس: `malmal`.
- `uv` برای کاربر `malmal` (پروژه فقط با `uv` و `pnpm` کار می‌کند — D27). Node روی سرور **لازم نیست**:
  `static/css/app.css` ساخته و commit می‌شود.

```bash
adduser --disabled-password --gecos "" malmal
su - malmal -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
```

Redis فقط روی لوپ‌بک گوش بدهد و رمز داشته باشد (`/etc/redis/redis.conf`):

```
bind 127.0.0.1
requirepass <رمز-تصادفی-بلند>
maxmemory-policy allkeys-lru
```

و در `.env`:

```
REDIS_URL=redis://:<رمز>@127.0.0.1:6379/1
```

---

## ۲. استقرار اول

```bash
sudo mkdir -p /srv/malmal && sudo chown malmal: /srv/malmal
su - malmal
git clone <repo> /srv/malmal
cd /srv/malmal
uv sync --no-dev --frozen
cp .env.example .env && nano .env      # همه‌ی مقدارها را پر کنید
```

مراحل به ترتیب (همه با `uv run python manage.py ...`):

1. `migrate`
2. `sync_geo`
3. `collectstatic --noinput`
4. `setup_groups`  (گروه‌های مجوز «محتوا»، «فروش»، «نظرها»)
5. `createsuperuser`  (مدیر کل)
6. `create_staff 0912... --group محتوا --group فروش`  (کارمند؛ برای مشتری کار نمی‌کند)
7. `rebuild_search`
8. `check_launch`  (تا وقتی خطا دارد منتشر نکنید؛ `--strict` هشدارها را هم خطا می‌بیند)

سپس سرویس و وب‌سرور و کران:

```bash
sudo cp deploy/malmal.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now malmal
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/malmal
sudo ln -s /etc/nginx/sites-available/malmal /etc/nginx/sites-enabled/
sudo certbot --nginx -d example.ir        # گواهی و https
sudo systemctl reload nginx
crontab -e                            # محتوای deploy/crontab.example (کاربر malmal)
```

**.env لازم در production:** `DJANGO_SECRET_KEY`، `REDIS_URL`، `ALLOWED_HOSTS`، `SITE_URL` (با `https`)،
`ADMIN_URL` (غیرپیش‌فرض)، `CSRF_TRUSTED_ORIGINS`، `SMS_BACKEND=smsir` + کلید و شناسه‌های قالب،
`ZARINPAL_MERCHANT_ID` با `ZARINPAL_SANDBOX=false`، `TRUSTED_PROXY_IPS=127.0.0.1`، `BACKUP_DIR`، `NESHAN_SERVICE_KEY`،
`SSL_REDIRECT=true`. `BACKUP_DIR` باید **بیرون از پروژه** باشد (ترجیحاً دیسک دیگر).

`sync_geo` پشتیبان استان/شهر است و هفتگی در cron می‌رود (`deploy/crontab.example`).

`TRUSTED_PROXY_IPS=127.0.0.1` چون gunicorn روی TCP لوپ‌بک اجرا می‌شود، نه سوکت یونیکس: با سوکت،
`REMOTE_ADDR` خالی است و محدودیت نرخ بر پایه‌ی IP کار نمی‌کند.

---

## ۳. بروزرسانی

```bash
cd /srv/malmal
git pull
uv sync --no-dev --frozen
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
sudo systemctl restart malmal
uv run python manage.py warm_cache
```

اگر تغییر مدل/قالب کش‌شده بوده، `warm_cache` بعد از `restart` اجرا شود (نه قبل).

---

## ۴. پشتیبان و بازیابی

پشتیبان شبانه (کران، ۰۳:۵۰):

```bash
uv run python manage.py backup_db --with-media   # db-YYYYMMDD-HHMMSS.sqlite3 + media/ در BACKUP_DIR
```

`backup_db` از API آنلاین SQLite استفاده می‌کند (کپی consistent حتی وقتی سرویس بالاست)،
`PRAGMA integrity_check` را روی کپی اجرا می‌کند، شمار ردیف‌های چهار جدول اصلی را چاپ می‌کند و
نسخه‌های قدیمی‌تر از ۱۴ روز را پاک می‌کند (`--keep-days`).

**`--with-media` (P7):** کپی `MEDIA_ROOT` داخل خود دستور انجام می‌شود (`rsync -a` اگر باشد، وگرنه
`shutil.copytree`)، چون cron متغیرهای `.env` را نمی‌خواند و `$BACKUP_DIR` در خط crontab خالی می‌ماند
(نتیجه: نوشتن روی `/media/`). پس خط crontab فقط `backup_db --with-media` است و هیچ `rsync` جداگانه‌ای ندارد.

**بازیابی:**

1. `sudo systemctl stop malmal`
2. `cp "$BACKUP_DIR/db-....sqlite3" /srv/malmal/db.sqlite3`
3. `rm -f /srv/malmal/db.sqlite3-wal /srv/malmal/db.sqlite3-shm`
4. `rsync -a "$BACKUP_DIR/media/" media/`  (اگر عکس‌ها هم باید برگردند)
5. `sudo systemctl start malmal`
6. `uv run python manage.py check_launch` و بازدید چند سفارش از ادمین

پشتیبان **رسیدگی‌شده** (تمرین بازیابی) قبل از انتشار الزامی است؛ یک‌بار روی سرور staging همین مراحل را انجام دهید.

---

## ۵. پرداخت روی سفارش مرده یا تکراری

پرداخت تاییدشده‌ای که سفارشش لغو/منقضی شده یا پرداخت دوم روی سفارشی که قبلاً پرداخت شده،
خودکار برنمی‌گردد؛ فقط لاگ می‌شود (D-P6 §2). مسیر رسیدگی:

1. `journalctl -u malmal | grep refund`  (شماره‌ی سفارش و `payment pk`)
2. در پنل زرین‌پال بازگشت وجه را انجام دهید.
3. در ادمین: پرداخت‌ها → فیلتر «نیازمند بازگشت وجه» → انتخاب ردیف‌ها → اکشن **«ثبت بازگشت وجه انجام‌شد»**
   (وضعیت را `refunded` می‌کند و پرداخت را از گزارش نیازمند بازگشت وجه بیرون می‌آورد؛ مجوز
   `orders.manage_order_status` لازم دارد). گزارش حالا پرداخت تکراری را هم نشان می‌دهد (P7).
4. اگر پرداخت روی سفارش منقضی دوباره رزرو شد، وضعیت سفارش را به مسیر عادی برگردانید (workflow).
5. `manage.py check_launch` بعد از رسیدگی نباید هشدار «نیازمند بازگشت وجه» بدهد.

---

## ۶. نکات Redis

- کلیدهای `epoch` و `trust_rev` کش‌های نسخه‌دار را می‌چرخانند. **پاک‌کردن بخشی از آن‌ها ممنوع است.**
  `FLUSHALL` کامل مجاز است (کش از نو ساخته می‌شود؛ بعدش `warm_cache`).
- `maxmemory-policy allkeys-lru` تا Redis با فشار حافظه سرویس را نخواباند.

---

## ۷. عیب‌یابی سریع

| نشانه | کار |
|-------|-----|
| ۵۰۰ بعد از استقرار | `journalctl -u malmal -n 200`؛ اغلب `DJANGO_SECRET_KEY`/`REDIS_URL` خالی در `.env` |
| استاتیک ۴۰۴ | `collectstatic --noinput` دوباره و مسیر `/static/` در nginx |
| کد ورود نمی‌رسد | `SMS_BACKEND=smsir`، `SMSIR_API_KEY` و `SMSIR_TEMPLATE_ID_OTP`؛ لاگ پیامک در ادمین |
| پرداخت خطا می‌دهد | `ZARINPAL_SANDBOX=false`، مرچنت‌کد درست، `SITE_URL` با `https` (callback از آن ساخته می‌شود) |
| «خبرم کن» پیامک نمی‌فرستد | شناسه‌ی قالب `back_in_stock`، ساعت بین `SiteSettings.back_in_stock_start_hour` و `end_hour`، و کران `send_back_in_stock` |

---

## ۸. پنل مدیریت (از P9)

بخش‌های این قسمت با اجرای فازهای P9 تا P15 معتبر می‌شوند (`docs/09-panel-spec.md`). تا آن موقع کار روزانه در ادمین است.

- **اولین کارمند:** پس از `setup_groups` با `create_staff 0912... --group فروش` (یا گروه دیگر) ساخته می‌شود و از `/panel/login/` وارد می‌شود. مدیر کل همان `createsuperuser` است؛ superuser از پنل ساخته نمی‌شود (D47). شماره‌ی یک مشتری موجود staff نمی‌شود.
- **ساخت همکار از پنل (از P14):** همکار تازه از «سیستم ← همکاران» ساخته می‌شود (موبایل، نام، گروه، رمز موقت) و دستور `create_staff` برای شماره‌ی موجود رفتار قبلی را دارد (رمز و گروه را به‌روز می‌کند). بعد از این فاز `setup_groups` باید یک‌بار دیگر اجرا شود تا مجوز `accounts.view_user` به گروه «فروش» برسد.
- **`setup_groups` بعد از هر استقرار که مجوز تازه دارد:** دستور idempotent است و مجوزهای تازه‌ی گروه‌ها (مثل `catalog.adjust_stock` در P12) فقط با اجرای آن به گروه‌ها می‌رسند. ترتیب: `migrate` ← `setup_groups` ← `collectstatic` ← restart.
- **آپلود تصویر:** پنل هر درخواست آپلود را زیر حدود ۱۵ مگابایت نگه می‌دارد و حد nginx ۲۰ مگابایت است (`client_max_body_size`؛ `[VERIFY]` با `deploy/nginx.conf.example`). اگر حد nginx کمتر باشد، آپلود چندتایی عکس محصول با ۴۱۳ شکست می‌خورد.
- **robots و noindex:** `/panel/` در `robots.txt` می‌آید (`Disallow`) و همه‌ی پاسخ‌های پنل `X-Robots-Tag: noindex, nofollow` و `Cache-Control: private, no-store` دارند (D44). مسیر ادمین همچنان در `robots.txt` نمی‌آید (`02` جدول P6، ردیف ۸).
- **`ADMIN_URL`** نباید با `panel/` شروع شود؛ `check_launch` از P9 خطا می‌دهد.
- **بازگشت وجه:** از P10 رسیدگی بخش ۵ در پنل هم انجام می‌شود (پرداخت‌ها ← «نیازمند بازگشت وجه») و با اکشن ادمین یک مسیر مشترک (`record_refund`) دارد.

---

## ۹. تغییرات

- ۰.۲ — بخش ۸ «پنل مدیریت» (اولین کارمند، `setup_groups` پس از مجوز تازه، حد آپلود، robots/noindex، `ADMIN_URL`، بازگشت وجه). این سند تا ۰.۱ بخش «تغییرات» نداشت.
