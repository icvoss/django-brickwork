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
    bw-radio for radio options, bw-input for everything else (Select and the
    date/time input types included: the CSS draws each via the element
    selector, no extra widget-class branch needed for those, BR-BW-INPUT-004).

    Order matters: CheckboxSelectMultiple subclasses RadioSelect, so it must be
    tested first. For RadioSelect/CheckboxSelectMultiple the class lands on the
    group wrapper div AND on every option input, because both widgets inherit
    option attrs from ``as_widget`` (``option_inherits_attrs``), the same route
    the aria attributes already take.

    Toggle opt-in (BR-BW-INPUT-001): a single ``CheckboxInput`` whose own
    widget ``attrs`` already carry ``bw-toggle`` (the consumer's form sets
    ``forms.CheckboxInput(attrs={"class": "bw-toggle"})``) renders as
    ``bw-toggle bw-checkbox`` instead of bare ``bw-checkbox``, so the CSS can
    key the switch-track presentation off ``bw-toggle`` while every aria/error
    wiring below stays identical to a plain checkbox. CheckboxSelectMultiple
    also subclasses CheckboxInput's attrs handling, but a multi-select group
    is never a single on/off switch, so only the exact CheckboxInput case
    (not the multiple-select branch above) opts in.
    """
    if isinstance(widget, CheckboxSelectMultiple):
        return "bw-checkbox"
    if isinstance(widget, CheckboxInput):
        existing = widget.attrs.get("class", "")
        if "bw-toggle" in existing.split():
            return "bw-toggle bw-checkbox"
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
    - a toggle-opted-in checkbox (BR-BW-INPUT-001, see ``_widget_css_class``)
      additionally carries ``role="switch"``: a checkbox with that role reports
      its native ``aria-checked`` from the checked state with no JS, which is
      the whole no-JS floor for the switch (setting the role is the only part
      that is not automatic).
    The returned SafeString is Django's own widget HTML (escaped by Django), with
    only attribute values we control added.
    """
    described_by: list[str] = []
    if field.help_text:
        described_by.append(f"{field.auto_id}_help")
    if field.errors:
        described_by.append(f"{field.auto_id}_errors")

    css_class = _widget_css_class(field.field.widget)
    attrs: dict[str, str] = {"class": css_class}
    if "bw-toggle" in css_class.split():
        attrs["role"] = "switch"
    if field.errors:
        attrs["aria-invalid"] = "true"
    if described_by:
        attrs["aria-describedby"] = " ".join(described_by)
    if readonly:
        attrs["readonly"] = "readonly"

    return field.as_widget(attrs=attrs)
