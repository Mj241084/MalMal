from django.db import migrations


def seed(apps, schema_editor):
    ShippingMethod = apps.get_model("orders", "ShippingMethod")
    ShippingMethod.objects.get_or_create(
        code="tipax",
        defaults={
            "title": "ارسال با تیپاکس",
            "product_note": "ارسال با تیپاکس به سراسر کشور؛ کرایه هنگام تحویل به پیک پرداخت می‌شود.",
            "checkout_note": "کرایه‌ی ارسال هنگام تحویل بار به پیک تیپاکس پرداخت می‌شود و جزو مبلغ این پرداخت نیست.",
            "has_tracking": True,
            "payment_mode": "collect",
            # [VERIFY] Tipax heavy/bulky class tops out at 100 kg (docs/vendors/tipax §13.20)
            "max_weight_g": 100000,
            "sort": 0,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
