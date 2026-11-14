"""Authentication (OTP) and account views (docs/02 §4, P2)."""

from __future__ import annotations

import math

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django_htmx.http import HttpResponseClientRedirect, trigger_client_event

from apps.accounts import otp
from apps.accounts.forms import AddressForm, MobileForm, OTPCodeForm, ProfileForm
from apps.accounts.models import Address, OTPChallenge, User
from apps.core.validators import normalize_iran_mobile


def _normalize_or_empty(value: str | None) -> str:
    try:
        return normalize_iran_mobile(value)
    except ValidationError:
        return ""


def _client_ip(request: HttpRequest) -> str | None:
    remote = (request.META.get("REMOTE_ADDR") or "").strip()
    trusted = getattr(settings, "TRUSTED_PROXY_IPS", ())
    if remote and remote in trusted:
        x_real = (request.META.get("HTTP_X_REAL_IP") or "").strip()
        if x_real:
            return x_real
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR") or ""
        if x_forwarded:
            first = x_forwarded.split(",")[0].strip()
            if first:
                return first
    return remote or None


def _safe_next(request: HttpRequest, value: str | None) -> str:
    """Only internal destinations are accepted (docs/02 §4)."""
    value = (value or "").strip()
    if value and url_has_allowed_host_and_scheme(
        value,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return value
    return reverse("core:home")


def _seconds_context(mobile: str) -> dict:
    challenge = OTPChallenge.objects.filter(mobile=mobile).first()
    return {
        "seconds_remaining": challenge.seconds_remaining if challenge else 0,
    }


def _flow_response(request: HttpRequest, form, error_status: str = "", **extra) -> HttpResponse:
    context = {"form": form, "error_status": error_status, **extra}
    if request.htmx:
        return render(request, "partials/_login_flow.html", context)
    context["step"] = "mobile"
    return render(request, "pages/login.html", context)


def _code_response(request: HttpRequest, form, **extra) -> HttpResponse:
    context = {"form": form, **extra}
    if request.htmx:
        return render(request, "partials/_otp_code_step.html", context)
    context["step"] = "code"
    return render(request, "pages/login.html", context)


OTP_PENDING_KEY = "otp_pending"


def _remember_pending(request: HttpRequest, mobile: str, next_url: str) -> None:
    request.session[OTP_PENDING_KEY] = {"mobile": mobile, "next": next_url}


def _forget_pending(request: HttpRequest) -> None:
    request.session.pop(OTP_PENDING_KEY, None)


def _pending_step(request: HttpRequest) -> HttpResponse | None:
    """Code step (or lock notice) for a challenge this browser started; None when there is nothing to resume."""
    data = request.session.get(OTP_PENDING_KEY)
    if not data:
        return None
    mobile = data.get("mobile") or ""
    next_url = data.get("next") or ""
    challenge = OTPChallenge.objects.filter(mobile=mobile).first()
    if challenge is None:
        _forget_pending(request)
        return None
    if challenge.is_locked:
        return _flow_response(
            request,
            MobileForm(initial={"next": next_url}),
            error_status=otp.STATUS_LOCKED,
            lock_minutes=math.ceil(challenge.lock_seconds_remaining / 60),
        )
    if not challenge.is_active:
        _forget_pending(request)
        return None
    return _code_response(
        request,
        OTPCodeForm(initial={"mobile": mobile, "next": next_url}),
        mobile=mobile,
        reused=True,
        seconds_remaining=challenge.seconds_remaining,
    )


@require_GET
def login_view(request: HttpRequest) -> HttpResponse:
    target = _safe_next(request, request.GET.get("next"))
    if request.user.is_authenticated:
        return redirect(target)
    resumed = _pending_step(request)
    if resumed is not None:
        return resumed
    return render(
        request,
        "pages/login.html",
        {"form": MobileForm(initial={"next": request.GET.get("next", "")}), "step": "mobile"},
    )


@require_GET
def otp_modal_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return HttpResponse(status=204)
    resumed = _pending_step(request)
    if resumed is not None:
        return resumed
    return render(
        request,
        "partials/_login_flow.html",
        {"form": MobileForm(initial={"next": request.GET.get("next", "")})},
    )


@require_POST
def otp_cancel_view(request: HttpRequest) -> HttpResponse:
    """«تغییر شماره»: forget the pending challenge and go back to the mobile step."""
    next_url = (request.session.get(OTP_PENDING_KEY) or {}).get("next", "")
    _forget_pending(request)
    return _flow_response(request, MobileForm(initial={"next": next_url}))


@require_POST
def otp_request_view(request: HttpRequest) -> HttpResponse:
    form = MobileForm(request.POST)
    if not form.is_valid():
        return _flow_response(request, form)

    mobile = form.cleaned_data["mobile"]
    next_url = _safe_next(request, form.cleaned_data["next"])
    result = otp.request_code(mobile, _client_ip(request))

    if result.ok:
        _remember_pending(request, mobile, next_url)
        code_form = OTPCodeForm(initial={"mobile": mobile, "next": next_url})
        return _code_response(
            request,
            code_form,
            mobile=mobile,
            reused=result.status == otp.STATUS_REUSED,
            seconds_remaining=result.seconds_remaining,
        )

    return _flow_response(
        request,
        form,
        error_status=result.status,
        mobile=mobile,
        lock_minutes=math.ceil(result.lock_seconds / 60),
        retry_minutes=math.ceil(result.retry_after / 60),
    )


@require_POST
def otp_verify_view(request: HttpRequest) -> HttpResponse:
    form = OTPCodeForm(request.POST)
    if not form.is_valid():
        mobile = form.cleaned_data.get("mobile") or _normalize_or_empty(form.data.get("mobile"))
        context = _seconds_context(mobile) if mobile else {"seconds_remaining": 0}
        return _code_response(request, form, mobile=mobile, **context)

    mobile = form.cleaned_data["mobile"]
    target = _safe_next(request, form.cleaned_data["next"])
    result = otp.verify_code(mobile, form.cleaned_data["code"])

    if not result.ok:
        context = _seconds_context(mobile)
        return _code_response(
            request,
            form,
            mobile=mobile,
            error_status=result.status,
            attempts_remaining=result.attempts_remaining,
            lock_minutes=math.ceil(result.lock_seconds / 60),
            **context,
        )

    user = User.objects.filter(mobile=result.mobile).first()
    if user is None:
        try:
            with transaction.atomic():
                user = User.objects.create_user(mobile=result.mobile)
        except IntegrityError:
            user = User.objects.get(mobile=result.mobile)

    if not user.is_active or user.is_staff:
        return _code_response(
            request,
            form,
            mobile=mobile,
            error_status="unavailable",
            seconds_remaining=0,
        )

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    _forget_pending(request)
    # Cart merge hook lands in P3 (docs/02 §5); nothing to merge until the cart app exists.

    if request.htmx:
        response = HttpResponseClientRedirect(target)
        trigger_client_event(response, "auth:login", {})
        return response
    return redirect(target)


@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("core:home")


@login_required
@require_POST
def logout_all_view(request: HttpRequest) -> HttpResponse:
    user = request.user
    User.objects.filter(pk=user.pk).update(session_version=F("session_version") + 1)
    logout(request)
    messages.success(request, "از همه‌ی دستگاه‌ها خارج شدید.")
    return redirect("core:home")


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "اطلاعات حساب ذخیره شد.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, "pages/account/profile.html", {"form": form})


@login_required
@require_GET
def address_list(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/account/addresses.html", _addresses_context(request.user))


def _addresses_context(user) -> dict:
    addresses = (
        user.addresses.filter(deleted_at__isnull=True).select_related("province", "city").order_by("-is_default", "id")
    )
    return {
        "addresses": addresses,
        "neshan_map_key": settings.NESHAN_MAP_KEY,
        "neshan_service_enabled": bool(settings.NESHAN_SERVICE_KEY),
    }


def _form_context(form, address=None) -> dict:
    return {
        "form": form,
        "address": address,
        "neshan_map_key": settings.NESHAN_MAP_KEY,
        "neshan_service_enabled": bool(settings.NESHAN_SERVICE_KEY),
    }


def _addresses_section(request: HttpRequest, form=None, status: int = 200) -> HttpResponse:
    context = _addresses_context(request.user)
    context["form"] = form
    return render(request, "partials/_addresses_section.html", context, status=status)


def _address_queryset(user):
    return Address.objects.filter(user=user, deleted_at__isnull=True)


def _ensure_default_address(user) -> None:
    """Keep the `one default per user` invariant (docs/03 §3)."""
    queryset = _address_queryset(user)
    if queryset.filter(is_default=True).exists():
        return
    replacement = queryset.order_by("id").first()
    if replacement is not None:
        replacement.is_default = True
        replacement.save(update_fields=["is_default", "updated_at"])


@login_required
@require_http_methods(["GET", "POST"])
def address_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AddressForm(request.POST, user=request.user)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            with transaction.atomic():
                has_addresses = _address_queryset(request.user).exists()
                address.is_default = form.cleaned_data["is_default"] or not has_addresses
                if address.is_default:
                    _address_queryset(request.user).update(is_default=False)
                address.save()
            if request.htmx:
                return _addresses_section(request)
            return redirect("accounts:addresses")
        if request.htmx:
            return _addresses_section(request, form=form, status=200)
        return render(
            request,
            "pages/account/addresses.html",
            {**_addresses_context(request.user), "form": form},
            status=200,
        )

    form = AddressForm(user=request.user)
    if request.htmx:
        return render(request, "partials/_address_form.html", _form_context(form))
    return render(request, "pages/account/addresses.html", {**_addresses_context(request.user), "form": form})


@login_required
@require_http_methods(["GET", "POST"])
def address_edit(request: HttpRequest, pk: int) -> HttpResponse:
    address = get_object_or_404(_address_queryset(request.user), pk=pk)
    was_default = address.is_default  # the form mutates the instance while validating

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                updated = form.save(commit=False)
                updated.is_default = updated.is_default or was_default  # default only moves by choosing another one
                if updated.is_default:
                    _address_queryset(request.user).exclude(pk=updated.pk).update(is_default=False)
                updated.save()
                _ensure_default_address(request.user)
            if request.htmx:
                return _addresses_section(request)
            return redirect("accounts:addresses")
        if request.htmx:
            return _addresses_section(request, form=form)
        return render(
            request,
            "pages/account/addresses.html",
            {**_addresses_context(request.user), "form": form},
        )

    form = AddressForm(instance=address, user=request.user)
    if request.htmx:
        return render(request, "partials/_address_form.html", _form_context(form, address=address))
    return render(
        request,
        "pages/account/addresses.html",
        {**_addresses_context(request.user), "form": form},
    )


@login_required
@require_POST
def address_delete(request: HttpRequest, pk: int) -> HttpResponse:
    address = get_object_or_404(_address_queryset(request.user), pk=pk)
    with transaction.atomic():
        was_default = address.is_default
        address.is_default = False
        address.deleted_at = timezone.now()
        address.save(update_fields=["is_default", "deleted_at", "updated_at"])
        if was_default:
            replacement = _address_queryset(request.user).order_by("id").first()
            if replacement is not None:
                replacement.is_default = True
                replacement.save(update_fields=["is_default", "updated_at"])
    if request.htmx:
        return _addresses_section(request)
    return redirect("accounts:addresses")


@login_required
@require_POST
def address_set_default(request: HttpRequest, pk: int) -> HttpResponse:
    address = get_object_or_404(_address_queryset(request.user), pk=pk)
    with transaction.atomic():
        _address_queryset(request.user).update(is_default=False)
        address.is_default = True
        address.save(update_fields=["is_default", "updated_at"])
    if request.htmx:
        return _addresses_section(request)
    return redirect("accounts:addresses")
