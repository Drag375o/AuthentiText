from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import LoginForm, NewPasswordForm, RegisterForm, ResetRequestForm


def accounts_home(request):
    """/accounts/ has no page of its own: send people where they most likely meant to go."""
    if request.user.is_authenticated:
        return redirect("analyzer:dashboard")
    return redirect("accounts:login")


class SignInView(auth_views.LoginView):
    template_name = "auth/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember"):
            # Unticked: the session ends when the browser closes.
            self.request.session.set_expiry(0)
        # Ticked: default lifetime (SESSION_COOKIE_AGE, two weeks).
        return response


class RegisterView(CreateView):
    template_name = "auth/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("analyzer:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)  # sign the new user straight in
        return response


# ---- Password reset (Django's views, wired to our templates and namespace) ----

class ResetRequestView(auth_views.PasswordResetView):
    template_name = "auth/password_reset_form.html"
    email_template_name = "auth/email/password_reset.txt"
    subject_template_name = "auth/email/password_reset_subject.txt"
    form_class = ResetRequestForm
    success_url = reverse_lazy("accounts:password_reset_done")


class ResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "auth/password_reset_done.html"


class ResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "auth/password_reset_confirm.html"
    form_class = NewPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")


class ResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "auth/password_reset_complete.html"
