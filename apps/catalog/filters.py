"""Category/search filtering and sorting (docs/02 §8.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from django.db.models import Q, QuerySet

from apps.catalog.cache import filters_hash
from apps.core.text import normalize_digits

MAX_FILTER_NUMBER = 10**12

SORT_NEWEST = "newest"
SORT_CHEAPEST = "cheapest"
SORT_EXPENSIVE = "expensive"
SORT_BEST_SELLING = "best_selling"
SORT_POPULAR = "popular"

SORT_CHOICES = [
    (SORT_NEWEST, "جدیدترین"),
    (SORT_CHEAPEST, "ارزان‌ترین"),
    (SORT_EXPENSIVE, "گران‌ترین"),
    (SORT_BEST_SELLING, "پرفروش‌ترین"),
    (SORT_POPULAR, "محبوب‌ترین"),
]

SORT_ORDERING = {
    SORT_NEWEST: ["-created_at", "-pk"],
    SORT_CHEAPEST: ["min_price", "-pk"],
    SORT_EXPENSIVE: ["-max_price", "-pk"],
    SORT_BEST_SELLING: ["-purchase_count_30d", "-pk"],
    SORT_POPULAR: ["-like_count", "-pk"],
}

PAGE_SIZE = 24


def _int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    digits = "".join(ch for ch in normalize_digits(value) if ch in "0123456789")[:15]
    return min(int(digits), MAX_FILTER_NUMBER) if digits else None


def _id_or_none(value: str) -> int | None:
    value = normalize_digits(value).strip()
    return int(value) if value.isascii() and value.isdigit() and len(value) <= 12 else None


def _decimal_or_none(value: str) -> Decimal | None:
    try:
        number = Decimal(normalize_digits(value).strip())
    except (InvalidOperation, ValueError):
        return None
    # ProductSpecValue.value_number is Decimal(12, 2): anything larger would raise inside the DB adapter
    return number if number.is_finite() and abs(number) < Decimal("1e10") else None


@dataclass
class ProductFilter:
    """Parsed filter state for a category or search listing."""

    brands: list[int] = field(default_factory=list)
    min_price: int | None = None
    max_price: int | None = None
    in_stock: bool = False
    discounted: bool = False
    specs: dict[int, list[str]] = field(default_factory=dict)
    sort: str = SORT_NEWEST
    explicit_sort: bool = False
    page: int = 1
    query: str = ""

    @classmethod
    def from_params(cls, params, *, query: str = "") -> ProductFilter:
        brands = [b for b in (_id_or_none(v) for v in params.getlist("brand")) if b is not None]

        specs: dict[int, list[str]] = {}
        for key in params:
            if not key.startswith("attr_"):
                continue
            attribute_id = _id_or_none(key[5:])
            values = [value[:100] for value in params.getlist(key) if value]
            if attribute_id is not None and values:
                specs[attribute_id] = values

        raw_sort = params.get("sort")
        explicit = raw_sort in SORT_ORDERING
        return cls(
            brands=brands,
            min_price=_int_or_none(params.get("min_price")),
            max_price=_int_or_none(params.get("max_price")),
            in_stock=params.get("in_stock") == "1",
            discounted=params.get("discounted") == "1",
            specs=specs,
            sort=raw_sort if explicit else SORT_NEWEST,
            explicit_sort=explicit,
            page=max(_int_or_none(params.get("page")) or 1, 1),
            query=query,
        )

    def apply(self, queryset: QuerySet) -> QuerySet:
        return self.apply_filters(queryset).order_by(*SORT_ORDERING[self.sort])

    def apply_filters(self, queryset: QuerySet) -> QuerySet:
        if self.brands:
            queryset = queryset.filter(brand_id__in=self.brands)
        if self.min_price is not None:
            queryset = queryset.filter(max_price__gte=self.min_price)
        if self.max_price is not None:
            queryset = queryset.filter(min_price__lte=self.max_price)
        if self.in_stock:
            queryset = queryset.filter(in_stock=True)
        if self.discounted:
            queryset = queryset.filter(discount_pct__gt=0)

        for attribute_id, values in self.specs.items():
            condition = Q()
            for value in values:
                match = Q(spec_values__value_text=value)
                number = _decimal_or_none(value)
                if number is not None:
                    match |= Q(spec_values__value_number=number)
                condition |= Q(spec_values__attribute_id=attribute_id) & match
            queryset = queryset.filter(condition).distinct()

        return queryset

    def cache_fragment(self) -> str:
        return filters_hash(
            {
                "brands": ",".join(str(brand) for brand in sorted(self.brands)),
                "min_price": self.min_price,
                "max_price": self.max_price,
                "in_stock": int(self.in_stock),
                "discounted": int(self.discounted),
                "specs": ";".join(f"{key}:{','.join(sorted(values))}" for key, values in sorted(self.specs.items())),
                "q": self.query,
            }
        )

    @property
    def is_filtered(self) -> bool:
        return bool(self.brands or self.min_price or self.max_price or self.in_stock or self.discounted or self.specs)

    def pairs(self, page: int | None = None) -> list[tuple[str, object]]:
        """Deterministic (name, value) pairs for pagination links and hidden inputs."""
        params: list[tuple[str, object]] = []
        if self.query:
            params.append(("q", self.query))
        for brand in sorted(self.brands):
            params.append(("brand", brand))
        if self.min_price is not None:
            params.append(("min_price", self.min_price))
        if self.max_price is not None:
            params.append(("max_price", self.max_price))
        if self.in_stock:
            params.append(("in_stock", 1))
        if self.discounted:
            params.append(("discounted", 1))
        for attribute_id, values in sorted(self.specs.items()):
            for value in sorted(values):
                params.append((f"attr_{attribute_id}", value))
        if self.sort != SORT_NEWEST or self.explicit_sort:
            params.append(("sort", self.sort))
        if page and page > 1:
            params.append(("page", page))
        return params

    def querystring(self, page: int | None = None) -> str:
        """Deterministic querystring for pagination links (no request needed)."""
        from urllib.parse import urlencode

        return urlencode(self.pairs(page))
