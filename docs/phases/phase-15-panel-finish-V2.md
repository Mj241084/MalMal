# فاز P15: تکمیل پنل و بازنشسته‌کردن ادمین برای کار روزانه

**هدف:** پنل تنها ابزار روزانه شود: داشبورد کامل، جستجو و بج‌های واقعی، دسترسی هر نقش دقیقاً مطابق ماتریس، و مستند کار روزانه. بعد از این فاز، فازهای پنل (P9 تا P15) بسته‌اند.

---

## ۰. قواعد این نشست (سخت‌گیرانه)

- پروژه: فروشگاه آنلاین «مل‌مل»، Django + HTMX + DaisyUI، فارسی و RTL. با کاربر فارسی و کوتاه حرف بزن؛ کد و کامنت و پیام commit انگلیسی.
- فقط فایل‌هایی را که در این بریف نام برده شده می‌خوانی و تغییر می‌دهی. اسکیل اجرا نکن (از جمله `unslop` که بریف قبلی فاز می‌گفت؛ در این فاز بررسی ظاهر با من است)، وب نگرد، فایل اضافه نخوان. فقط دستورهای گام ۰ و گام ۶ و grepهای نام‌برده‌شده مجازند.
- **بررسی چشمی را خودت انجام نمی‌دهی.** مرورگر، Playwright و اسکرین‌شات ممنوع است. فقط «فهرست بررسی چشمی» پایین را در گزارش آخر به من بده.
- **تست‌ها فقط دو بار اجرا می‌شوند:** گام ۰ و گام ۶. وسط کار تست اجرا نکن.
- خطای `unable to open database file` مشکل محیط (قفل یا مسیر موقت ویندوز) است، نه کد. دنبال علتش نگرد؛ فقط با `TEMP`/`TMP` داخل پروژه اجرا کن (دستور گام ۰). اگر باز هم آمد، همان را گزارش کن و ادامه بده.
- اگر تستی شکست خورد:
  - اگر تقصیر کد یا تست تازه‌ی همین فاز بود، خودت درستش کن.
  - اگر به کد قدیمی مربوط بود، فقط نام تست و خطا را گزارش کن و منتظر تایید من بمان. بدون تایید چیزی را برای رفع آن تغییر نده.
- تستی غیر از تست‌های همین بریف ننویس. پوشه‌های `tests` را نگرد؛ فقط یک نگاه به `apps/panel/tests/` برای یافتن helper ورود کارمند (`panel_login`) کافی است.
- هیچ `[DECIDED]` را عوض نکن. هیچ مجوز گروهی را در `setup_groups` عوض نکن. commit نزن مگر خودم بخواهم.
- سوال باز ۴ (گروه چهارم) جواب گرفت: **لازم نیست** (ممکن است بعداً عوض شود). فقط در اسناد ثبت می‌شود. بقیه‌ی `[OPEN]`ها (`09` بخش ۲.۱۰ و `02` بخش ۱۶) را بخوان؛ هر کدام که هنوز `[OPEN]` است، خودت تصمیم نگیر و در گزارش آخر فهرستش کن.

## مطالعه (فقط این‌ها)

`CLAUDE.md`، این بریف، و فایل‌های ویرایشی: `apps/panel/{providers.py,queries.py,nav.py}`، `apps/panel/views/{dashboard.py,orders.py,payments.py}`، `templates/panel/dashboard.html`، `templates/panel/shell.html`، `static/js/mm/panel.js`، و اسناد `docs/09-panel-spec.md`، `docs/02-spec.md` (فقط بخش ۱۶)، `docs/deploy.md` (بخش ۸)، `docs/00-README.md`، `docs/phases/STATUS.md`.

---

## گام ۰: وضعیت پایه

```powershell
$env:TEMP="$PWD\.tmp"; $env:TMP="$PWD\.tmp"; $env:UV_CACHE_DIR="$PWD\.uv-cache"
uv run pytest -q
```

نام تست‌های شکست‌خورده را یادداشت کن (خط پایه؛ انتظار: ۳۰۶ پاس). سه grep سریع:

```powershell
rg -n "\[TEMP\]" apps templates docs/phases
rg -n "admin:" templates/panel apps/panel
rg -n "grep_marker_none" apps/panel/tests
```

(grep سوم را اجرا نکن، فقط این را اجرا کن:)

```powershell
rg -ln "CaptureQueries|assert_max_num_queries|assert_num_queries" apps/panel/tests
```

- هر `[TEMP]` که پیدا شد را با لینک واقعی پنل جایگزین کن.
- لینک ادمین (`admin:`) باید فقط در `templates/panel/shell.html` و فقط برای superuser باشد (الان هست؛ دست نزن). اگر جای دیگری بود گزارش کن.
- فهرست فایل‌های تست که قبلاً گارد query دارند برایت مشخص می‌کند در گام ۴ چه چیزی تکراری است. لیست‌هایی که قبلاً گارد دارند دوباره تست نشوند.

---

## گام ۱: بج‌ها و جستجو (باگ پنهان: ناوبری به بج‌هایی ارجاع می‌دهد که ثبت نشده‌اند)

`nav.py` برای «سفارش‌ها» بج `orders_to_ship` و برای «پرداخت‌ها» بج `refunds` دارد، ولی در `providers.py` فقط `reviews_pending` ثبت است و `badges.counts_for` بی‌صدا ردشان می‌کند.

### `apps/panel/queries.py`

import `from apps.core.models import SiteSettings` را به `from apps.core.models import SiteSettings, StaticPage` تغییر بده و به انتهای فایل اضافه کن:

```python
# --- Phase 15 helpers --------------------------------------------------------


def pages_needing_review(limit: int = 5) -> list[StaticPage]:
    """Active static pages still marked as drafts (check_launch warns about the same ones)."""
    return list(StaticPage.objects.filter(is_active=True, needs_review=True).order_by("title")[:limit])
```

### `apps/panel/providers.py` (کل فایل)

```python
from django.db.models import Q
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Product, Variant
from apps.core.text import normalize_fa
from apps.orders.models import Order
from apps.panel import badges, queries, search
from apps.payments import services as payment_services


@badges.register("reviews_pending")
def reviews_pending() -> int:
    return queries.reviews_pending()


@badges.register("orders_to_ship")
def orders_to_ship() -> int:
    return queries.orders_to_ship()


@badges.register("refunds")
def refunds() -> int:
    return payment_services.refund_candidates().count()


@search.register("orders", "سفارش‌ها", "orders.view_order")
def orders_search(query: str) -> list[search.Hit]:
    condition = queries.order_search_q(query)
    if condition is None:
        return []
    rows = Order.objects.filter(condition).order_by("-created_at", "-pk")[: search.PER_PROVIDER]
    return [
        search.Hit(
            title=order.number,
            subtitle=f"{order.buyer_name} — {order.get_status_display()}",
            url=reverse("panel:order_detail", args=[order.number]),
        )
        for order in rows
    ]


# change_product, not view_product: the studio the hit opens needs both, and a link that ends in a 403 is worse than no hit
@search.register("products", "محصولات", "catalog.change_product")
def products_search(query: str) -> list[search.Hit]:
    text = normalize_fa(query, for_search=True)[:60]
    if len(text) < search.MIN_LENGTH:
        return []
    by_sku = Variant.objects.filter(sku__icontains=text).values("product_id")
    rows = Product.objects.filter(Q(search_text__contains=text) | Q(pk__in=by_sku)).order_by("-created_at")
    return [
        search.Hit(
            title=product.title,
            subtitle=product.get_status_display(),
            url=reverse("panel:product_studio", args=[product.pk]),
        )
        for product in rows[: search.PER_PROVIDER]
    ]


@search.register("customers", "مشتریان", "accounts.view_user")
def customers_search(query: str) -> list[search.Hit]:
    condition = queries.customer_search_q(query)
    if condition is None:
        return []
    rows = User.objects.filter(is_staff=False).filter(condition).order_by("-date_joined")[: search.PER_PROVIDER]
    return [
        search.Hit(
            title=user.get_full_name() or user.mobile,
            subtitle=user.mobile,
            url=reverse("panel:customer_detail", args=[user.pk]),
        )
        for user in rows
    ]
```

### باطل‌کردن بج بعد از هر عمل (وگرنه تا ۳۰ ثانیه عدد کهنه می‌ماند، حتی در سایدبار OOB همان پاسخ)

**`apps/panel/views/orders.py`**:
- import را به `from apps.panel import audit, badges, htmx, queries` تغییر بده.
- در `order_bulk`، بلافاصله بعد از حلقه‌ی `for pk in list(ids): ...` و قبل از `skipped = len(numbers) - done` اضافه کن:
  ```python
      badges.bust("orders_to_ship")
  ```
- در `order_status`، بعد از بلوک `try/except workflow.TransitionError` و درست قبل از `return _detail_response(request, number, DONE[data["to"]])` اضافه کن (لغو سفارش پرداخت‌شده یک «نیازمند بازگشت وجه» می‌سازد):
  ```python
      badges.bust("orders_to_ship")
      badges.bust("refunds")
  ```

**`apps/panel/views/payments.py`**:
- import را به `from apps.panel import audit, auth, badges, htmx, queries` تغییر بده.
- در `payment_refund`، داخل `else:` بعد از `audit.log(...)` و قبل از `message, level = "بازگشت وجه ثبت شد", "success"` اضافه کن:
  ```python
              badges.bust("refunds")
  ```
  (تورفتگی را با همان بلوک `else` هم‌تراز کن.)

### `templates/panel/shell.html`

placeholder جستجو را عوض کن: `placeholder="جستجو: سفارش، موبایل، کد رهگیری"` ← `placeholder="جستجو: سفارش، محصول، مشتری"`.

### `static/js/mm/panel.js`

قبل از آخرین `})(window.MM);` اضافه کن (Escape پنل نتایج جستجو را می‌بندد؛ الان فقط کلیک بیرون می‌بندد):

```javascript
  /* Escape closes the global search results */
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    var panel = document.getElementById("search-results");
    if (panel) panel.classList.add("hidden");
  });
```

---

## گام ۲: داشبورد نهایی

### `apps/panel/views/dashboard.py` (کل فایل)

```python
from __future__ import annotations

from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.panel import queries
from apps.panel.permissions import panel_view
from apps.payments import services as payment_services


@panel_view(authenticated_only=True)
@require_GET
def dashboard(request):
    user = request.user
    can_orders = user.has_perm("orders.view_order")
    can_reviews = user.has_perm("engagement.view_review")
    can_stock = user.has_perm("catalog.view_variant")
    can_pages = user.has_perm("core.view_staticpage")
    context = {
        "can_orders": can_orders,
        "can_reviews": can_reviews,
        "can_stock": can_stock,
        "can_pages": can_pages,
        "refunds": payment_services.refund_candidates().count() if user.has_perm("payments.view_payment") else 0,
    }
    if can_orders:
        context.update(to_ship=queries.orders_to_ship(), sales=queries.sales_last_30_days(), **queries.ship_queue(user))
    if can_reviews:
        context.update(reviews_pending=queries.reviews_pending(), **queries.review_queue(user))
    if can_stock:
        context.update(stock_alerts=queries.stock_alert_count(), wanted=queries.wanted_out_of_stock())
    if can_pages:
        context.update(
            review_pages=queries.pages_needing_review(), can_edit_pages=user.has_perm("core.change_staticpage")
        )
    return render(request, "panel/dashboard.html", context)
```

### `templates/panel/partials/_pages_review.html` (جدید)

```html
{% load core_tags %}
<section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
  <div class="flex items-center justify-between gap-3">
    <h2 class="text-lead font-medium">صفحه‌های نیازمند بازبینی</h2>
    <a href="{% url 'panel:pages' %}" class="text-small text-brand-ink">محتوا</a>
  </div>
  {% for page in review_pages %}
    <div class="flex items-center justify-between gap-3 {% if not forloop.first %}border-t pt-3{% endif %}">
      <span class="min-w-0 flex flex-col">
        <span class="text-small line-clamp-1">{{ page.title|fa_text }}</span>
        <bdi class="latin text-label text-ink-3">/pages/{{ page.slug }}/</bdi>
      </span>
      {% if can_edit_pages %}<a href="{% url 'panel:page_edit' page.pk %}" class="btn btn-sm h-10 bg-base-300 border shrink-0">بازبینی</a>{% endif %}
    </div>
  {% endfor %}
</section>
```

### `templates/panel/dashboard.html` (کل فایل)

```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}داشبورد{% endblock %}
{% block content %}
<div class="flex flex-col gap-6">
  {% include "panel/partials/_page_heading.html" with title="داشبورد" %}

  {% if refunds %}
    <a href="{% url 'panel:payments' %}" class="alert text-small hover:bg-base-300 transition-colors">
      {% icon "alert-circle" size=18 class="text-ink-2 shrink-0" %}
      <span>{{ refunds|fa_digits }} پرداخت تاییدشده نیاز به بازگشت وجه دارد</span>
    </a>
  {% endif %}

  {% if can_orders or can_reviews or can_stock %}
    <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3" aria-label="خلاصه">
      {% if can_orders %}
        <a href="{% url 'panel:orders' %}" class="bg-base-100 border rounded-box p-4 flex flex-col gap-1 hover:bg-base-300 transition-colors">
          <span class="text-small text-ink-2">منتظر ارسال</span>
          <span class="text-title font-medium">{{ to_ship|fa_digits }}</span>
          <span class="text-label text-ink-3">پرداخت‌شده یا در حال آماده‌سازی</span>
        </a>
        <div class="bg-base-100 border rounded-box p-4 flex flex-col gap-1">
          <span class="text-small text-ink-2">فروش ۳۰ روز اخیر</span>
          <span class="text-title font-medium whitespace-nowrap">{{ sales|toman }} <span class="text-small text-ink-2 font-normal">تومان</span></span>
          <span class="text-label text-ink-3">سفارش‌های پرداخت‌شده</span>
        </div>
      {% endif %}
      {% if can_reviews %}
        <a href="{% url 'panel:reviews' %}" class="bg-base-100 border rounded-box p-4 flex flex-col gap-1 hover:bg-base-300 transition-colors">
          <span class="text-small text-ink-2">نظرهای منتظر تایید</span>
          <span class="text-title font-medium">{{ reviews_pending|fa_digits }}</span>
          <span class="text-label text-ink-3">تا تایید نشوند در فروشگاه دیده نمی‌شوند</span>
        </a>
      {% endif %}
      {% if can_stock %}
        <a href="{% url 'panel:inventory' %}?state=alert" class="bg-base-100 border rounded-box p-4 flex flex-col gap-1 hover:bg-base-300 transition-colors">
          <span class="text-small text-ink-2">ناموجود یا کم‌موجود</span>
          <span class="text-title font-medium">{{ stock_alerts|fa_digits }}</span>
          <span class="text-label text-ink-3">تنوع فعال از محصولات فعال</span>
        </a>
      {% endif %}
    </section>
  {% endif %}

  {% if can_orders %}{% include "panel/partials/_ship_queue.html" %}{% endif %}
  {% if can_reviews and review_queue %}{% include "panel/partials/_review_queue.html" %}{% endif %}
  {% if can_stock and wanted %}{% include "panel/partials/_wanted_stock.html" %}{% endif %}
  {% if can_pages and review_pages %}{% include "panel/partials/_pages_review.html" %}{% endif %}

  {% if not refunds and not can_orders and not can_reviews and not can_stock and not can_pages %}
    {% include "partials/_empty_state.html" with title="هنوز بخشی به حساب شما اضافه نشده" description="از مدیر کل بخواهید دسترسی‌های لازم را بدهد" %}
  {% endif %}
</div>
{% endblock %}
```

---

## گام ۳: پاس دسترس‌پذیری (فقط این سه grep، بدون بازنویسی)

```powershell
rg -n "btn-(square|circle)" templates/panel | rg -v "aria-label"
rg -n "<img" templates/panel | rg -v "alt="
rg -n "<th>|<th " templates/panel | rg -v "scope="
```

هر موردی که پیدا شد را درجا اصلاح کن: دکمه‌ی آیکونی `aria-label` فارسی بگیرد، `<img>` بدون `alt` یک `alt=""` (تزئینی) یا متن مناسب بگیرد، `<th>` بدون `scope` بشود `scope="col"`. هر grep باید صفر نتیجه بدهد. (اگر یک مورد در جای دیگری از لیست‌ها فقط چون چندخطی است پیدا شد و واقعاً درست بود، توضیح بده.) به چیز دیگری دست نزن.

---

## گام ۴: تست‌ها (فقط همین فایل، همین مجموعه)

`apps/panel/tests/test_p15.py`. دلیل هر تست: ماتریس مجوز واقعاً با دسترسی عملی یکی است؛ لیست‌های تازه N+1 ندارند؛ جستجو مجوز را رعایت می‌کند؛ بج‌های ناوبری همه شمارنده دارند (باگ بی‌صدای بالا).

اگر یک گارد query برای یکی از موردهای `customers`/`sms`/`audit`/`dashboard` از قبل در تست‌های قبلی هست (خروجی grep گام ۰)، همان یکی را اینجا تکرار نکن.

```python
"""P15: permissions match real access, new lists have no N+1, global search respects permissions."""

from __future__ import annotations

import time

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import User
from apps.engagement.models import Review
from apps.notifications.models import SmsLog
from apps.panel import audit, badges, nav

pytestmark = pytest.mark.django_db
STRONG = "Str0ng-pass-92"


def panel_login(client, user):
    client.force_login(user)
    session = client.session
    session["panel_login_at"] = int(time.time())
    session.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
    return client


def _staff(mobile: str, *, group: str = "", perms=()) -> User:
    staff = User.objects.create_user(mobile, is_staff=True)
    if group:
        staff.groups.add(Group.objects.get(name=group))
    for codename in perms:
        staff.user_permissions.add(Permission.objects.get(codename=codename))
    return staff


# --- permissions match access -------------------------------------------------

# What each group must never see / must see (docs/09 §2.5). If one fails, report it: do not change setup_groups.
HIDDEN = {
    "نظرها": {"orders", "payments", "products", "categories", "brands", "inventory", "marketing", "content", "customers", "settings", "sms", "system"},
    "فروش": {"marketing", "content", "settings", "sms", "system"},
    "محتوا": {"orders", "payments", "customers", "settings", "sms", "system"},
}  # fmt: skip
SEEN = {
    "نظرها": {"dashboard", "reviews"},
    "فروش": {"dashboard", "orders", "payments", "customers"},
    "محتوا": {"dashboard", "products", "inventory", "marketing", "content"},
}


@pytest.mark.parametrize("group", ["نظرها", "فروش", "محتوا"])
def test_every_visible_link_opens_and_every_hidden_one_is_forbidden(client, group):
    call_command("setup_groups")
    staff = _staff("09120000011", group=group)
    panel_login(client, staff)
    visible = {item.key for item in nav.ITEMS if nav._allowed(staff, item)}
    assert SEEN[group] <= visible and not (HIDDEN[group] & visible)
    for item in nav.ITEMS:  # follow=True: an index page that redirects to a 403 must fail too
        response = client.get(reverse(item.url_name), follow=True)
        assert response.status_code == (200 if item.key in visible else 403), (group, item.key)


def test_superuser_opens_every_link(client):
    boss = User.objects.create_superuser("09120000010", STRONG)
    panel_login(client, boss)
    for item in nav.ITEMS:
        assert client.get(reverse(item.url_name), follow=True).status_code == 200, item.key


def test_every_nav_badge_has_a_counter():
    assert {item.badge for item in nav.ITEMS if item.badge} <= set(badges.BADGES)


# --- no N+1 on the new lists --------------------------------------------------


def _count(client, url) -> int:
    client.get(url)  # warm the caches (Redis, session) first
    with CaptureQueriesContext(connection) as ctx:
        assert client.get(url).status_code == 200
    return len(ctx)


@pytest.fixture
def boss_client(client):
    return panel_login(client, User.objects.create_superuser("09120000010", STRONG))


def test_customers_list_query_count_does_not_grow_with_rows(boss_client):
    url = reverse("panel:customers")
    for i in range(2):
        User.objects.create_user(f"0912001{i:04d}")
    few = _count(boss_client, url)
    for i in range(2, 12):
        User.objects.create_user(f"0912001{i:04d}")
    assert _count(boss_client, url) == few


def test_sms_and_audit_lists_query_count_does_not_grow_with_rows(boss_client):
    admin = User.objects.get(mobile="09120000010")
    urls = (reverse("panel:sms"), reverse("panel:audit"))

    def add(n: int) -> None:
        for _ in range(n):
            SmsLog.objects.create(mobile="09120000099", kind="otp", status=SmsLog.STATUS_SENT)
            audit.log(admin, admin, audit.CHANGE, "x")

    add(2)
    few = [_count(boss_client, url) for url in urls]
    add(8)
    assert [_count(boss_client, url) for url in urls] == few


def test_dashboard_query_count_does_not_grow_with_the_review_queue(boss_client, product):
    def add(start: int, stop: int) -> None:
        for i in range(start, stop):
            user = User.objects.create_user(f"0912002{i:04d}")
            Review.objects.create(user=user, product=product, rating=5, body="نظر آزمایشی برای صف")

    url = reverse("panel:dashboard")
    add(0, 2)
    few = _count(boss_client, url)
    add(2, 6)
    assert _count(boss_client, url) == few


# --- global search respects permissions --------------------------------------


def _search(client, query: str) -> str:
    return client.get(reverse("panel:search"), {"q": query}).content.decode()


def test_search_shows_orders_and_products_only_to_those_allowed(client, placed_order, product):
    order_url = f"/panel/orders/{placed_order.number}/"
    studio_url = f"/panel/products/{product.pk}/"

    reviewer = _staff("09120000012", perms=("view_review",))
    panel_login(client, reviewer)
    assert order_url not in _search(client, placed_order.number)
    assert studio_url not in _search(client, "WM-1234")

    viewer = _staff("09120000013", perms=("view_product",))  # the studio needs change_product too
    panel_login(client, viewer)
    assert studio_url not in _search(client, "WM-1234")

    boss = User.objects.create_superuser("09120000010", STRONG)
    panel_login(client, boss)
    assert order_url in _search(client, placed_order.number)
    assert studio_url in _search(client, "WM-1234")
```

اگر `placed_order` شماره‌ی سفارش را با حروف بزرگ می‌سازد و جستجو با `normalize_fa` چیزی را تغییر می‌دهد که تست را می‌شکند، خود تست را اصلاح کن (نه provider را)، مگر واقعاً باگ باشد؛ در آن صورت گزارش بده.

---

## گام ۵: اسناد (فقط این‌ها)

### `docs/panel-guide.md` (جدید، حداکثر دو صفحه، فارسی ساده، بدون اصطلاح فنی)

راهنمای کوتاه روزانه‌ی کارمند با این سرفصل‌ها و دقیقاً همین واقعیت‌ها:
1. **ورود:** `/panel/login/` با موبایل و رمز؛ نشست ۱۲ ساعته؛ تغییر رمز و خروج از همه‌ی دستگاه‌ها در «حساب من».
2. **هر روز صبح:** داشبورد (منتظر ارسال، نظرهای منتظر، ناموجودها، صف ارسال، هشدار بازگشت وجه، صفحه‌های نیازمند بازبینی)؛ بج‌های سایدبار هر ۶۰ ثانیه تازه می‌شوند؛ جستجوی بالا برای شماره‌ی سفارش، موبایل، محصول و مشتری.
3. **پردازش سفارش:** پرداخت‌شده ← «شروع آماده‌سازی» ← «ثبت ارسال» با کد رهگیری تیپاکس (فقط حرف لاتین، عدد و خط تیره، حداکثر ۲۵ نویسه؛ پیامک خودکار می‌رود) ← «ثبت تحویل». «کپی مشخصات» برای چسباندن در پنل تیپاکس. لغو سفارش دلیل اجباری دارد، موجودی برمی‌گردد و پیامک می‌رود.
4. **بازگشت وجه:** اول مبلغ را از پنل زرین‌پال برگردان؛ بعد در «پرداخت‌ها ← نیازمند بازگشت وجه» (یا صفحه‌ی سفارش) «ثبت بازگشت وجه» را با شماره‌ی پیگیری در یادداشت بزن. اینجا فقط ثبت می‌شود، پول جابه‌جا نمی‌شود.
5. **تغییر موجودی:** «انبار ← تغییر موجودی»؛ سه حالت افزودن، کم‌کردن، تنظیم به عدد شمارش؛ دلیل اجباری؛ هر تغییر در دفتر گردش موجودی می‌ماند. اگر هم‌زمان کسی موجودی را عوض کرده باشد پیام می‌دهد و عدد تازه را نشان می‌دهد.
6. **افزودن محصول:** عنوان و دسته ← پیش‌نویس ← عکس (اولی تصویر اصلی است) ← تنوع و قیمت ← مشخصات ← «فعال‌سازی». چک‌لیست انتشار: عنوان، دسته و دست‌کم یک تنوع فعال با قیمت بیشتر از صفر اجباری‌اند؛ نبودن عکس، توضیح یا برند فقط هشدار است. محصول سفارش‌دار حذف نمی‌شود، بایگانی می‌شود.
7. **نظرها:** تایید، رد با دلیل داخلی، پاسخ فروشگاه، تایید دسته‌جمعی.
8. **بازاریابی و محتوا:** یک پاراگراف (چیدمان صفحه‌ی اصلی، بنر، مجموعه، مزیت‌ها، صفحه‌های ثابت، لینک‌های فوتر).
9. **فقط مدیر کل:** تنظیمات، مشتریان (تغییر کد ملی با دلیل)، همکاران، گزارش پیامک، ممیزی، آمادگی انتشار.
10. **پیام‌های رایج:** «وضعیت سفارش هم‌زمان تغییر کرد؛ صفحه را دوباره باز کنید» یعنی همکار دیگری همان سفارش را تغییر داده؛ صفحه را تازه کن و دوباره بزن.

### سایر اسناد

- `docs/00-README.md`: ردیف `panel-guide.md` را به جدول بخش ۱ اضافه کن (راهنمای روزانه‌ی کارمند، ✅) و یک خط «تغییرات» (۰.۱۳ — P15: تکمیل پنل). اگر بخش ۷ (چک‌لیست انتشار) چیزی درباره‌ی پنل لازم دارد که نیست، یک مورد کوتاه اضافه کن (اولین کارمند از پنل ساخته و ورودش آزموده شود).
- `docs/09-panel-spec.md`:
  - سوال باز ۴ را `[RESOLVED]` کن: «گروه چهارم لازم نیست؛ ممکن است بعداً عوض شود».
  - ماژول ۱ (داشبورد) و بخش ۲.۹ را با واقعیت هم‌تراز کن (بلوک `needs_review` و provider جستجوی سراسری محصول و سفارش و مشتری در P15 ساخته شد؛ بج‌های `orders_to_ship` و `refunds` ثبت و پس از هر عمل باطل می‌شوند؛ provider محصول مجوز `change_product` می‌خواهد).
  - یک خط «تغییرات».
- `docs/02-spec.md` بخش ۱۶: مورد ۱۰ را `[RESOLVED]` کن. بقیه‌ی `[OPEN]`ها را دست نزن.
- `docs/deploy.md` بخش ۸: ببین «اولین کارمند» (از پنل: سیستم ← همکاران) و «`setup_groups` بعد از هر استقرار با مجوز تازه» آمده‌اند؛ اگر نه، اضافه کن. یک خط هم به `docs/panel-guide.md` ارجاع بده. یک خط «تغییرات» (اگر بخش تغییرات دارد).
- `docs/phases/STATUS.md`: ردیف P15 را ✅ کن و یک یادداشت کوتاه بنویس (باگ بج‌های ثبت‌نشده، providerها، بلوک صفحه‌های بازبینی، تست نقش‌محور). یک خط هم بنویس که مرحله‌ی «دودی انتها‌به‌انتها» و چک‌لیست `00` بخش ۷ با کاربر است.

---

## گام ۶: پایان کار

فقط این‌ها را اجرا کن (با همان متغیرهای محیطی گام ۰):

```powershell
uv run python scripts/build_sprite.py
uv run ruff check .
uv run ruff format .
pnpm run build:css
uv run pytest -q
```

اگر `pnpm` به‌خاطر محیط شکست خورد، رفعش نکن؛ بنویس که باید خودم اجرا کنم. نتیجه‌ی `pytest` را با خط پایه‌ی گام ۰ مقایسه کن (انتظار: ۳۰۶ + تست‌های تازه). بعد grepهای `04` بخش ۱۳ روی `templates/panel/` (چهار الگوی همان بخش) و grepهای گام ۳ را اجرا کن؛ همه باید صفر باشند. `[TEMP]` هم باید صفر باشد.

## گزارش پایانی

چند خط: چه ساخته یا اصلاح شد، نتیجه‌ی `pytest` نسبت به خط پایه، موردهای گام ۳ که اصلاح شد، `[OPEN]`های باقی‌مانده (اگر هست)، و هر تناقض یا شکستی که به تایید من نیاز دارد. نیازی به فهرست «کارهای من» نیست مگر چیز تازه‌ای پیدا شد.

---

## فهرست بررسی چشمی (برای من، نه برای تو)

دو تم، عرض ۳۲۰ و ۱۲۸۰:

1. **داشبورد با هر نقش** (مدیر کل، فروش، محتوا، نظرها): فقط بلوک‌های مجاز دیده می‌شوند؛ بلوک «صفحه‌های نیازمند بازبینی» با یک صفحه‌ی `needs_review` ظاهر می‌شود؛ ارتفاع بلوک‌ها پرش ندارد.
2. **بج‌ها:** عدد «سفارش‌ها» بعد از «شروع آماده‌سازی» و عدد «پرداخت‌ها» بعد از ثبت بازگشت وجه یا لغو سفارش پرداخت‌شده، فوراً عوض می‌شود (نه بعد از ۳۰ ثانیه).
3. **جستجوی بالا:** شماره‌ی سفارش، نام یا SKU محصول، موبایل مشتری؛ Escape نتایج را می‌بندد؛ با نقش «نظرها» هیچ سفارش و محصولی نتیجه نمی‌دهد.
4. **ناوبری هر نقش:** لینکی که دیده می‌شود به ۴۰۳ نمی‌رسد.
5. **کیبورد:** با Tab در جزئیات سفارش، استودیوی محصول و مودال‌ها (ثبت ارسال، لغو، بازگشت وجه) فوکوس دیده می‌شود و Esc مودال را می‌بندد؛ دکمه‌های آیکونی با صفحه‌خوان نام دارند.
6. **دودی انتها‌به‌انتها** (با من):
   - ورود کارمند ← سفارش پرداخت‌شده ← آماده‌سازی ← ارسال با کد رهگیری ← پیامک ← تحویل.
   - محصول تازه با عکس، تنوع و مشخصات ← فعال‌سازی ← دیدنش در فروشگاه.
   - تغییر موجودی و دیدن ردیف دفتر.
   - تایید یک نظر.
   - ثبت یک بازگشت وجه.
7. **چک‌لیست انتشار** `00` بخش ۷ را با هم مرور می‌کنیم.