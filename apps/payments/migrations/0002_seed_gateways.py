from django.db import migrations


def seed(apps, schema_editor):
    Gateway = apps.get_model("payments", "PaymentGateway")
    # [VERIFY] limits: 100M Toman is code -41 in the vendor guide; the Rial minimum differs between pages (1,000 / 10,000 Rial).
    Gateway.objects.get_or_create(
        code="zarinpal",
        defaults={"title": "زرین‌پال", "sort": 0, "min_amount": 1000, "max_amount": 100_000_000},
    )
    # Hidden in production by the adapter itself (dev_only); the row only makes it selectable while DEBUG is on.
    Gateway.objects.get_or_create(code="fake", defaults={"title": "درگاه آزمایشی (فقط توسعه)", "sort": 99})


class Migration(migrations.Migration):
    dependencies = [("payments", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
