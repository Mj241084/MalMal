"""P14 business rules: staff protection, the national-code lock, settings guards, check_launch compatibility."""

from __future__ import annotations

import time

import pytest
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts import services
from apps.accounts.models import User
from apps.core.management.commands import check_launch

pytestmark = pytest.mark.django_db
STRONG = "Str0ng-pass-92"


def panel_login(client, user):
    client.force_login(user)
    session = client.session
    session["panel_login_at"] = int(time.time())
    session.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
    return client


def test_staff_rules_protect_customers_and_the_last_superuser(buyer):
    with pytest.raises(services.StaffError) as exc:
        services.create_staff_user(buyer.mobile, STRONG, [], allow_existing=False)
    assert exc.value.code == "customer"

    member = services.create_staff_user("09120000007", STRONG, [], allow_existing=False)
    assert member.is_staff and not member.is_superuser

    boss = User.objects.create_superuser("09120000009", STRONG)
    with pytest.raises(services.StaffError) as exc:
        services.set_staff_active(boss, by=boss, active=False)
    assert exc.value.code == "self"
    with pytest.raises(services.StaffError) as exc:
        services.set_staff_active(boss, by=member, active=False)
    assert exc.value.code == "last_superuser"


def test_staff_password_reset_ends_their_sessions():
    member = services.create_staff_user("09120000007", STRONG, [], allow_existing=False)
    before = member.session_version
    services.reset_staff_password(member, "An0ther-pass-77")
    member.refresh_from_db()
    assert member.session_version == before + 1 and member.check_password("An0ther-pass-77")


def test_national_code_change_needs_permission_a_reason_and_leaves_an_audit_entry(client, buyer):
    staff = User.objects.create_user("09120000006", is_staff=True)
    staff.user_permissions.add(Permission.objects.get(content_type__app_label="accounts", codename="view_user"))
    panel_login(client, staff)
    url = reverse("panel:customer_national_code", args=[buyer.pk])
    data = {"code": "0499370899", "note": "اصلاح به درخواست مشتری", "confirm": "1"}

    assert client.post(url, data).status_code == 403  # view_user alone does not open the D20 lock
    buyer.refresh_from_db()
    assert buyer.national_code == "0012345679"

    staff.user_permissions.add(Permission.objects.get(codename="change_national_code"))
    assert client.post(url, {**data, "note": ""}).status_code == 302  # no reason: refused
    buyer.refresh_from_db()
    assert buyer.national_code == "0012345679"

    assert client.post(url, data).status_code == 302
    buyer.refresh_from_db()
    assert buyer.national_code == "0499370899"
    assert LogEntry.objects.filter(object_id=str(buyer.pk), change_message__contains="کد ملی").exists()


def test_last_active_shipping_method_cannot_be_deactivated(client, checkout_env):
    boss = User.objects.create_superuser("09120000005", STRONG)
    panel_login(client, boss)
    response = client.post(
        reverse("panel:shipping_edit", args=[checkout_env.pk]), {"title": checkout_env.title, "sort": "0"}
    )
    checkout_env.refresh_from_db()
    assert response.status_code == 200 and checkout_env.is_active  # form re-rendered with the error


def test_collect_detailed_keeps_the_collect_output():
    assert [(level, text) for level, text, _ in check_launch.collect_detailed()] == list(check_launch.collect())
