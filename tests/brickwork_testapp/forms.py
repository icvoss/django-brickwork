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


# The combobox demo option sets (0.9.0): module-level so the a11y fixture
# generator and the filter endpoint read the exact same data (no fixture drift).
COLOUR_CHOICES = [("red", "Red"), ("green", "Green"), ("blue", "Blue"), ("plaid", "Plaid")]
TAG_CHOICES = [("alpha", "Alpha"), ("beta", "Beta"), ("gamma", "Gamma")]

# The standalone allow_create instance's option set (CBH-021 gap): deliberately
# small so a query that matches nothing is trivial to type in the spec.
SKILL_OPTIONS = [("python", "Python"), ("django", "Django"), ("javascript", "JavaScript")]


class ComboDemoForm(forms.Form):
    """The combobox demo form (04-interfaces 4b, 0.9.0): a single-select
    ChoiceField (server filter mode) plus a MultipleChoiceField chips case
    (client mode), and a required reason field so a failed submit proves the
    combobox selections survive the 422 re-render through the floor controls."""

    colour = forms.ChoiceField(choices=COLOUR_CHOICES, label="Colour", help_text="The widget's colour.")
    tags = forms.MultipleChoiceField(required=False, choices=TAG_CHOICES, label="Tags")
    reason = forms.CharField(label="Reason", help_text="Why these were picked.")

    def clean_colour(self) -> str:
        colour = self.cleaned_data["colour"]
        if colour == "plaid":
            # a deterministic failure ON the combobox field itself, for the
            # errored field-chrome fixtures
            raise forms.ValidationError("Plaid is a pattern, not a colour.")
        return colour


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
