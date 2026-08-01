"""Form-field rendering helpers for the accessible field partial.

``bw_field_widget`` renders a BoundField's widget with the correct accessibility
attributes wired in (aria-invalid + aria-describedby), which must sit on the
actual input element, not a wrapper, to be announced by a screen reader
(BR-BW-A11Y-002). Django's ``BoundField.as_widget`` accepts an ``attrs`` dict, so
this augments (never replaces) the field's own widget rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django import template
from django.forms.widgets import CheckboxInput, CheckboxSelectMultiple, RadioSelect, Widget
from django.utils.safestring import SafeString

if TYPE_CHECKING:
    from django.forms import BoundField

register = template.Library()


def _widget_css_class(widget: Widget) -> str:
    """The brickwork class for ``widget``: bw-checkbox for checkbox controls,
    bw-radio for radio options, bw-input for everything else (Select included:
    the CSS draws it via the element selector).

    Order matters: CheckboxSelectMultiple subclasses RadioSelect, so it must be
    tested first. For RadioSelect/CheckboxSelectMultiple the class lands on the
    group wrapper div AND on every option input, because both widgets inherit
    option attrs from ``as_widget`` (``option_inherits_attrs``), the same route
    the aria attributes already take.
    """
    if isinstance(widget, CheckboxSelectMultiple | CheckboxInput):
        return "bw-checkbox"
    if isinstance(widget, RadioSelect):
        return "bw-radio"
    return "bw-input"


@register.simple_tag(name="bw_field_widget")
def bw_field_widget(field: BoundField, *, readonly: bool = False) -> SafeString:
    """Render ``field``'s widget with aria-invalid / aria-describedby wired on.

    - aria-invalid="true" when the field has errors.
    - aria-describedby lists the help-text id and the error-container id that the
      _field.html partial renders (so the input points at both).
    - readonly=True sets the ``readonly`` HTML attribute (STA-011), distinct from
      the field's own ``disabled``.
    The returned SafeString is Django's own widget HTML (escaped by Django), with
    only attribute values we control added.
    """
    described_by: list[str] = []
    if field.help_text:
        described_by.append(f"{field.auto_id}_help")
    if field.errors:
        described_by.append(f"{field.auto_id}_errors")

    attrs: dict[str, str] = {"class": _widget_css_class(field.field.widget)}
    if field.errors:
        attrs["aria-invalid"] = "true"
    if described_by:
        attrs["aria-describedby"] = " ".join(described_by)
    if readonly:
        attrs["readonly"] = "readonly"

    return field.as_widget(attrs=attrs)
