"""Cart rules (docs/02 §5, D29). The server re-resolves every variant on every read."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from django.db import transaction

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, Variant
from apps.core.cache import safe_cache_delete, safe_cache_get, safe_cache_set
from apps.core.text import to_fa_text

MAX_LINES = 30
MAX_QTY = 999
COUNT_TTL = 60 * 10


class CartError(Exception):
    """A user-facing reason a cart change was refused."""


@dataclass(frozen=True)
class Line:
    variant: Variant
    qty: int  # what the customer will actually get (already clamped when available)
    requested: int  # what is stored / was asked for
    available: bool

    @property
    def total(self) -> int:
        return self.variant.price * self.qty if self.available else 0

    @property
    def reduced(self) -> bool:
        return self.available and self.qty < self.requested


@dataclass(frozen=True)
class Summary:
    items_total: int
    has_unavailable: bool


def _sellable(variant: Variant) -> bool:
    return variant.is_active and variant.product.status == Product.STATUS_ACTIVE and variant.max_orderable > 0


def _to_int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def parse_items(raw: str | None) -> list[tuple[int, int]]:
    """Parse the guest cart JSON `[{"v": id, "q": qty}]`; junk is dropped, duplicates keep the max."""
    try:
        data = json.loads(raw or "[]")
    except ValueError:
        return []
    pairs: dict[int, int] = {}
    for entry in data if isinstance(data, list) else []:
        if isinstance(entry, dict):
            variant_id, qty = _to_int(entry.get("v")), _to_int(entry.get("q"))
            if variant_id > 0 and qty > 0:
                pairs[variant_id] = max(pairs.get(variant_id, 0), min(qty, MAX_QTY))
    return list(pairs.items())[:MAX_LINES]


def resolve_lines(pairs: list[tuple[int, int]]) -> list[Line]:
    variants = Variant.objects.filter(pk__in=[v for v, _ in pairs]).select_related(
        "product__brand", "product__main_image"
    )
    by_id = {variant.pk: variant for variant in variants}
    lines = []
    for variant_id, requested in pairs:
        variant = by_id.get(variant_id)
        if variant is None:  # deleted variant: silently dropped
            continue
        sellable = _sellable(variant)
        qty = min(requested, variant.max_orderable) if sellable else requested
        lines.append(Line(variant, qty, requested, sellable))
    return lines


def notices_for(lines: list[Line]) -> list[str]:
    return [
        to_fa_text(f"تعداد «{line.variant.product.title}» به {line.qty} عدد کاهش یافت (حداکثر مجاز در هر سفارش)")
        for line in lines
        if line.reduced
    ]


def summarize(lines: list[Line]) -> Summary:
    ok = [line for line in lines if line.available]
    return Summary(items_total=sum(line.total for line in ok), has_unavailable=len(ok) != len(lines))


def fingerprint(lines: list[Line]) -> str:
    """What the customer saw: variant, qty and unit price. Checkout refuses to order if it changed."""
    raw = ";".join(
        f"{line.variant.pk}:{line.qty}:{line.variant.price}"
        for line in sorted((line for line in lines if line.available), key=lambda line: line.variant.pk)
    )
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


# --- server cart ----------------------------------------------------------


def get_cart(user) -> Cart:
    return Cart.objects.get_or_create(user=user)[0]


def count(user) -> int:
    if user is None or not user.is_authenticated:
        return 0
    key = f"cart_count:{user.pk}"
    cached = safe_cache_get(key)
    if isinstance(cached, int):
        return cached
    value = CartItem.objects.filter(cart__user=user).count()
    safe_cache_set(key, value, COUNT_TTL)
    return value


def bust_count(user_id: int) -> None:
    safe_cache_delete(f"cart_count:{user_id}")


def quantities(user, variant_ids) -> dict[int, int]:
    """Stored quantity per variant in the signed-in viewer's cart (empty for guests)."""
    if user is None or not user.is_authenticated:
        return {}
    ids = list(variant_ids)
    if not ids:
        return {}
    return dict(CartItem.objects.filter(cart__user=user, variant_id__in=ids).values_list("variant_id", "qty"))


def quantity(user, variant_id: int) -> int:
    return quantities(user, [variant_id]).get(variant_id, 0)


def normalize(cart: Cart) -> tuple[list[Line], list[str]]:
    """Resolve the stored cart and persist clamped quantities (idempotent)."""
    pairs = list(cart.items.order_by("pk").values_list("variant_id", "qty"))
    lines = resolve_lines(pairs)
    for line in lines:
        if line.reduced:
            cart.items.filter(variant=line.variant).update(qty=line.qty)
    bust_count(cart.user_id)
    return lines, notices_for(lines)


def set_quantity(user, variant_id: int, qty: int) -> str:
    """Absolute quantity; 0 removes. Returns a notice ('' if none). Raises CartError."""
    qty = max(0, min(int(qty), MAX_QTY))
    with transaction.atomic():
        cart = get_cart(user)
        existing = cart.items.filter(variant_id=variant_id).first()
        notice = ""
        if qty == 0:
            if existing:
                existing.delete()
        else:
            variant = Variant.objects.select_related("product").filter(pk=variant_id).first()
            if variant is None or not _sellable(variant):
                raise CartError("این کالا در حال حاضر موجود نیست")
            if existing is None and cart.items.count() >= MAX_LINES:
                raise CartError(to_fa_text(f"سبد خرید حداکثر {MAX_LINES} قلم کالا دارد"))
            final = min(qty, variant.max_orderable)
            CartItem.objects.update_or_create(cart=cart, variant=variant, defaults={"qty": final})
            if final < qty:
                notice = to_fa_text(f"حداکثر {variant.max_orderable} عدد در هر سفارش")
    bust_count(user.pk)
    return notice


def add_one(user, variant_id: int) -> str:
    current = CartItem.objects.filter(cart__user=user, variant_id=variant_id).values_list("qty", flat=True).first() or 0
    return set_quantity(user, variant_id, current + 1)


def merge_guest_items(user, pairs: list[tuple[int, int]]) -> None:
    """Idempotent merge: qty = max(local, server), clamped to max_orderable. Never summed."""
    if not pairs:
        return
    resolved = {line.variant.pk: line for line in resolve_lines(pairs)}
    with transaction.atomic():
        cart = get_cart(user)
        existing = dict(cart.items.values_list("variant_id", "qty"))
        for variant_id, qty in pairs:
            line = resolved.get(variant_id)
            if line is None or not line.available:
                continue
            if variant_id not in existing and len(existing) >= MAX_LINES:
                continue
            target = min(max(qty, existing.get(variant_id, 0)), line.variant.max_orderable)
            if existing.get(variant_id) != target:
                CartItem.objects.update_or_create(cart=cart, variant=line.variant, defaults={"qty": target})
                existing[variant_id] = target
    bust_count(user.pk)
