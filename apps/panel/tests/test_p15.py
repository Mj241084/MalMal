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
    "نظرها": {
        "orders",
        "payments",
        "products",
        "categories",
        "brands",
        "inventory",
        "marketing",
        "content",
        "customers",
        "settings",
        "sms",
        "system",
    },
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
