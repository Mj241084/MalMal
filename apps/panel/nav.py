"""Sidebar registry."""

from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse

GROUPS = (
    ("daily", "کار روزانه"),
    ("catalog", "کاتالوگ"),
    ("store", "فروشگاه"),
    ("customers", "مشتریان"),
    ("admin", "مدیریت"),
)


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    url_name: str
    icon: str
    group: str
    perms: tuple[str, ...] = ()
    superuser: bool = False
    badge: str = ""


@dataclass(frozen=True)
class NavLink:
    item: NavItem
    url: str
    active: bool


ITEMS: list[NavItem] = [
    NavItem("dashboard", "داشبورد", "panel:dashboard", icon="layout-dashboard", group="daily"),
    NavItem(
        "orders",
        "سفارش‌ها",
        "panel:orders",
        icon="shopping-bag",
        group="daily",
        perms=("orders.view_order",),
        badge="orders_to_ship",
    ),
    NavItem(
        "payments",
        "پرداخت‌ها",
        "panel:payments",
        icon="credit-card",
        group="daily",
        perms=("payments.view_payment",),
        badge="refunds",
    ),
]


def _allowed(user, item: NavItem) -> bool:
    if item.superuser:
        return user.is_superuser
    return not item.perms or any(user.has_perm(perm) for perm in item.perms)


def visible_groups(user, path: str) -> list[tuple[str, list[NavLink]]]:
    groups = []
    for code, label in GROUPS:
        links = []
        for item in ITEMS:
            if item.group != code or not _allowed(user, item):
                continue
            url = reverse(item.url_name)
            active = path == url if item.key == "dashboard" else path.startswith(url)
            links.append(NavLink(item, url, active))
        if links:
            groups.append((label, links))
    return groups
