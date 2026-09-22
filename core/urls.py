from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("about/", views.about, name="about"),
    # Routes below are placeholders until their phases are built.
    # They render an honest "in progress" page instead of a 404.
    path("analyze/", views.upcoming, {"feature": "Analyze"}, name="analyze"),
    path("compare/", views.upcoming, {"feature": "Compare"}, name="compare"),
    path("profile/", views.upcoming, {"feature": "Writing Profile"}, name="profile"),
    path("login/", views.upcoming, {"feature": "Login"}, name="login"),
    path("register/", views.upcoming, {"feature": "Register"}, name="register"),
]
