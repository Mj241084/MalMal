"""Gateways (docs/02 §7). Money is Toman everywhere except inside an adapter's wire format (D14)."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.urls import reverse

from apps.payments.models import PaymentGateway


class GatewayError(Exception):
    """The gateway refused the request or could not be reached."""


@dataclass(frozen=True)
class StartResult:
    authority: str
    redirect_url: str
    payload: dict


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    ref_id: str = ""
    card_pan: str = ""
    payload: dict = field(default_factory=dict)
    retryable: bool = False  # network trouble: decide nothing, let the customer retry


class BaseGateway:
    code = ""
    dev_only = False

    def request(
        self, *, amount: int, callback_url: str, description: str, mobile: str, order_number: str
    ) -> StartResult:
        raise NotImplementedError

    def verify(self, *, authority: str, amount: int) -> VerifyResult:
        raise NotImplementedError

    def parse_callback(self, params) -> tuple[str, bool]:
        """(authority, customer_reports_success)"""
        return params.get("Authority", ""), params.get("Status") == "OK"


class ZarinpalGateway(BaseGateway):
    code = "zarinpal"
    # Synthetic: the sandbox accepts any UUID (docs/vendors/zarinpal §6). Never used when ZARINPAL_SANDBOX is false.
    SANDBOX_MERCHANT_ID = "00000000-0000-4000-8000-000000000000"

    @property
    def _host(self) -> str:
        return "sandbox.zarinpal.com" if settings.ZARINPAL_SANDBOX else "payment.zarinpal.com"

    def _merchant_id(self) -> str:
        if settings.ZARINPAL_MERCHANT_ID:
            return settings.ZARINPAL_MERCHANT_ID
        if settings.ZARINPAL_SANDBOX:
            return self.SANDBOX_MERCHANT_ID
        raise GatewayError("ZARINPAL_MERCHANT_ID is not configured")

    def _post(self, path: str, body: dict) -> dict:
        http_request = Request(
            f"https://{self._host}/pg/v4/payment/{path}.json",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urlopen(http_request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as exc:  # errors still carry a JSON body with the gateway code
            try:
                return json.loads(exc.read().decode("utf-8") or "{}")
            except ValueError:
                raise GatewayError(f"HTTP {exc.code}") from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise GatewayError(exc.__class__.__name__) from exc

    @staticmethod
    def _code(body: dict) -> int | None:
        for part in (body.get("data"), body.get("errors")):
            if isinstance(part, dict) and "code" in part:
                try:
                    return int(part["code"])
                except (TypeError, ValueError):
                    return None
        return None

    def request(self, *, amount, callback_url, description, mobile, order_number) -> StartResult:
        body = self._post(
            "request",
            {
                "merchant_id": self._merchant_id(),
                "amount": amount * 10,  # Toman -> Rial, only here
                "currency": "IRR",
                "description": description,
                "callback_url": callback_url,
                "metadata": {"mobile": mobile, "order_id": order_number},
            },
        )
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        authority = str(data.get("authority") or "")
        code = self._code(body)
        if code != 100 or not authority:
            raise GatewayError(f"request code={code}")
        # [VERIFY] StartPay URL: both www/payment hosts serve /pg/StartPay/; we reuse the API host (vendor note).
        return StartResult(authority, f"https://{self._host}/pg/StartPay/{authority}", {"code": code})

    def verify(self, *, authority, amount) -> VerifyResult:
        try:
            body = self._post(
                "verify", {"merchant_id": self._merchant_id(), "amount": amount * 10, "authority": authority}
            )
        except GatewayError:
            return VerifyResult(False, retryable=True)
        code = self._code(body)
        if code is None:
            return VerifyResult(False, retryable=True)
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        if code in (100, 101):  # 101 = already verified (a repeated callback): still a success
            return VerifyResult(
                True,
                ref_id=str(data.get("ref_id") or ""),
                card_pan=str(data.get("card_pan") or ""),
                payload={"code": code, "fee": data.get("fee")},
            )
        return VerifyResult(False, payload={"code": code})


class FakeGateway(BaseGateway):
    """DEBUG only: pay or cancel on a local page, no network (CLAUDE.md §2, D26)."""

    code = "fake"
    dev_only = True

    def request(self, *, amount, callback_url, description, mobile, order_number) -> StartResult:
        authority = f"FAKE{secrets.token_hex(12).upper()}"
        return StartResult(authority, reverse("payments:fake_bank", args=[authority]), {})

    def verify(self, *, authority, amount) -> VerifyResult:
        return VerifyResult(True, ref_id=str(secrets.randbelow(10**9)), card_pan="603799******1234")


_REGISTRY = {cls.code: cls() for cls in (ZarinpalGateway, FakeGateway)}


def adapter_for(code: str) -> BaseGateway:
    adapter = _REGISTRY[code]  # KeyError for unknown codes
    if adapter.dev_only and not settings.DEBUG:
        raise KeyError(code)
    return adapter


def available(amount: int | None = None) -> list[PaymentGateway]:
    rows = []
    for row in PaymentGateway.objects.filter(is_active=True):
        adapter = _REGISTRY.get(row.code)
        if adapter is None or (adapter.dev_only and not settings.DEBUG):
            continue
        if amount is None or row.accepts(amount):
            rows.append(row)
    return rows
