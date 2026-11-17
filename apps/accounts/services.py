"""Account business rules shared by the account views and checkout."""

from __future__ import annotations

from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.accounts.models import Address, User
from apps.core.validators import normalize_iran_mobile, validate_national_code


def save_new_address(user, form) -> Address:
    """Save a validated AddressForm for `user`, keeping the one-default-per-user invariant."""
    address = form.save(commit=False)
    address.user = user
    active = Address.objects.filter(user=user, deleted_at__isnull=True)
    with transaction.atomic():
        address.is_default = form.cleaned_data["is_default"] or not active.exists()
        if address.is_default:
            active.update(is_default=False)
        address.save()
    return address


# --- staff (docs/09 module 13, D47) ---------------------------------------

STAFF_ERRORS = {
    "customer": "این شماره‌ی یک مشتری است (ورود با کد پیامکی)؛ برای همکار شماره‌ی جدا لازم است",
    "exists": "این شماره قبلاً به‌عنوان همکار ثبت شده؛ از فهرست همکاران ویرایشش کنید",
    "group": "گروه نامعتبر است؛ ابتدا setup_groups را اجرا کنید",
    "self": "حساب خودتان را نمی‌توانید غیرفعال کنید",
    "last_superuser": "آخرین مدیر کل فعال را نمی‌توان غیرفعال کرد",
    "superuser": "حساب مدیر کل از پنل ویرایش نمی‌شود",
    "not_staff": "این حساب همکار نیست",
}


class StaffError(Exception):
    """A refusal whose message is safe to show. `code` lets callers (the management command) pick their own text."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or STAFF_ERRORS[code])
        self.code = code


def _groups(names) -> list[Group]:
    names = list(names)
    groups = list(Group.objects.filter(name__in=names))
    if len(groups) != len(set(names)):
        raise StaffError("group")
    return groups


def prepare_staff(mobile: str, group_names, *, allow_existing: bool = True):
    """The checks that do not need a password. Returns (normalized mobile, existing user or None, groups)."""
    try:
        mobile = normalize_iran_mobile(mobile)
    except ValidationError as exc:
        raise StaffError("mobile", exc.messages[0]) from exc
    user = User.objects.filter(mobile=mobile).first()
    if user is not None and not user.is_staff:
        raise StaffError("customer")
    if user is not None and not allow_existing:
        raise StaffError("exists")
    return mobile, user, _groups(group_names)


def create_staff_user(
    mobile: str,
    password: str,
    group_names=(),
    *,
    first_name: str = "",
    last_name: str = "",
    allow_existing: bool = True,
) -> User:
    """Create a staff account (never a superuser). An existing staff number gets the new password and groups."""
    mobile, user, groups = prepare_staff(mobile, group_names, allow_existing=allow_existing)
    try:
        validate_password(password, user)
    except ValidationError as exc:
        raise StaffError("password", " ".join(exc.messages)) from exc
    with transaction.atomic():
        if user is None:
            user = User.objects.create_user(
                mobile, password=password, is_staff=True, first_name=first_name, last_name=last_name
            )
        else:
            user.set_password(password)
            user.save()
        user.groups.set(groups)
    return user


def _editable_staff(target: User) -> None:
    if not target.is_staff:
        raise StaffError("not_staff")
    if target.is_superuser:
        raise StaffError("superuser")


def update_staff_profile(target: User, *, first_name: str, last_name: str, group_names) -> None:
    _editable_staff(target)
    groups = _groups(group_names)
    with transaction.atomic():
        target.first_name, target.last_name = first_name, last_name
        target.save(update_fields=["first_name", "last_name"])
        target.groups.set(groups)


def reset_staff_password(target: User, password: str) -> None:
    """New password; every session of that person ends (session_version + 1)."""
    _editable_staff(target)
    try:
        validate_password(password, target)
    except ValidationError as exc:
        raise StaffError("password", " ".join(exc.messages)) from exc
    target.set_password(password)
    target.session_version += 1
    target.save(update_fields=["password", "session_version"])


def set_staff_active(target: User, *, by: User, active: bool) -> None:
    if not target.is_staff:
        raise StaffError("not_staff")
    if not active:
        if target.pk == by.pk:
            raise StaffError("self")
        others = User.objects.filter(is_staff=True, is_superuser=True, is_active=True).exclude(pk=target.pk)
        if target.is_superuser and not others.exists():
            raise StaffError("last_superuser")
    if target.is_active != active:
        target.is_active = active  # the session hash includes is_active: an inactive person's sessions stop working
        target.save(update_fields=["is_active"])


# --- customers (docs/09 module 11, D20) ------------------------------------


class CustomerError(Exception):
    """A refusal whose message is safe to show to staff."""


def _customer(user: User) -> None:
    if user.is_staff:
        raise CustomerError("حساب همکار از این بخش ویرایش نمی‌شود")


def change_national_code(user: User, raw_code: str) -> str:
    """Open the D20 lock for one validated change. The view checks the permission and writes the audit entry.

    Returns the previous code.
    """
    _customer(user)
    try:
        code = validate_national_code(raw_code)
    except ValidationError as exc:
        raise CustomerError(exc.messages[0]) from exc
    previous = user.national_code
    if code == previous:
        raise CustomerError("کد ملی تازه با کد فعلی یکی است")
    with transaction.atomic():
        user.allow_national_code_change()
        user.national_code = code
        user.save(update_fields=["national_code"])
    return previous


def set_customer_active(user: User, active: bool) -> None:
    _customer(user)
    if user.is_active != active:
        user.is_active = active
        user.save(update_fields=["is_active"])


def revoke_sessions(user: User) -> None:
    User.objects.filter(pk=user.pk).update(session_version=F("session_version") + 1)
