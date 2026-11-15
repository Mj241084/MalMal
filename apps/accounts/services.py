"""Account business rules shared by the account views and checkout."""

from __future__ import annotations

from django.db import transaction

from apps.accounts.models import Address


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
