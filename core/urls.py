from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("about/", views.about, name="about"),
    # Routes below are placeholders until their phases are built.
    # They render an honest "in progress" page instead of a 404.
    path("profile/", views.upcoming, {"feature": "Writing Profile"}, name="profile"),
]
