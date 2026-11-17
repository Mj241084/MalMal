"""Up/down ordering for lists with a plain integer column (variants, images, categories, layout, banners...)."""

from __future__ import annotations


def moved(items: list, pk: int, delta: int) -> list | None:
    """The list with `pk` moved by `delta` places, or None when it cannot move (already at the end)."""
    ids = [item.pk for item in items]
    if pk not in ids:
        return None
    index = ids.index(pk)
    target = index + delta
    if not 0 <= target < len(items):
        return None
    items = list(items)
    items[index], items[target] = items[target], items[index]
    return items


def to_front(items: list, pk: int) -> list:
    items = list(items)
    for index, item in enumerate(items):
        if item.pk == pk:
            items.insert(0, items.pop(index))
            break
    return items


def renumber(items: list, field: str = "sort") -> list:
    """Give the items 0..n-1 in list order. Returns only the ones whose value changed."""
    changed = []
    for index, item in enumerate(items):
        if getattr(item, field) != index:
            setattr(item, field, index)
            changed.append(item)
    return changed


def _columns(item, field: str) -> list[str]:
    stamped = any(column.name == "updated_at" for column in item._meta.concrete_fields)
    return [field, "updated_at"] if stamped else [field]


def reorder(items: list, pk: int, action: str, field: str = "sort") -> bool:
    """Move one item ('up' | 'down' | 'first'), renumber and save what changed. True when something changed."""
    ordered = to_front(items, pk) if action == "first" else moved(items, pk, -1 if action == "up" else 1)
    if ordered is None:
        return False
    changed = renumber(ordered, field)
    for item in changed:
        item.save(update_fields=_columns(item, field))
    return bool(changed)
