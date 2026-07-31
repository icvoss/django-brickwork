from __future__ import annotations

from django import forms

from .models import Widget


class WidgetForm(forms.ModelForm):
    class Meta:
        model = Widget
        fields = ["name", "status"]

    def clean_name(self) -> str:
        name = self.cleaned_data["name"]
        if name.lower() == "invalid":
            # a deterministic validation failure for the 422-swap test
            raise forms.ValidationError("The name 'invalid' is not allowed.")
        return name

    def clean(self) -> dict:
        # A deterministic CROSS-FIELD failure so the form-errors block (the
        # non-field summary) renders in the a11y fixtures: archiving requires a
        # name that passed validation. Submitting name="invalid" with
        # status="archived" therefore produces BOTH a field error and this
        # non-field error.
        cleaned = super().clean()
        if cleaned.get("status") == "archived" and not cleaned.get("name"):
            raise forms.ValidationError("An archived widget must keep a valid name.")
        return cleaned
