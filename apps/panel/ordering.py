"""Up/down ordering for lists with a plain integer column (variants, images, categories)."""

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


def reorder(items: list, pk: int, action: str, field: str = "sort") -> bool:
    """Move one item ('up' | 'down' | 'first'), renumber and save what changed. True when something changed."""
    if action == "first":
        ordered = to_front(items, pk)
    else:
        ordered = moved(items, pk, -1 if action == "up" else 1)
    if ordered is None:
        return False
    changed = renumber(ordered, field)
    for item in changed:
        item.save(update_fields=[field, "updated_at"])
    return bool(changed)
