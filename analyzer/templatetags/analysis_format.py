"""Display formatting for feature values, driven by FeatureSpec.unit."""
from django import template

register = template.Library()


@register.filter
def feature_display(value, unit: str) -> str:
    if value is None:
        return "\u2014"
    if unit == "ratio":
        return f"{value * 100:.0f}%"
    if unit == "count":
        return f"{int(round(value)):,}"
    if unit == "words":
        return f"{value:.1f}".rstrip("0").rstrip(".")
    if unit == "per100":
        return f"{value:.1f}"
    if unit == "zipf":
        return f"{value:.2f}"
    return f"{value:.1f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)


@register.filter
def percent_of(value, total) -> float:
    """Width percentage for simple bars."""
    try:
        return round(100 * float(value) / float(total), 1) if total else 0
    except (TypeError, ValueError):
        return 0
