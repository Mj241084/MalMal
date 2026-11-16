from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.orders.models import ShippingMethod
from apps.payments.models import PaymentGateway

pytestmark = pytest.mark.django_db

READY = {
    "DEBUG": False,
    "SECRET_KEY": "x" * 60,
    "ALLOWED_HOSTS": ["malmal.ir"],
    "SITE_URL": "https://malmal.ir",
    "ADMIN_URL": "panel-9f3a/",
    "SESSION_COOKIE_SECURE": True,
    "CSRF_COOKIE_SECURE": True,
    "ZARINPAL_SANDBOX": False,
    "ZARINPAL_MERCHANT_ID": "00000000-0000-4000-8000-000000000001",
    "SMS_BACKEND": "smsir",
    "SMSIR_API_KEY": "key",
    "SMSIR_TEMPLATE_ID_OTP": "100",
}


@pytest.fixture
def ready(settings, city):
    for name, value in READY.items():
        setattr(settings, name, value)
    ShippingMethod.objects.get_or_create(code="tipax", defaults={"title": "تیپاکس"})
    PaymentGateway.objects.get_or_create(code="zarinpal", defaults={"title": "زرین‌پال"})
    PaymentGateway.objects.filter(code="zarinpal").update(is_active=True)


def test_a_ready_setup_passes_and_warnings_only_fail_in_strict(ready):
    out = StringIO()

    call_command("check_launch", stdout=out)  # warnings do not fail the gate
    assert "هشدار" in out.getvalue()
    with pytest.raises(CommandError):
        call_command("check_launch", "--strict", stdout=StringIO())


@pytest.mark.parametrize(
    ("name", "bad"),
    [
        ("DEBUG", True),
        ("ZARINPAL_SANDBOX", True),
        ("SMS_BACKEND", "console"),
        ("ADMIN_URL", "admin/"),
        ("SITE_URL", "http://localhost:8000"),
        ("SESSION_COOKIE_SECURE", False),
    ],
)
def test_each_unsafe_setting_blocks_launch(ready, settings, name, bad):
    setattr(settings, name, bad)

    with pytest.raises(CommandError):
        call_command("check_launch", stdout=StringIO())
