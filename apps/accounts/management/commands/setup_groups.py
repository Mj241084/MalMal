"""Create the staff permission groups of docs/02 §12 (idempotent). Superusers are the «مدیر کل»."""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

CRUD = ("add", "change", "delete", "view")
VIEW = ("view",)
GROUPS = {
    "محتوا": [
        (
            "catalog",
            ("brand", "category", "product", "variant", "productimage", "specattribute", "productspecvalue"),
            CRUD,
        ),
        ("catalog", ("stockmovement",), VIEW),
        ("engagement", ("stocksubscription",), VIEW),
        ("marketing", ("banner", "collection", "collectionitem", "homeblock", "trustitem"), CRUD),
        ("core", ("staticpage", "footerlink"), CRUD),
    ],
    "فروش": [
        ("orders", ("order",), VIEW),
        ("payments", ("payment",), VIEW),
        ("catalog", ("product", "variant", "stockmovement"), VIEW),
        ("engagement", ("stocksubscription",), VIEW),
        ("accounts", ("user",), VIEW),
    ],
    "نظرها": [("engagement", ("review",), ("view", "change"))],
}
EXTRA = {
    "محتوا": [("catalog", "adjust_stock")],
    "فروش": [("orders", "manage_order_status"), ("catalog", "adjust_stock")],
}


class Command(BaseCommand):
    help = "Create or refresh the staff permission groups."

    def handle(self, *args, **options):
        for name, rules in GROUPS.items():
            group, _ = Group.objects.get_or_create(name=name)
            perms = [
                Permission.objects.get(content_type__app_label=app, codename=f"{action}_{model}")
                for app, models, actions in rules
                for model in models
                for action in actions
            ]
            perms += [
                Permission.objects.get(content_type__app_label=app, codename=code) for app, code in EXTRA.get(name, [])
            ]
            group.permissions.set(perms)
            self.stdout.write(f"{name}: {len(perms)} permission(s)")
