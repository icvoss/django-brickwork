from __future__ import annotations

from django import forms

from .models import Widget


class WidgetFilterForm(forms.Form):
    """The list page's filter-bar fields, rendered through _filter_bar.html
    (each through the accessible forms/_field.html renderer)."""

    q = forms.CharField(required=False, label="Search")
    status = forms.ChoiceField(
        required=False,
        label="Status",
        choices=[("", "All statuses"), ("draft", "Draft"), ("active", "Active"), ("archived", "Archived")],
    )


class WidgetForm(forms.ModelForm):
    # A declared (non-model) boolean so the a11y fixtures exercise the drawn
    # checkbox control (bw-checkbox) through the accessible field renderer;
    # help_text wires aria-describedby onto the checkbox input too.
    flagged = forms.BooleanField(
        required=False,
        label="Flagged",
        help_text="Mark this widget for review.",
    )

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
