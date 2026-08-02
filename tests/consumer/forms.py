from __future__ import annotations

from django import forms

from .models import Ticket


class TicketForm(forms.ModelForm):
    """The 422 form-swap loop's subject (BR-BW-HTMX-003, brickwork#61 seam 4).

    Rendered through {% bw_form %} (0.15.0), not a hand-picked per-field
    loop, so the smoke leg exercises the whole-form renderer against a real
    view, not just brickwork_testapp's existing per-field _field.html loop.
    """

    class Meta:
        model = Ticket
        fields = ["title", "priority"]

    def clean_title(self) -> str:
        title = self.cleaned_data["title"]
        if title.lower() == "invalid":
            # a deterministic validation failure for the 422-swap test
            raise forms.ValidationError("The title 'invalid' is not allowed.")
        return title
