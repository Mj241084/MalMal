import pytest
from django.urls import reverse

from apps.accounts.forms import AddressForm, MobileForm, ProfileForm
from apps.accounts.models import Address
from apps.core.testing import find_ascii_digits
from apps.core.widgets import FaDigitsInput, FaTextarea, FaTextInput

pytestmark = pytest.mark.django_db


def _assert_clean(response):
    text, inputs = find_ascii_digits(response.content.decode())
    assert not text, f"ASCII digits shown to the user: {text}"
    assert not inputs, f"digit inputs rendered with ASCII values: {inputs}"


def test_account_pages_show_persian_digits(client, user, other_user, province, city):
    user.national_code = "0012345679"
    user.save()
    Address.objects.create(
        user=user,
        recipient_name="مریم",
        recipient_mobile="09121234567",
        province=province,
        city=city,
        address_text="خیابان 12 پلاک 5",
        plate="12",
        unit="3",
        postal_code="1234567890",
        is_default=True,
    )
    client.force_login(user)
    for name in ("core:home", "accounts:profile", "accounts:addresses", "accounts:address_create"):
        _assert_clean(client.get(reverse(name)))

    client.force_login(other_user)  # no name: the header shows the mobile number
    _assert_clean(client.get(reverse("core:home")))


def test_login_and_code_step_show_persian_digits(client, fixed_otp_code):
    _assert_clean(client.get(reverse("accounts:login")))
    response = client.post(reverse("accounts:otp_request"), {"mobile": "09121234567"}, HTTP_HX_REQUEST="true")
    _assert_clean(response)


def test_persian_input_is_stored_as_ascii(client, user, province, city):
    client.force_login(user)
    client.post(
        reverse("accounts:address_create"),
        {
            "recipient_name": "مریم",
            "recipient_mobile": "۰۹۱۲۱۲۳۴۵۶۷",
            "province": province.pk,
            "city": city.pk,
            "address_text": "خیابان",
            "plate": "۱۲",
            "unit": "۳",
            "postal_code": "۱۲۳۴۵۶۷۸۹۰",
        },
    )
    address = Address.objects.get(user=user)
    assert (address.recipient_mobile, address.plate, address.unit, address.postal_code) == (
        "09121234567",
        "12",
        "3",
        "1234567890",
    )


def test_widgets_render_persian_digits_and_preserve_latin_tokens():
    rendered_mobile = FaDigitsInput().render("mobile", "09121234567")
    assert 'value="۰۹۱۲۱۲۳۴۵۶۷"' in rendered_mobile

    rendered_text = FaTextInput().render("title", "مدل WM-1234 شماره 12")
    assert 'value="مدل WM-1234 شماره ۱۲"' in rendered_text

    rendered_textarea = FaTextarea().render("address_text", "پلاک 12 کد WM-1234")
    assert "پلاک ۱۲ کد WM-1234" in rendered_textarea


def test_forms_normalize_persian_digits_to_ascii(user, province, city):
    mobile_form = MobileForm(data={"mobile": "۰۹۱۲۱۲۳۴۵۶۷"})
    assert mobile_form.is_valid(), mobile_form.errors
    assert mobile_form.cleaned_data["mobile"] == "09121234567"

    profile_form = ProfileForm(
        data={
            "first_name": "مریم",
            "last_name": "احمدی",
            "national_code": "۰۰۱۲۳۴۵۶۷۹",
            "national_code_confirm": "on",
            "email": "",
        },
        instance=user,
    )
    assert profile_form.is_valid(), profile_form.errors
    saved_user = profile_form.save()
    assert saved_user.national_code == "0012345679"

    address_form = AddressForm(
        data={
            "title": "خانه ۱۲",
            "recipient_name": "مریم",
            "recipient_mobile": "۰۹۱۲۱۲۳۴۵۶۷",
            "province": str(province.pk),
            "city": str(city.pk),
            "address_text": "خیابان ۱۲ پلاک ۵",
            "plate": "۱۲",
            "unit": "۳",
            "postal_code": "۱۲۳۴۵۶۷۸۹۰",
        },
        user=user,
    )
    assert address_form.is_valid(), address_form.errors
    assert address_form.cleaned_data["recipient_mobile"] == "09121234567"
    assert address_form.cleaned_data["postal_code"] == "1234567890"
    assert address_form.cleaned_data["plate"] == "12"
    assert address_form.cleaned_data["unit"] == "3"
    saved_address = address_form.save(commit=False)
    saved_address.user = user
    saved_address.save()
    saved_address.refresh_from_db()
    assert (
        saved_address.recipient_mobile,
        saved_address.postal_code,
        saved_address.plate,
        saved_address.unit,
    ) == ("09121234567", "1234567890", "12", "3")
