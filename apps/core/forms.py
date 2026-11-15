"""Form helpers shared across apps."""

from __future__ import annotations

from django import forms


def _error_class(widget) -> str:
    if isinstance(widget, forms.Select):
        return "select-error"
    if isinstance(widget, forms.Textarea):
        return "textarea-error"
    if isinstance(widget, forms.CheckboxInput):
        return "checkbox-error"
    return "input-error"


class FieldErrorAttrsMixin:
    """Attach `aria-invalid="true"` and DaisyUI `*-error` classes on bound form errors."""

    skip_error_class_fields: tuple[str, ...] = ()

    def full_clean(self) -> None:
        super().full_clean()
        if not self.is_bound:
            return
        for name in self.errors:
            if name == "__all__":
                continue
            field = self.fields.get(name)
            if field is None:
                continue
            attrs = field.widget.attrs
            attrs["aria-invalid"] = "true"
            if name in self.skip_error_class_fields:
                continue
            err_cls = _error_class(field.widget)
            existing = attrs.get("class", "").split()
            if err_cls not in existing:
                attrs["class"] = " ".join([*existing, err_cls]).strip()
