"""Global search registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from apps.core.text import normalize_fa

MIN_LENGTH, MAX_LENGTH, PER_PROVIDER = 2, 80, 5


@dataclass(frozen=True)
class Hit:
    title: str
    subtitle: str
    url: str


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    perm: str
    run: Callable[[str], list[Hit]]


PROVIDERS: list[Provider] = []


def register(key: str, label: str, perm: str):
    def decorator(func: Callable[[str], list[Hit]]):
        PROVIDERS.append(Provider(key, label, perm, func))
        return func

    return decorator


def search(user, raw_query: str) -> list[tuple[Provider, list[Hit]]]:
    query = normalize_fa(raw_query)[:MAX_LENGTH]
    if len(query) < MIN_LENGTH:
        return []
    results = []
    for provider in PROVIDERS:
        if provider.perm and not user.has_perm(provider.perm):
            continue
        hits = provider.run(query)[:PER_PROVIDER]
        if hits:
            results.append((provider, hits))
    return results
