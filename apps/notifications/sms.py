"""SMS adapter (docs/05 §4).

Contract: `send_template(key, mobile, params)` sends one templated SMS through the
configured backend and records a `SmsLog` row. It never raises for provider
failures; callers inspect `SmsLog.status`.

* `SMS_BACKEND=console` (development default) prints the message and stores
  `status="sent"` without any network call.
* `SMS_BACKEND=smsir` calls the official Verify endpoint. A missing template id
  is not a startup error: nothing is sent and `status="skipped_no_template"` is
  logged with a warning. The caller decides whether that is fatal for its flow.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction

from apps.core.validators import normalize_iran_mobile
from apps.notifications.models import SmsLog

logger = logging.getLogger(__name__)

SMSIR_VERIFY_URL = "https://api.sms.ir/v1/send/verify"
MAX_PARAM_VALUE_LENGTH = 25

TEMPLATE_SETTINGS: dict[str, str] = {
    "otp": "SMSIR_TEMPLATE_ID_OTP",
    "order_paid": "SMSIR_TEMPLATE_ID_ORDER_PAID",
    "order_shipped": "SMSIR_TEMPLATE_ID_ORDER_SHIPPED",
    "order_shipped_courier": "SMSIR_TEMPLATE_ID_ORDER_SHIPPED_COURIER",
    "order_delivered": "SMSIR_TEMPLATE_ID_ORDER_DELIVERED",
    "order_cancelled": "SMSIR_TEMPLATE_ID_ORDER_CANCELLED",
    "order_refunded": "SMSIR_TEMPLATE_ID_ORDER_REFUNDED",
    "back_in_stock": "SMSIR_TEMPLATE_ID_BACK_IN_STOCK",
    "admin_new_order": "SMSIR_TEMPLATE_ID_ADMIN_NEW_ORDER",
}

VALID_BACKENDS = ("console", "smsir")


def backend_name() -> str:
    """Return the configured backend, failing loudly on a typo in settings."""
    name = str(getattr(settings, "SMS_BACKEND", "console") or "console").strip().lower()
    if name not in VALID_BACKENDS:
        raise ImproperlyConfigured(f"SMS_BACKEND must be one of {VALID_BACKENDS}, got {name!r}.")
    return name


def template_id(key: str) -> str:
    """Return the configured sms.ir template id for `key` (empty when unset)."""
    setting_name = TEMPLATE_SETTINGS.get(key)
    if setting_name is None:
        raise ValueError(f"Unknown SMS template key: {key!r}")
    return str(getattr(settings, setting_name, "") or "").strip()


def template_is_configured(key: str) -> bool:
    """True when `key` can actually be delivered through the current backend."""
    if backend_name() == "console":
        return True
    return bool(template_id(key))


def truncate_sms_value(value: Any, max_length: int = MAX_PARAM_VALUE_LENGTH) -> str:
    """Collapse whitespace and fit a human text parameter within sms.ir's 25-char limit."""
    cleaned = " ".join(str(value or "").split())
    if len(cleaned) <= max_length:
        return cleaned
    clipped = cleaned[: max_length - 1]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return f"{clipped}…"


def _clean_name(name: Any) -> str:
    cleaned = str(name).strip().strip("#").strip()
    if not cleaned:
        raise ValueError("SMS parameter name must not be empty.")
    return cleaned


def _clean_value(name: str, value: Any) -> str:
    # sms.ir rejects newlines and values longer than 25 characters (error 114).
    cleaned = " ".join(str(value).split())
    if name.upper() == "LINK" and len(cleaned) > MAX_PARAM_VALUE_LENGTH:
        raise ValueError(f"SMS LINK parameter exceeds {MAX_PARAM_VALUE_LENGTH} characters: {cleaned!r}")
    return cleaned[:MAX_PARAM_VALUE_LENGTH]


def _render_console(key: str, mobile: str, params: dict[str, str]) -> str:
    details = ", ".join(f"{name}={value}" for name, value in params.items())
    return f"[SMS:{key}] {mobile} | {details}" if details else f"[SMS:{key}] {mobile}"


def _send_smsir(mobile: str, template: str, params: dict[str, str]) -> tuple[bool, str, str]:
    """Call sms.ir Verify. Returns (ok, message_id, error)."""
    try:
        template_id_int = int(template)
    except ValueError:
        return False, "", f"invalid template id: {template!r}"

    body = json.dumps(
        {
            "mobile": mobile,
            "templateId": template_id_int,
            "parameters": [{"name": name, "value": value} for name, value in params.items()],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        SMSIR_VERIFY_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": str(getattr(settings, "SMSIR_API_KEY", "") or ""),
        },
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        detail = ""
        if getattr(exc, "fp", None) is not None:
            try:
                err_payload = json.loads(exc.read().decode("utf-8", errors="ignore") or "{}")
                if isinstance(err_payload, dict) and (
                    err_payload.get("status") is not None or err_payload.get("message")
                ):
                    detail = f" status={err_payload.get('status')} message={err_payload.get('message')}"
            except (json.JSONDecodeError, OSError):
                pass
        return False, "", f"HTTP {exc.code}{detail}"[:500]
    except (URLError, TimeoutError, OSError) as exc:
        return False, "", f"network error: {exc.__class__.__name__}"
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False, "", "invalid JSON response"

    if isinstance(payload, dict) and payload.get("status") == 1:
        data = payload.get("data") or {}
        return True, str(data.get("messageId") or ""), ""

    status_code = payload.get("status") if isinstance(payload, dict) else None
    message = payload.get("message") if isinstance(payload, dict) else None
    return False, "", f"status={status_code} message={message}"[:500]


def send_template(key: str, mobile: str, params: dict[str, Any] | None = None) -> SmsLog:
    """Send one templated SMS and record it in `SmsLog`. Never raises on delivery failure."""
    if key not in TEMPLATE_SETTINGS:
        raise ValueError(f"Unknown SMS template key: {key!r}")

    try:
        normalized_mobile = normalize_iran_mobile(mobile)
    except ValidationError as exc:
        raise ValueError(f"Invalid mobile number: {mobile!r}") from exc

    cleaned_params = {}
    for raw_name, raw_value in (params or {}).items():
        name = _clean_name(raw_name)
        cleaned_params[name] = _clean_value(name, raw_value)
    backend = backend_name()

    if backend == "console":
        logger.info("%s", _render_console(key, normalized_mobile, cleaned_params))
        return SmsLog.objects.create(
            mobile=normalized_mobile,
            kind=key,
            status=SmsLog.STATUS_SENT,
        )

    template = template_id(key)
    if not template:
        logger.warning(
            "SMS template %r is not configured (%s is empty); sending skipped.",
            key,
            TEMPLATE_SETTINGS[key],
        )
        return SmsLog.objects.create(
            mobile=normalized_mobile,
            kind=key,
            status=SmsLog.STATUS_SKIPPED_NO_TEMPLATE,
        )

    if not str(getattr(settings, "SMSIR_API_KEY", "") or "").strip():
        error = "SMSIR_API_KEY is empty"
        logger.error("SMS %r to %s failed: %s", key, normalized_mobile, error)
        return SmsLog.objects.create(
            mobile=normalized_mobile,
            kind=key,
            status=SmsLog.STATUS_FAILED,
            error=error,
        )

    ok, message_id, error = _send_smsir(normalized_mobile, template, cleaned_params)
    if ok:
        logger.info("SMS %r to %s sent (messageId=%s).", key, normalized_mobile, message_id or "?")
    else:
        logger.error("SMS %r to %s failed: %s", key, normalized_mobile, error)

    return SmsLog.objects.create(
        mobile=normalized_mobile,
        kind=key,
        status=SmsLog.STATUS_SENT if ok else SmsLog.STATUS_FAILED,
        provider_message_id=message_id,
        error=error,
    )


def send_template_on_commit(key: str, mobile: str, params: dict[str, Any] | None = None) -> None:
    """Schedule `send_template` after the current transaction commits.

    Use this from order/payment code so no network call runs while a DB
    transaction is open (docs/02, rule "no network inside transactions").
    """
    transaction.on_commit(lambda: send_template(key, mobile, params))
