"""SMS adapter behavior (docs/05 §4): backend selection, cleaning, and logging."""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from urllib.error import HTTPError

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications import maintenance, sms
from apps.notifications.models import SmsLog

pytestmark = pytest.mark.django_db

MOBILE = "09121234567"


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _install_urlopen(monkeypatch, payload=None, error=None) -> list:
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append((request, timeout))
        if error is not None:
            raise error
        return _FakeResponse(payload)

    monkeypatch.setattr(sms, "urlopen", fake_urlopen)
    return calls


@pytest.fixture
def smsir(settings):
    settings.SMS_BACKEND = "smsir"
    settings.SMSIR_API_KEY = "test-api-key"
    settings.SMSIR_TEMPLATE_ID_OTP = "123456"
    return settings


class TestConsoleBackend:
    def test_writes_a_sent_log_without_network(self, settings, monkeypatch, caplog):
        settings.SMS_BACKEND = "console"
        calls = _install_urlopen(monkeypatch)

        with caplog.at_level(logging.INFO, logger="apps.notifications.sms"):
            log = sms.send_template("otp", MOBILE, {"code": "1234"})

        assert calls == []
        assert log.status == SmsLog.STATUS_SENT
        assert log.mobile == MOBILE
        assert "1234" in caplog.text
        assert SmsLog.objects.count() == 1

    def test_console_is_considered_configured_even_without_template_ids(self, settings):
        settings.SMS_BACKEND = "console"

        assert sms.template_is_configured("otp")


class TestSmsIrBackend:
    def test_request_shape_and_success_log(self, smsir, monkeypatch):
        calls = _install_urlopen(monkeypatch, payload={"status": 1, "data": {"messageId": 42}})

        log = sms.send_template("otp", "+98 912 123 4567", {"code": "1234"})

        request, timeout = calls[0]
        body = json.loads(request.data.decode("utf-8"))
        assert request.full_url == "https://api.sms.ir/v1/send/verify"
        assert request.get_method() == "POST"
        assert request.get_header("X-api-key") == "test-api-key"
        assert request.get_header("Content-type") == "application/json"
        assert timeout == 10
        assert body == {
            "mobile": MOBILE,
            "templateId": 123456,
            "parameters": [{"name": "code", "value": "1234"}],
        }
        assert log.status == SmsLog.STATUS_SENT
        assert log.provider_message_id == "42"
        assert log.mobile == MOBILE

    def test_parameter_names_and_values_are_cleaned(self, smsir, monkeypatch):
        calls = _install_urlopen(monkeypatch, payload={"status": 1, "data": {}})

        sms.send_template(
            "otp",
            MOBILE,
            {"#code#": "12\n34", "long": "x" * 40},
        )

        body = json.loads(calls[0][0].data.decode("utf-8"))
        assert body["parameters"] == [
            {"name": "code", "value": "12 34"},
            {"name": "long", "value": "x" * 25},
        ]

    def test_provider_error_status_is_logged_not_raised(self, smsir, monkeypatch):
        _install_urlopen(monkeypatch, payload={"status": 0, "message": "invalid params"})

        log = sms.send_template("otp", MOBILE, {"code": "1234"})

        assert log.status == SmsLog.STATUS_FAILED
        assert "status=0" in log.error
        assert "invalid params" in log.error

    def test_http_error_is_logged_not_raised(self, smsir, monkeypatch):
        _install_urlopen(monkeypatch, error=HTTPError("https://api.sms.ir", 500, "boom", {}, None))

        log = sms.send_template("otp", MOBILE, {"code": "1234"})

        assert log.status == SmsLog.STATUS_FAILED
        assert log.error == "HTTP 500"

    def test_http_error_with_json_body_logs_detail(self, smsir, monkeypatch):
        import io

        fp = io.BytesIO(json.dumps({"status": 113, "message": "قالب یافت نشد"}).encode("utf-8"))
        _install_urlopen(monkeypatch, error=HTTPError("https://api.sms.ir", 400, "Bad Request", {}, fp))

        log = sms.send_template("otp", MOBILE, {"code": "1234"})

        assert log.status == SmsLog.STATUS_FAILED
        assert "HTTP 400" in log.error
        assert "status=113" in log.error
        assert "قالب یافت نشد" in log.error

    def test_invalid_template_id_is_a_failure(self, settings, monkeypatch):
        settings.SMS_BACKEND = "smsir"
        settings.SMSIR_API_KEY = "test-api-key"
        settings.SMSIR_TEMPLATE_ID_OTP = "not-a-number"
        calls = _install_urlopen(monkeypatch, payload={"status": 1})

        log = sms.send_template("otp", MOBILE, {"code": "1234"})

        assert calls == []
        assert log.status == SmsLog.STATUS_FAILED
        assert "invalid template id" in log.error

    def test_missing_template_id_skips_without_network(self, settings, monkeypatch):
        settings.SMS_BACKEND = "smsir"
        settings.SMSIR_TEMPLATE_ID_OTP = ""
        calls = _install_urlopen(monkeypatch)

        log = sms.send_template("otp", MOBILE, {"code": "1234"})

        assert calls == []
        assert log.status == SmsLog.STATUS_SKIPPED_NO_TEMPLATE
        assert not sms.template_is_configured("otp")

    def test_missing_api_key_is_a_failure(self, settings, monkeypatch):
        settings.SMS_BACKEND = "smsir"
        settings.SMSIR_API_KEY = ""
        settings.SMSIR_TEMPLATE_ID_OTP = "123456"
        calls = _install_urlopen(monkeypatch)

        log = sms.send_template("otp", MOBILE, {"code": "1234"})

        assert calls == []
        assert log.status == SmsLog.STATUS_FAILED
        assert "SMSIR_API_KEY" in log.error


class TestContract:
    def test_truncate_sms_value(self):
        short_text = "گوشی سامسونگ"
        assert sms.truncate_sms_value(short_text) == "گوشی سامسونگ"

        long_text = "گوشی موبایل سامسونگ مدل گلکسی اس ۲۴ اولترا ۵۱۲ گیگابایت"
        truncated = sms.truncate_sms_value(long_text)
        assert len(truncated) <= 25
        assert truncated.endswith("…")

    def test_link_parameter_over_limit_raises_value_error(self, settings):
        settings.SMS_BACKEND = "console"
        with pytest.raises(ValueError, match="SMS LINK parameter exceeds 25 characters"):
            sms.send_template("back_in_stock", MOBILE, {"product": "گوشی", "link": "r/" + "x" * 30})

    def test_unknown_template_key_raises(self, settings):
        settings.SMS_BACKEND = "console"

        with pytest.raises(ValueError):
            sms.send_template("nope", MOBILE)

    def test_invalid_mobile_raises(self, settings):
        settings.SMS_BACKEND = "console"

        with pytest.raises(ValueError):
            sms.send_template("otp", "123")

    def test_unknown_backend_fails_loudly(self, settings):
        settings.SMS_BACKEND = "twilio"

        with pytest.raises(ImproperlyConfigured):
            sms.backend_name()

    def test_send_is_deferred_until_commit(self, settings, django_capture_on_commit_callbacks):
        settings.SMS_BACKEND = "console"

        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            sms.send_template_on_commit("otp", MOBILE, {"code": "1234"})
            assert not SmsLog.objects.exists()

        assert len(callbacks) == 1

        with django_capture_on_commit_callbacks(execute=True):
            sms.send_template_on_commit("otp", MOBILE, {"code": "1234"})

        assert SmsLog.objects.count() == 1


class TestSmsLogRetention:
    def test_purge_sms_logs_deletes_older_than_90_days(self):
        old_log = SmsLog.objects.create(mobile=MOBILE, kind="otp", status=SmsLog.STATUS_SENT)
        fresh_log = SmsLog.objects.create(mobile=MOBILE, kind="otp", status=SmsLog.STATUS_SENT)
        SmsLog.objects.filter(pk=old_log.pk).update(created_at=timezone.now() - timedelta(days=91))
        SmsLog.objects.filter(pk=fresh_log.pk).update(created_at=timezone.now() - timedelta(days=30))

        deleted = maintenance.purge_sms_logs()
        assert deleted == 1
        assert not SmsLog.objects.filter(pk=old_log.pk).exists()
        assert SmsLog.objects.filter(pk=fresh_log.pk).exists()

    def test_smslog_admin_purge_action_permissions_and_execution(self, client):
        old_log = SmsLog.objects.create(mobile=MOBILE, kind="otp", status=SmsLog.STATUS_SENT)
        SmsLog.objects.filter(pk=old_log.pk).update(created_at=timezone.now() - timedelta(days=95))
        url = reverse("admin:notifications_smslog_changelist")

        staff = User.objects.create_user("09129000011", password="secret", is_staff=True)
        client.force_login(staff)
        resp_staff = client.post(url, {"action": "purge_stale", "_selected_action": [str(old_log.pk)]})
        assert resp_staff.status_code in (302, 403)
        assert SmsLog.objects.filter(pk=old_log.pk).exists()

        superuser = User.objects.create_superuser("09129000012", password="secret")
        client.force_login(superuser)
        changelist = client.get(url)
        assert "purge_stale" in changelist.content.decode()

        resp_super = client.post(
            url,
            {"action": "purge_stale", "_selected_action": [str(old_log.pk)]},
            follow=True,
        )
        assert resp_super.status_code == 200
        assert not SmsLog.objects.filter(pk=old_log.pk).exists()
        assert "1 لاگ پاک شد" in resp_super.content.decode()
