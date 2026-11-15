"""«خبرم کن» (docs/02 §13): subscribe, mark due on a real restock, send inside the allowed hours."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.models import SiteSettings
from apps.core.shortlinks import short_link_param
from apps.engagement.models import StockSubscription
from apps.notifications import sms
from apps.notifications.models import SmsLog

MAX_OPEN_PER_USER = 30
BATCH = 200


def _open(user):
    return StockSubscription.objects.filter(user=user, notified_at__isnull=True)


def is_subscribed(user, variant_id: int) -> bool:
    return _open(user).filter(variant_id=variant_id).exists()


def subscribe(user, variant_id: int) -> bool:
    if is_subscribed(user, variant_id):
        return True
    if _open(user).count() >= MAX_OPEN_PER_USER:
        return False
    try:
        with transaction.atomic():
            StockSubscription.objects.create(user=user, variant_id=variant_id)
    except IntegrityError:
        pass  # double click: already subscribed
    return True


def unsubscribe(user, variant_id: int) -> None:
    _open(user).filter(variant_id=variant_id).delete()


def mark_due(variant_id: int) -> int:
    """A real restock (stock edited from 0 to more). Reservation expiry never calls this."""
    return StockSubscription.objects.filter(
        variant_id=variant_id, notified_at__isnull=True, restocked_at__isnull=True
    ).update(restocked_at=timezone.now())


def send_due(now=None) -> int:
    now = now or timezone.now()
    site = SiteSettings.get_solo()
    if not site.back_in_stock_start_hour <= timezone.localtime(now).hour < site.back_in_stock_end_hour:
        return 0
    if not sms.template_is_configured("back_in_stock"):
        return 0  # nothing is burned while the template does not exist (D26)

    rows = (
        StockSubscription.objects.filter(restocked_at__isnull=False, notified_at__isnull=True)
        .select_related("user", "variant__product")
        .order_by("pk")[:BATCH]
    )
    told: set[tuple[int, int]] = set()
    sent = 0
    for sub in rows:
        variant, product = sub.variant, sub.variant.product
        if not (variant.is_active and product.is_active and variant.max_orderable > 0):
            StockSubscription.objects.filter(pk=sub.pk).update(
                restocked_at=None
            )  # sold out again: wait for the next restock
            continue
        # claim first, send after: a crash loses one SMS but never sends two
        if not StockSubscription.objects.filter(pk=sub.pk, notified_at__isnull=True).update(notified_at=now):
            continue
        key = (sub.user_id, product.pk)
        if key in told:  # two variants of one product: one SMS
            continue
        told.add(key)
        log = sms.send_safely(
            "back_in_stock",
            sub.user.mobile,
            {"PRODUCT": sms.truncate_sms_value(product.title), "LINK": short_link_param("p", product.pk)},
        )
        if log is None or log.status == SmsLog.STATUS_FAILED:
            StockSubscription.objects.filter(pk=sub.pk).update(notified_at=None)  # provider trouble: retry next run
            told.discard(key)
        else:
            sent += 1
    return sent
