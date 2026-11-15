"""Address book behavior: default invariant, soft delete, ownership, and form rules."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import Address

pytestmark = pytest.mark.django_db

MOBILE = "09121234567"


def _address_data(province, city, **overrides) -> dict:
    data = {
        "title": "خانه",
        "recipient_name": "مریم احمدی",
        "recipient_mobile": MOBILE,
        "province": str(province.pk),
        "city": str(city.pk),
        "address_text": "خیابان ولیعصر، کوچه‌ی دوم",
        "plate": "12",
        "unit": "3",
        "postal_code": "1234567890",
    }
    data.update(overrides)
    return data


def _create_address(client, province, city, htmx=False, **overrides):
    extra = {"HTTP_HX_REQUEST": "true"} if htmx else {}
    return client.post(
        reverse("accounts:address_create"),
        _address_data(province, city, **overrides),
        **extra,
    )


def _active(user):
    return Address.objects.filter(user=user, deleted_at__isnull=True)


class TestAddressList:
    def test_requires_login(self, client):
        response = client.get(reverse("accounts:addresses"))

        assert response.status_code == 302
        assert response["Location"].startswith("/login/")

    def test_empty_state_hidden_when_form_has_validation_errors(self, client, user, province, city):
        client.force_login(user)

        for htmx in (False, True):
            response = _create_address(client, province, city, htmx=htmx, postal_code="123")
            body = response.content.decode()
            assert response.status_code == 200
            assert "هنوز آدرسی ثبت نکرده‌اید" not in body
            assert 'id="address-form"' in body


class TestAddressCreate:
    def test_first_address_is_always_default(self, client, user, province, city):
        client.force_login(user)

        response = _create_address(client, province, city)

        address = _active(user).get()
        assert response.status_code == 302
        assert address.is_default

    def test_new_default_unsets_the_previous_one(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city)

        _create_address(client, province, city, title="محل کار", is_default="on")

        defaults = _active(user).filter(is_default=True)
        assert defaults.count() == 1
        assert defaults.get().title == "محل کار"

    def test_non_default_address_keeps_the_existing_default(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city)

        _create_address(client, province, city, title="محل کار")

        defaults = _active(user).filter(is_default=True)
        assert defaults.count() == 1
        assert defaults.get().title == "خانه"

    def test_postal_code_and_mobile_are_normalized(self, client, user, province, city):
        client.force_login(user)

        _create_address(
            client,
            province,
            city,
            postal_code="۱۲۳۴۵۶۷۸۹۰",
            recipient_mobile="+98 912 123 4567",
        )

        address = _active(user).get()
        assert address.postal_code == "1234567890"
        assert address.recipient_mobile == MOBILE

    def test_invalid_postal_code_is_rejected(self, client, user, province, city):
        client.force_login(user)

        response = _create_address(client, province, city, postal_code="123")

        assert response.status_code == 200
        assert "کدپستی باید دقیقاً ۱۰ رقم باشد" in response.content.decode()
        assert not _active(user).exists()

    def test_city_must_belong_to_the_province(self, client, user, province, other_city):
        client.force_login(user)

        response = _create_address(client, province, other_city)

        assert response.status_code == 200
        assert "شهر انتخاب‌شده متعلق به این استان نیست" in response.content.decode()
        assert not _active(user).exists()

    def test_invalid_province_input_returns_validation_error(self, client, user, city):
        client.force_login(user)
        data = _address_data(city.province, city)
        data["province"] = "abc"
        response = client.post(reverse("accounts:address_create"), data)
        assert response.status_code == 200
        assert not _active(user).exists()

    def test_coordinates_rounded_to_six_decimals(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city, lat="35.68921234", lng="51.38901234")
        address = _active(user).get()
        assert str(address.lat) == "35.689212"
        assert str(address.lng) == "51.389012"

    def test_incomplete_or_out_of_iran_coordinates_rejected(self, client, user, province, city):
        client.force_login(user)
        # Incomplete (only lat)
        resp1 = _create_address(client, province, city, lat="35.6892")
        assert resp1.status_code == 200
        assert "مختصات نقشه ناقص است" in resp1.content.decode()

        # Outside Iran
        resp2 = _create_address(client, province, city, lat="10.0", lng="10.0")
        assert resp2.status_code == 200
        assert "خارج از محدوده‌ی ایران است" in resp2.content.decode()

    def test_neshan_assets_only_rendered_when_key_set(self, client, user, settings):
        client.force_login(user)
        settings.NESHAN_MAP_KEY = ""
        resp = client.get(reverse("accounts:addresses"))
        assert "static.neshan.org" not in resp.content.decode()
        assert "data-neshan-picker" not in resp.content.decode()

        settings.NESHAN_MAP_KEY = "test-map-key"
        resp2 = client.get(reverse("accounts:addresses"))
        assert "static.neshan.org" in resp2.content.decode()

        form_resp = client.get(reverse("accounts:address_create"), HTTP_HX_REQUEST="true")
        assert "data-neshan-picker" in form_resp.content.decode()


class TestAddressEdit:
    def test_default_survives_unchecking_the_box(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city)
        address = _active(user).get()

        response = client.post(
            reverse("accounts:address_edit", args=[address.pk]),
            _address_data(province, city, title="خانه‌ی جدید"),
        )

        address.refresh_from_db()
        assert response.status_code == 302
        assert address.is_default
        assert _active(user).filter(is_default=True).count() == 1

    def test_marking_another_address_default_unsets_the_first(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city)
        _create_address(client, province, city, title="محل کار")
        second = _active(user).get(title="محل کار")

        client.post(
            reverse("accounts:address_edit", args=[second.pk]),
            _address_data(province, city, title="محل کار", is_default="on"),
        )

        second.refresh_from_db()
        assert second.is_default
        assert _active(user).filter(is_default=True).count() == 1

    def test_editing_second_default_without_checkbox_keeps_it_default(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city, title="اول")
        _create_address(client, province, city, title="دوم", is_default="on")
        first = _active(user).get(title="اول")
        second = _active(user).get(title="دوم")
        assert second.is_default and not first.is_default

        response = client.post(
            reverse("accounts:address_edit", args=[second.pk]),
            _address_data(province, city, title="دوم ویرایش‌شده"),
        )

        first.refresh_from_db()
        second.refresh_from_db()
        assert response.status_code == 302
        assert second.is_default
        assert not first.is_default

    def test_other_users_address_is_not_found(self, client, user, other_user, province, city):
        address = Address.objects.create(
            user=other_user,
            recipient_name="دیگری",
            recipient_mobile=MOBILE,
            province=province,
            city=city,
            address_text="آدرس",
            plate="1",
            postal_code="1234567890",
        )
        client.force_login(user)

        response = client.get(reverse("accounts:address_edit", args=[address.pk]))

        assert response.status_code == 404

    def test_soft_deleted_address_is_not_found(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city)
        address = _active(user).get()
        client.post(reverse("accounts:address_delete", args=[address.pk]))

        response = client.get(reverse("accounts:address_edit", args=[address.pk]))

        assert response.status_code == 404


class TestAddressDelete:
    def test_delete_is_soft_and_promotes_the_earliest_address(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city)
        _create_address(client, province, city, title="محل کار")
        first = _active(user).get(title="خانه")

        client.post(reverse("accounts:address_delete", args=[first.pk]))

        deleted = Address.objects.get(pk=first.pk)
        replacement = _active(user).get()
        assert deleted.deleted_at is not None
        assert not deleted.is_default
        assert replacement.title == "محل کار"
        assert replacement.is_default

    def test_deleting_the_last_address_leaves_none(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city)
        address = _active(user).get()

        client.post(reverse("accounts:address_delete", args=[address.pk]))

        assert not _active(user).exists()

    def test_htmx_delete_returns_the_updated_section(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city)
        address = _active(user).get()

        response = client.post(reverse("accounts:address_delete", args=[address.pk]), HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        assert "هنوز آدرسی ثبت نکرده‌اید" in response.content.decode()


class TestAddressSetDefault:
    def test_switches_the_default(self, client, user, province, city):
        client.force_login(user)
        _create_address(client, province, city)
        _create_address(client, province, city, title="محل کار")
        second = _active(user).get(title="محل کار")

        client.post(reverse("accounts:address_set_default", args=[second.pk]))

        second.refresh_from_db()
        assert second.is_default
        assert _active(user).filter(is_default=True).count() == 1
