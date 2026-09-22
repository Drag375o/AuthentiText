from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User


class StyledFormMixin:
    """Adds the shared input class and autocomplete hints to every field."""

    autocomplete = {
        "username": "username",
        "email": "email",
        "password": "current-password",
        "password1": "new-password",
        "password2": "new-password",
        "new_password1": "new-password",
        "new_password2": "new-password",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            is_checkbox = isinstance(field.widget, forms.CheckboxInput)
            field.widget.attrs.setdefault("class", "field-checkbox" if is_checkbox else "field-input")
            if name in self.autocomplete:
                field.widget.attrs["autocomplete"] = self.autocomplete[name]


class LoginForm(StyledFormMixin, AuthenticationForm):
    remember = forms.BooleanField(required=False, label="Keep me logged in")

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "That username and password don't match. Check both and try again.",
    }


class RegisterForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=False, help_text="Optional, but needed if you ever want to reset your password.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class ResetRequestForm(StyledFormMixin, PasswordResetForm):
    pass


class NewPasswordForm(StyledFormMixin, SetPasswordForm):
    pass
