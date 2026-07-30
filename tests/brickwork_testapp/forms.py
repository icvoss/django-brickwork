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
