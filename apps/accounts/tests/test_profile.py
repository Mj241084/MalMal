"""Profile behavior: national-code lock (D20), D07 no-overwrite, and admin rules."""

from __future__ import annotations

import pytest
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

MOBILE = "09121234567"
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
VALID_CODE = "0012345679"
OTHER_VALID_CODE = "1234567891"


def _profile_data(**overrides):
    data = {
        "first_name": "مریم",
        "last_name": "احمدی",
        "national_code": "",
        "email": "",
    }
    data.update(overrides)
    return data


class TestProfilePage:
    def test_get_shows_the_locked_national_code(self, client, user):
        user.national_code = VALID_CODE
        user.save()
        client.force_login(user)

        response = client.get(reverse("accounts:profile"))

        body = response.content.decode()
        assert response.status_code == 200
        assert VALID_CODE.translate(FA_DIGITS) in body
        assert MOBILE.translate(FA_DIGITS) in body
        assert "readonly" in body
        assert "bg-base-300" in body
        assert "برای تغییر با پشتیبانی تماس بگیرید" in body
        assert 'name="national_code" disabled' not in body

    def test_duplicate_email_registration_returns_persian_error(self, client, user):
        User.objects.create_user("09129999999", email="maryam@example.com")
        client.force_login(user)

        response = client.post(
            reverse("accounts:profile"),
            _profile_data(email="maryam@example.com"),
        )

        assert response.status_code == 200
        body = response.content.decode()
        assert "این ایمیل قبلاً برای حساب دیگری ثبت شده است" in body

    def test_deactivating_user_revokes_active_session(self, client, user):
        client.force_login(user)
        assert client.get(reverse("accounts:profile")).status_code == 200

        user.is_active = False
        user.save(update_fields=["is_active"])

        response = client.get(reverse("accounts:profile"))
        assert response.status_code == 302
        assert response["Location"].startswith("/login/")

    def test_tampered_post_cannot_change_mobile(self, client, user):
        client.force_login(user)
        response = client.post(
            reverse("accounts:profile"),
            _profile_data(mobile="09129998877"),
        )
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.mobile == MOBILE

    def test_first_national_code_requires_confirmation(self, client, user):
        client.force_login(user)

        response = client.post(reverse("accounts:profile"), _profile_data(national_code=VALID_CODE))

        user.refresh_from_db()
        assert response.status_code == 200
        assert "تایید قیدشده" in response.content.decode()
        assert user.national_code == ""

    def test_first_national_code_accepts_persian_digits_with_confirmation(self, client, user):
        client.force_login(user)
        persian_code = VALID_CODE.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

        response = client.post(
            reverse("accounts:profile"),
            _profile_data(national_code=persian_code, national_code_confirm="on"),
        )

        user.refresh_from_db()
        assert response.status_code == 302
        assert user.national_code == VALID_CODE

    @pytest.mark.parametrize("bad_code", ["0012345678", "1111111111", "123"])
    def test_invalid_national_codes_are_rejected(self, client, user, bad_code):
        client.force_login(user)

        response = client.post(
            reverse("accounts:profile"),
            _profile_data(national_code=bad_code, national_code_confirm="on"),
        )

        user.refresh_from_db()
        assert response.status_code == 200
        assert "معتبر نیست" in response.content.decode() or "۱۰ رقم" in response.content.decode()
        assert user.national_code == ""

    def test_filled_national_code_is_never_overwritten_by_the_form(self, client, user):
        user.national_code = VALID_CODE
        user.save()
        client.force_login(user)

        response = client.post(
            reverse("accounts:profile"),
            _profile_data(
                first_name="زهرا",
                national_code=OTHER_VALID_CODE,
                national_code_confirm="on",
            ),
        )

        user.refresh_from_db()
        assert response.status_code == 302
        assert user.national_code == VALID_CODE
        assert user.first_name == "زهرا"
        assert user.mobile == MOBILE

    def test_names_are_normalized_before_saving(self, client, user):
        client.force_login(user)

        client.post(
            reverse("accounts:profile"),
            _profile_data(first_name=" كيان ", last_name="احمدي"),
        )

        user.refresh_from_db()
        assert user.first_name == "کیان"
        assert user.last_name == "احمدی"


class TestNationalCodeModelLock:
    def test_locked_value_cannot_be_changed_by_direct_save(self, user):
        user.national_code = VALID_CODE
        user.save()

        user.national_code = OTHER_VALID_CODE
        with pytest.raises(ValidationError):
            user.save()

        user.refresh_from_db()
        assert user.national_code == VALID_CODE

    def test_explicit_permission_hook_allows_the_change(self, user):
        user.national_code = VALID_CODE
        user.save()

        user.national_code = OTHER_VALID_CODE
        user.allow_national_code_change()
        user.save()

        user.refresh_from_db()
        assert user.national_code == OTHER_VALID_CODE


class TestAdminNationalCode:
    def _admin_data(self, user, national_code) -> dict:
        return {
            "mobile": user.mobile,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "national_code": national_code,
            "email": user.email,
            "is_active": "on",
        }

    def test_superuser_change_is_saved_and_logged(self, client, user):
        superuser = User.objects.create_superuser("09120000000", password="secret")
        user.national_code = VALID_CODE
        user.save()
        client.force_login(superuser)
        url = reverse("admin:accounts_user_change", args=[user.pk])

        response = client.post(url, self._admin_data(user, OTHER_VALID_CODE))

        user.refresh_from_db()
        assert response.status_code == 302
        assert user.national_code == OTHER_VALID_CODE
        # Django's own change entry plus the explicit audit entry for the code change.
        entries = LogEntry.objects.filter(user=superuser, object_id=str(user.pk))
        assert any("National code changed" in entry.change_message for entry in entries)

    def test_staff_without_permission_cannot_change_it(self, client, user):
        user.national_code = VALID_CODE
        user.save()
        staff = User.objects.create_user("09120000001", password="secret", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename="change_user", content_type__app_label="accounts"))
        client.force_login(staff)
        url = reverse("admin:accounts_user_change", args=[user.pk])

        response = client.post(url, self._admin_data(user, OTHER_VALID_CODE))

        user.refresh_from_db()
        assert response.status_code == 302
        assert user.national_code == VALID_CODE
        assert not LogEntry.objects.filter(user=staff, change_message__contains="National code changed").exists()
