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
    NavItem("products", "محصولات", "panel:products", icon="package", group="catalog", perms=("catalog.view_product",)),
    NavItem(
        "categories",
        "دسته‌ها",
        "panel:categories",
        icon="layout-grid",
        group="catalog",
        perms=("catalog.view_category",),
    ),
    NavItem("brands", "برندها", "panel:brands", icon="tag", group="catalog", perms=("catalog.view_brand",)),
    NavItem(
        "reviews",
        "نظرها",
        "panel:reviews",
        icon="message-square",
        group="daily",
        perms=("engagement.view_review",),
        badge="reviews_pending",
    ),
    NavItem(
        "inventory", "انبار", "panel:inventory", icon="warehouse", group="catalog", perms=("catalog.view_variant",)
    ),
    NavItem(
        "marketing",
        "بازاریابی",
        "panel:marketing",
        icon="megaphone",
        group="store",
        perms=(
            "marketing.view_homeblock",
            "marketing.view_banner",
            "marketing.view_collection",
            "marketing.view_trustitem",
        ),
    ),
    NavItem(
        "content",
        "محتوا",
        "panel:content",
        icon="file-text",
        group="store",
        perms=("core.view_staticpage", "core.view_footerlink"),
    ),
    NavItem("customers", "مشتریان", "panel:customers", icon="users", group="customers", perms=("accounts.view_user",)),
    NavItem(
        "settings",
        "تنظیمات",
        "panel:settings_index",
        icon="settings",
        group="admin",
        perms=("core.change_sitesettings", "payments.change_paymentgateway", "orders.change_shippingmethod"),
    ),
    NavItem(
        "sms", "گزارش پیامک", "panel:sms", icon="message-circle", group="admin", perms=("notifications.view_smslog",)
    ),
    NavItem("system", "سیستم", "panel:system", icon="shield-check", group="admin", superuser=True),
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
