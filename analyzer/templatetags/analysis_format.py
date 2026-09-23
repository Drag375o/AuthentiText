"""Display formatting for feature values, driven by FeatureSpec.unit."""
from django import template

register = template.Library()


@register.filter
def feature_display(value, unit: str) -> str:
    """
    Formats a feature value for display.

    Small values keep a decimal place: rounding 1.2% and 0.6% both to "1%" hid a
    twofold difference between two documents. Likewise -0.04 must not render as "-0".
    """
    if value is None:
        return "\u2014"
    if unit == "ratio":
        percent = value * 100
        return f"{percent:.1f}%" if 0 < abs(percent) < 10 else f"{percent:.0f}%"
    if unit == "count":
        return f"{int(round(value)):,}"
    if unit == "words":
        return f"{value:.1f}".rstrip("0").rstrip(".")
    if unit == "per100":
        return f"{value:.1f}"
    if unit == "zipf":
        return f"{value:.2f}"
    if unit == "number":
        return f"{value:.2f}" if abs(value) < 1 else f"{value:.1f}"
    return str(value)


@register.filter
def percent_of(value, total) -> float:
    """Width percentage for simple bars."""
    try:
        return round(100 * float(value) / float(total), 1) if total else 0
    except (TypeError, ValueError):
        return 0


@register.filter
def get_item(mapping, key):
    return mapping.get(key, key) if hasattr(mapping, "get") else key
