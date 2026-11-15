"""Likes and reviews: the rules live here, views only translate results (docs/02 §11, D12, D13)."""

from __future__ import annotations

from django.utils import timezone

from apps.engagement.models import Like, Review
from apps.orders.models import PAID_STATES, OrderItem


def set_like(user, product_id: int, want: bool) -> bool:
    """Absolute state, so repeated or replayed requests change nothing. The counter follows via the Like signals."""
    if want:
        Like.objects.get_or_create(user=user, product_id=product_id)
    else:
        Like.objects.filter(user=user, product_id=product_id).delete()
    return want


def has_purchased(user, product_id: int) -> bool:
    return OrderItem.objects.filter(order__user=user, order__status__in=PAID_STATES, product_id=product_id).exists()


def submit_review(user, product, *, rating: int, body: str) -> Review:
    """Create or edit the user's review. Every submission goes back to the moderation queue."""
    review, _ = Review.objects.update_or_create(
        user=user,
        product=product,
        defaults={
            "rating": rating,
            "body": body,
            "status": Review.PENDING,
            "is_verified_buyer": has_purchased(user, product.pk),
            "moderated_by": None,
            "moderated_at": None,
            "rejection_reason": "",
        },
    )
    return review


def moderate(review: Review, status: str, *, by=None, reason: str = "") -> None:
    review.status = status
    review.moderated_by = by
    review.moderated_at = timezone.now()
    review.rejection_reason = reason if status == Review.REJECTED else ""
    review.save()  # the post_save signal recomputes the product's review counters
