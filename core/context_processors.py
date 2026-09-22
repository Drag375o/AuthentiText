"""Values every template needs (brand, navigation)."""
from django.conf import settings
from django.http import HttpRequest

PRIMARY_NAV = [
    {"label": "Analyze", "url_name": "core:analyze"},
    {"label": "Compare", "url_name": "core:compare"},
    {"label": "Profile", "url_name": "core:profile"},
    {"label": "About", "url_name": "core:about"},
]


def site(request: HttpRequest) -> dict:
    return {
        "SITE_NAME": "AuthentiText",
        "SITE_TAGLINE": "Analyze the signals behind your writing.",
        "PRIMARY_NAV": PRIMARY_NAV,
        "DEBUG": settings.DEBUG,
    }
