from django import template

register = template.Library()

@register.filter
def times(number):
    return range(number)

@register.filter
def money_full(value):
    if not value:
        return "$---,---"
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "$---,---"
    return "${:,.0f}".format(value)

@register.filter
def money_abbr(value):
    """Formats 950000 -> $950K, 1150000 -> $1.15M"""
    if not value:   # None, empty, zero
        return "$---"

    try:
        value = int(value)
    except (TypeError, ValueError):
        return "$---"

    if value >= 1_000_000:
        return f"${value/1_000_000:.2f}M".rstrip("0").rstrip(".")
    if value >= 1_000:
        return f"${value/1_000:.0f}K"
    return f"${value}"