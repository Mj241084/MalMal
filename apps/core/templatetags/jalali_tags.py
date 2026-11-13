from django import template

from apps.core.jalali import jalali_str, to_fa_digits

register = template.Library()


@register.filter
def to_jalali(value, format_str=None):
    """{{ obj.created_at|to_jalali:"%Y/%m/%d %H:%M" }}"""
    return jalali_str(value, fmt=format_str, persian=True)


@register.filter
def fa_digits(value):
    """{{ 123|fa_digits }} ← ۱۲۳"""
    return to_fa_digits(value)
