"""Login flow behavior: request, verify, next safety, and session revocation (docs/02 §4)."""

from __future__ import annotations

import json
import re
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts import ratelimit
from apps.accounts.models import OTPChallenge, User
from apps.cart.models import CartItem
from apps.core.models import StaticPage
from apps.notifications.models import SmsLog

pytestmark = pytest.mark.django_db

MOBILE = "09121234567"
OTHER_MOBILE = "09127654321"
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _normalize(html: str) -> str:
    html = re.sub(r'name="csrfmiddlewaretoken" value="[^"]+"', "", html)
    html = re.sub(r'data-seconds="[^"]*"', 'data-seconds="x"', html)
    for mobile in (MOBILE, OTHER_MOBILE):
        html = html.replace(mobile.translate(FA_DIGITS), "MOBILE")
        html = html.replace(mobile, "MOBILE")
    return html


def _expire(mobile: str) -> None:
    OTPChallenge.objects.filter(mobile=mobile).update(expires_at=timezone.now() - timedelta(seconds=1))


def _request_code(client, mobile=MOBILE, next_url="", htmx=True):
    data = {"mobile": mobile}
    if next_url:
        data["next"] = next_url
    extra = {"HTTP_HX_REQUEST": "true"} if htmx else {}
    return client.post(reverse("accounts:otp_request"), data, **extra)


def _verify(client, code, mobile=MOBILE, next_url="", htmx=True):
    data = {"mobile": mobile, "code": code}
    if next_url:
        data["next"] = next_url
    extra = {"HTTP_HX_REQUEST": "true"} if htmx else {}
    return client.post(reverse("accounts:otp_verify"), data, **extra)


class TestRequestCode:
    def test_htmx_response_is_the_code_step(self, client, fixed_otp_code):
        response = _request_code(client)

        assert response.status_code == 200
        assert "partials/_otp_code_step.html" in [t.name for t in response.templates]
        body = response.content.decode()
        assert 'autocomplete="one-time-code"' in body
        assert 'inputmode="numeric"' in body
        assert "data-otp-timer" in body
        assert SmsLog.objects.count() == 1

    def test_full_page_fallback_renders_the_code_step(self, client, fixed_otp_code):
        response = _request_code(client, htmx=False)

        assert response.status_code == 200
        body = response.content.decode()
        assert "<html" in body
        assert "کد تایید را وارد کنید" in body

    def test_known_and_unknown_mobiles_get_identical_responses(self, client, fixed_otp_code):
        User.objects.create_user(MOBILE)

        known = _request_code(client, MOBILE).content.decode()
        unknown = _request_code(client, OTHER_MOBILE).content.decode()

        assert _normalize(known) == _normalize(unknown)
        assert SmsLog.objects.count() == 2

    def test_rate_limited_responses_do_not_reveal_the_account(self, client, fixed_otp_code, monkeypatch):
        monkeypatch.setattr(ratelimit, "MOBILE_HOURLY_LIMIT", 1)
        User.objects.create_user(MOBILE)

        _request_code(client, MOBILE)
        _expire(MOBILE)
        known = _request_code(client, MOBILE).content.decode()

        _request_code(client, OTHER_MOBILE)
        _expire(OTHER_MOBILE)
        unknown = _request_code(client, OTHER_MOBILE).content.decode()

        assert "تعداد درخواست‌ها زیاد شد" in known
        assert _normalize(known) == _normalize(unknown)

    def test_invalid_mobile_keeps_the_form_on_screen(self, client, fixed_otp_code):
        response = _request_code(client, "123")

        assert response.status_code == 200
        assert "partials/_login_flow.html" in [t.name for t in response.templates]
        assert not SmsLog.objects.exists()


class TestVerifyCode:
    def test_new_mobile_is_registered_and_logged_in(self, client, fixed_otp_code):
        _request_code(client, OTHER_MOBILE)

        response = _verify(client, fixed_otp_code, OTHER_MOBILE, htmx=False)

        user = User.objects.get(mobile=OTHER_MOBILE)
        assert response.status_code == 302
        assert response["Location"] == reverse("core:home")
        assert client.session["_auth_user_id"] == str(user.pk)

    def test_existing_user_is_reused(self, client, user, fixed_otp_code):
        _request_code(client)

        _verify(client, fixed_otp_code)

        assert User.objects.filter(mobile=MOBILE).count() == 1
        assert client.session["_auth_user_id"] == str(user.pk)

    def test_htmx_success_returns_client_redirect_and_event(self, client, fixed_otp_code):
        _request_code(client)

        response = _verify(client, fixed_otp_code)

        assert response.status_code == 200
        assert response["HX-Redirect"] == reverse("core:home")
        assert "auth:login" in response["HX-Trigger"]

    def test_internal_next_is_honored(self, client, fixed_otp_code):
        _request_code(client, next_url="/checkout/")

        response = _verify(client, fixed_otp_code, next_url="/checkout/", htmx=False)

        assert response["Location"] == "/checkout/"

    @pytest.mark.parametrize(
        "evil_next",
        ["https://evil.example", "//evil.example", "javascript:alert(1)"],
    )
    def test_external_next_is_rejected(self, client, fixed_otp_code, evil_next):
        _request_code(client, next_url=evil_next)

        response = _verify(client, fixed_otp_code, next_url=evil_next, htmx=False)

        assert response["Location"] == reverse("core:home")

    def test_wrong_code_reports_remaining_attempts(self, client, fixed_otp_code):
        _request_code(client)

        response = _verify(client, "9999")

        body = response.content.decode()
        assert "درست نیست" in body
        assert "۴ تلاش دیگر باقی مانده است" in body

    def test_five_wrong_codes_lock_the_mobile(self, client, fixed_otp_code):
        _request_code(client)

        for _ in range(4):
            _verify(client, "9999")
        response = _verify(client, "9999")

        assert "تعداد تلاش‌های ناموفق زیاد شد" in response.content.decode()
        assert not client.session.get("_auth_user_id")

    def test_expired_code_is_reported(self, client, fixed_otp_code):
        _request_code(client)
        _expire(MOBILE)

        response = _verify(client, fixed_otp_code)

        assert "کد منقضی شده است" in response.content.decode()

    def test_used_code_cannot_be_replayed(self, client, fixed_otp_code):
        _request_code(client)
        _verify(client, fixed_otp_code)

        replay = Client().post(
            reverse("accounts:otp_verify"),
            {"mobile": MOBILE, "code": fixed_otp_code},
            HTTP_HX_REQUEST="true",
        )

        assert "درست نیست" in replay.content.decode()

    def test_code_without_a_challenge_is_reported(self, client, fixed_otp_code):
        response = _verify(client, fixed_otp_code)

        assert "کد فعالی برای این شماره نیست" in response.content.decode()

    def test_staff_account_cannot_log_in_with_otp(self, client, fixed_otp_code):
        User.objects.create_user(MOBILE, password="secret", is_staff=True)
        _request_code(client)

        response = _verify(client, fixed_otp_code)

        assert response.status_code == 200
        assert "امکان ورود به این حساب در حال حاضر وجود ندارد" in response.content.decode()
        assert not client.session.get("_auth_user_id")
        assert not SmsLog.objects.exists()

    def test_inactive_account_cannot_log_in(self, client, fixed_otp_code):
        User.objects.create_user(MOBILE, is_active=False)
        _request_code(client)

        response = _verify(client, fixed_otp_code)

        assert "امکان ورود به این حساب در حال حاضر وجود ندارد" in response.content.decode()
        assert not client.session.get("_auth_user_id")

    def test_invalid_code_form_shows_error_and_preserves_timer(self, client, fixed_otp_code):
        _request_code(client)

        response = _verify(client, "12")
        body = response.content.decode()

        assert "کد تایید ۴ رقم است" in body
        assert 'data-seconds="0"' not in body
        match = re.search(r'data-seconds="(\d+)"', body)
        assert match and int(match.group(1)) > 0
        assert 'id="otp-resend"' in body
        assert "disabled" in body.split('id="otp-resend"')[1].split(">")[0]

    def test_next_is_preserved_on_change_mobile_button(self, client, fixed_otp_code):
        _request_code(client, next_url="/checkout/")
        response = _verify(client, "12", next_url="/checkout/")
        body = response.content.decode()

        assert reverse("accounts:otp_cancel") in body
        assert "تغییر شماره" in body

    def test_guest_cart_is_merged_before_the_redirect(self, client, fixed_otp_code, product):
        variant = product.variants.get()
        _request_code(client)

        client.post(
            reverse("accounts:otp_verify"),
            {
                "mobile": MOBILE,
                "code": fixed_otp_code,
                "guest_cart": json.dumps([{"v": variant.pk, "q": 2}]),
            },
            HTTP_HX_REQUEST="true",
        )

        user = User.objects.get(mobile=MOBILE)
        assert list(CartItem.objects.filter(cart__user=user).values_list("variant_id", "qty")) == [(variant.pk, 2)]

    def test_csrf_is_required(self, fixed_otp_code):
        client = Client(enforce_csrf_checks=True)

        response = client.post(reverse("accounts:otp_request"), {"mobile": MOBILE})

        assert response.status_code == 403
        assert not SmsLog.objects.exists()


class TestSessions:
    def test_login_page_redirects_authenticated_users(self, client, user):
        client.force_login(user)

        response = client.get(reverse("accounts:login"), {"next": "/checkout/"})

        assert response.status_code == 302
        assert response["Location"] == "/checkout/"

    def test_login_page_sanitizes_external_next_for_authenticated_users(self, client, user):
        client.force_login(user)

        response = client.get(reverse("accounts:login"), {"next": "https://evil.example"})

        assert response["Location"] == reverse("core:home")

    def test_modal_returns_204_when_authenticated(self, client, user):
        client.force_login(user)

        assert client.get(reverse("accounts:otp_modal")).status_code == 204

    def test_logout(self, client, user):
        client.force_login(user)

        response = client.post(reverse("accounts:logout"))

        assert response.status_code == 302
        assert not client.session.get("_auth_user_id")

    def test_logout_all_revokes_every_other_session(self, user):
        first, second = Client(), Client()
        first.force_login(user)
        second.force_login(user)
        profile_url = reverse("accounts:profile")
        assert second.get(profile_url).status_code == 200

        first.post(reverse("accounts:logout_all"))

        user.refresh_from_db()
        assert user.session_version == 1
        assert second.get(profile_url).status_code == 302
        assert first.get(profile_url).status_code == 302

    def test_profile_requires_login(self, client):
        response = client.get(reverse("accounts:profile"))

        assert response.status_code == 302
        assert response["Location"].startswith("/login/")


class TestPendingStep:
    def test_modal_resumes_the_code_step_without_a_new_sms(self, client, fixed_otp_code):
        _request_code(client)
        body = client.get(reverse("accounts:otp_modal"), HTTP_HX_REQUEST="true").content.decode()
        assert "data-otp-length" in body and "کد قبلی هنوز معتبر است" in body
        assert SmsLog.objects.count() == 1

    def test_other_browsers_see_the_mobile_step(self, client, fixed_otp_code):
        _request_code(client)
        body = Client().get(reverse("accounts:otp_modal"), HTTP_HX_REQUEST="true").content.decode()
        assert "data-otp-length" not in body and 'name="mobile"' in body

    def test_cancel_forgets_the_challenge_but_keeps_next(self, client, fixed_otp_code):
        _request_code(client, next_url="/checkout/")
        response = client.post(reverse("accounts:otp_cancel"), HTTP_HX_REQUEST="true")
        assert 'value="/checkout/"' in response.content.decode()
        assert (
            "data-otp-length" not in client.get(reverse("accounts:otp_modal"), HTTP_HX_REQUEST="true").content.decode()
        )

    def test_terms_link_shown_only_when_active_terms_page_exists(self, client):
        body_without_terms = client.get(reverse("accounts:otp_modal"), HTTP_HX_REQUEST="true").content.decode()
        assert "قوانین و مقررات" not in body_without_terms

        StaticPage.objects.create(slug="terms", title="قوانین و مقررات", body="متن قوانین", is_active=True)
        body_with_terms = client.get(reverse("accounts:otp_modal"), HTTP_HX_REQUEST="true").content.decode()
        assert "قوانین و مقررات" in body_with_terms
        assert reverse("core:static_page", args=["terms"]) in body_with_terms
