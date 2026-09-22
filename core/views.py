from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .landing_content import LANDING_CONTEXT


def landing(request: HttpRequest) -> HttpResponse:
    return render(request, "landing.html", LANDING_CONTEXT)


def about(request: HttpRequest) -> HttpResponse:
    return render(request, "about.html")


def upcoming(request: HttpRequest, feature: str) -> HttpResponse:
    return render(request, "upcoming.html", {"feature": feature})
