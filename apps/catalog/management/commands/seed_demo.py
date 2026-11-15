"""Seed an obviously-fake demo catalog for development (phase P1, item A7).

Every object created here is marked ``is_demo=True`` and can be removed again with
``manage.py seed_demo --clear``. The command refuses to run with ``DEBUG=False``
unless ``--force`` is passed, so demo data can never leak into production.
"""

from __future__ import annotations

import io

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageDraw

from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductSpecValue,
    SpecAttribute,
    StockMovement,
    Variant,
)
from apps.marketing import demo as marketing_demo

BRANDS = [
    ("اسنوا", "Snowa", "اسنوا، Snowa"),
    ("بوش", "Bosch", "بوش، Bosch"),
    ("ال‌جی", "LG", "ال جی، LG، الجی"),
    ("سامسونگ", "Samsung", "سامسونگ، Samsung"),
    ("فیلیپس", "Philips", "فیلیپس، Philips"),
    ("تفال", "Tefal", "تفال، Tefal"),
]

TREE = [
    (
        "یخچال و فریزر",
        ["ساید بای ساید", "دوقلو", "کمبی"],
    ),
    (
        "ماشین لباسشویی",
        ["اتوماتیک", "خشک‌کن دار"],
    ),
    (
        "ماشین ظرفشویی",
        ["مبله", "رومیزی"],
    ),
    (
        "لوازم آشپزخانه",
        ["چای‌ساز", "قهوه‌ساز", "غذاساز"],
    ),
]

MODELS = {
    "ساید بای ساید": ["SN8-2035GW", "GR-J310", "RS64R5301"],
    "دوقلو": ["ES-18", "RT-500"],
    "کمبی": ["C-300", "HM-420"],
    "اتوماتیک": ["WGA244X0IR", "F4WV910P2"],
    "خشک‌کن دار": ["WD-90", "DV-80"],
    "مبله": ["SMS46MI01", "DF-14"],
    "رومیزی": ["AD-6", "TS-5"],
    "چای‌ساز": ["BJ551B", "TK-17"],
    "قهوه‌ساز": ["EA-81", "CE-5"],
    "غذاساز": ["FP-51", "HR-77"],
}

COLORS = ["سفید", "نقره‌ای", "مشکی"]
WARRANTIES = ["۱۸ ماه گارانتی شرکتی", "۲۴ ماه گارانتی رسمی", "۱۲ ماه گارانتی فروشگاه"]


class Command(BaseCommand):
    help = "Create (or clear) an obviously fake demo catalog. Development only."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Delete all demo rows and stop.")
        parser.add_argument("--products", type=int, default=12, help="How many demo products to create.")
        parser.add_argument("--force", action="store_true", help="Run even when DEBUG is False.")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("seed_demo only runs with DEBUG=True (use --force to override).")

        if options["clear"]:
            self._clear()
            return

        with transaction.atomic():
            brands = self._brands()
            categories = self._categories()
            attributes = self._attributes(categories)
            created = self._products(brands, categories, attributes, options["products"])
            marketing_demo.seed_marketing()

        self.stdout.write(self.style.SUCCESS(f"{created} demo product(s) created. Remove with --clear."))

    # --- builders ----------------------------------------------------------

    def _clear(self) -> None:
        marketing_demo.clear_marketing()
        product_count = Product.objects.filter(is_demo=True).count()
        # StockMovement.variant is PROTECT: a ledger row from an earlier checkout on demo stock
        # would otherwise keep the demo product alive. Dev-only rows, so they go with the rest.
        StockMovement.objects.filter(variant__is_demo=True).delete()
        Product.objects.filter(is_demo=True).delete()
        Variant.objects.filter(is_demo=True).delete()
        # Category.parent is PROTECT: remove leaves before their parents.
        for category in Category.objects.filter(is_demo=True).order_by("-depth"):
            category.delete()
        Brand.objects.filter(is_demo=True).delete()
        self.stdout.write(self.style.SUCCESS(f"Demo data removed ({product_count} products)."))

    def _brands(self) -> list[Brand]:
        brands = []
        for name_fa, name_en, aliases in BRANDS:
            brand, _ = Brand.objects.get_or_create(
                name_fa=name_fa,
                defaults={"name_en": name_en, "aliases": aliases, "is_demo": True},
            )
            brands.append(brand)
        return brands

    def _categories(self) -> dict[str, Category]:
        by_name: dict[str, Category] = {}
        for order, (root_name, children) in enumerate(TREE):
            root, _ = Category.objects.get_or_create(
                name=root_name,
                parent=None,
                defaults={
                    "is_demo": True,
                    "is_featured": order < 4,
                    "featured_order": order,
                    "menu_order": order,
                    "description": f"همه‌ی محصولات {root_name}",
                },
            )
            by_name[root_name] = root
            for child_order, child_name in enumerate(children):
                child, _ = Category.objects.get_or_create(
                    name=child_name,
                    parent=root,
                    defaults={"is_demo": True, "menu_order": child_order},
                )
                by_name[child_name] = child
        return by_name

    def _attributes(self, categories: dict[str, Category]) -> list[SpecAttribute]:
        attributes = []
        for category_name in ("ساید بای ساید", "اتوماتیک", "چای‌ساز"):
            category = categories[category_name]
            for name, unit, filterable, order in (
                ("ظرفیت", "لیتر", True, 0),
                ("رنگ", "", True, 1),
                ("مصرف انرژی", "کیلووات ساعت", False, 2),
            ):
                attribute, _ = SpecAttribute.objects.get_or_create(
                    category=category,
                    name=name,
                    defaults={"unit": unit, "is_filterable": filterable, "sort": order},
                )
                attributes.append(attribute)
        return attributes

    def _placeholder_image(self, title: str, index: int) -> ContentFile:
        """A flat, obviously synthetic tile with the model code printed on it."""
        palette = [(238, 233, 223), (247, 244, 238), (239, 233, 223), (253, 251, 247)]
        image = Image.new("RGB", (800, 800), palette[index % len(palette)])
        draw = ImageDraw.Draw(image)
        draw.rectangle([40, 40, 760, 760], outline=(190, 182, 170), width=2)
        draw.rectangle([300, 300, 500, 500], outline=(190, 182, 170), width=2)
        draw.text((60, 720), f"DEMO {index + 1}", fill=(120, 112, 100))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return ContentFile(buffer.getvalue(), name=f"demo-{abs(hash(title)) % 10**8}-{index}.png")

    def _products(
        self,
        brands: list[Brand],
        categories: dict[str, Category],
        attributes: list[SpecAttribute],
        count: int,
    ) -> int:
        leaf_names = [name for name in MODELS]
        created = 0
        for index in range(count):
            leaf_name = leaf_names[index % len(leaf_names)]
            category = categories[leaf_name]
            brand = brands[index % len(brands)]
            model = MODELS[leaf_name][index % len(MODELS[leaf_name])]
            title = f"{category.name} {brand.name_fa} مدل {model}"

            product = Product.objects.create(
                title=title,
                brand=brand,
                category=category,
                status=Product.STATUS_ACTIVE,
                short_description=f"محصول نمونه برای توسعه — {title}",
                description="<p>این توضیح نمونه است و فقط برای آزمون رابط کاربری ساخته شده است.</p>",
                warranty_text=WARRANTIES[index % len(WARRANTIES)],
                is_demo=True,
            )

            base_price = 8_000_000 + (index * 1_350_000)
            for variant_index in range(2):
                price = base_price + variant_index * 500_000
                compare = price + 900_000 if index % 3 == 0 else None
                Variant.objects.create(
                    product=product,
                    sku=f"DEMO-{product.pk}-{variant_index + 1}",
                    title=f"{COLORS[variant_index % len(COLORS)]}",
                    options={"color": COLORS[variant_index % len(COLORS)], "model": model},
                    price=price,
                    compare_at_price=compare,
                    stock=0 if index % 7 == 6 and variant_index == 0 else 4 + variant_index * 6,
                    # D29: one demo variant carries a per-order cap below its stock.
                    max_per_order=2 if index % 4 == 1 and variant_index == 0 else None,
                    weight_g=1200 + index * 50,
                    sort=variant_index,
                    is_demo=True,
                )

            image = ProductImage(
                product=product,
                alt=title,
                sort=0,
            )
            image.image.save(f"demo-{product.pk}.png", self._placeholder_image(title, index), save=True)
            product.main_image = image
            product.save(update_fields=["main_image", "updated_at"])

            for attribute in attributes:
                if attribute.category_id != category.pk:
                    continue
                if attribute.name == "ظرفیت":
                    ProductSpecValue.objects.create(
                        product=product, attribute=attribute, value_text=f"{6 + index % 5} لیتر"
                    )
                elif attribute.name == "رنگ":
                    ProductSpecValue.objects.create(product=product, attribute=attribute, value_text="سفید")
                else:
                    ProductSpecValue.objects.create(product=product, attribute=attribute, value_text=f"{index % 4 + 1}")

            created += 1
        return created
