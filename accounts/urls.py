from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.accounts_home, name="home"),  # /accounts/ -> dashboard or login
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),  # POST only (Django 5)
    path("register/", views.RegisterView.as_view(), name="register"),
    path("password-reset/", views.ResetRequestView.as_view(), name="password_reset"),
    path("password-reset/sent/", views.ResetDoneView.as_view(), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", views.ResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset/complete/", views.ResetCompleteView.as_view(), name="password_reset_complete"),
]
