from django import forms
from django.conf import settings

from .services.text_stats import normalize_newlines


class PasteTextForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Untitled document",
            "autocomplete": "off",
            "class": "editor-title",
        }),
    )
    # strip=False: the original text is stored exactly as written.
    text = forms.CharField(
        strip=False,
        widget=forms.Textarea(attrs={
            "placeholder": "Paste or write your text here.",
            "class": "editor-textarea",
            "spellcheck": "true",
            "rows": 18,
        }),
        error_messages={"required": "Add some text to analyze first."},
    )

    def clean_title(self) -> str:
        return self.cleaned_data["title"].strip()

    def clean_text(self) -> str:
        text = self.cleaned_data["text"]
        if not text.strip():
            raise forms.ValidationError("Add some text to analyze first.")
        # Measure with CRLF as one character, the same way the editor counts.
        length = len(normalize_newlines(text))
        limit = settings.ANALYSIS_MAX_CHARS
        if length > limit:
            raise forms.ValidationError(
                f"This text is {length:,} characters. The limit is {limit:,}; split it into smaller documents."
            )
        return text


class RenameForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        required=False,
        error_messages={"max_length": "Keep the name under 200 characters."},
        widget=forms.TextInput(attrs={"autocomplete": "off", "class": "rename-input", "maxlength": 200}),
    )

    def clean_title(self) -> str:
        # Collapse runs of whitespace; an empty name falls back to the first words of the text.
        return " ".join(self.cleaned_data["title"].split())
