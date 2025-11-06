from django import template

register = template.Library()

@register.filter
def times(number):
    return range(number)

@register.filter
def money_full(value):
    """Formats 950000 -> $950,000"""
    if value is None:
        return "—"
    return "${:,.0f}".format(value)

@register.filter
def money_abbr(value):
    """Formats 950000 -> $950K, 1150000 -> $1.15M"""
    if value is None:
        return "—"
    if value >= 1_000_000:
        return f"${value/1_000_000:.2f}M".rstrip("0").rstrip(".")
    if value >= 1_000:
        return f"${value/1_000:.0f}K"
    return f"${value}"