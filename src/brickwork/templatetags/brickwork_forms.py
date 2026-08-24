"""Form-field rendering helpers for the accessible field partial.

``bw_field_widget`` renders a BoundField's widget with the correct accessibility
attributes wired in (aria-invalid + aria-describedby), which must sit on the
actual input element, not a wrapper, to be announced by a screen reader
(BR-BW-A11Y-002). Django's ``BoundField.as_widget`` accepts an ``attrs`` dict, so
this augments (never replaces) the field's own widget rendering.

``bw_form`` (brickwork#53, FRM-002/003/019) shapes a whole Django form into
rows of fields for ``forms/_form.html``: it never renders field markup itself
(that stays ``_field.html``'s job, via ``forms/_form.html``'s per-field
include), it only decides FIELD ORDER AND GROUPING, so the two concerns
(layout shape vs field chrome) stay separate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django import template
from django.forms.widgets import CheckboxInput, CheckboxSelectMultiple, RadioSelect, Widget
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import SafeString

if TYPE_CHECKING:
    from django.forms import BoundField, Form

register = template.Library()

_FORM_LAYOUTS = {"stacked", "grid"}
# ADR-060 rule 2: density reached data-density unvalidated while its two sibling
# arguments on this same tag validated. The set is the global density axis's.
_FORM_DENSITIES = {"compact", "comfortable", "spacious"}


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
    # dict[str, str | bool], matching BoundField.as_widget's attrs signature
    # exactly (django-stubs): dict is invariant in its value type, so a narrower
    # dict[str, str] does not satisfy that parameter even though every value
    # assigned here is in fact a str.
    attrs: dict[str, str | bool] = {"class": css_class}
    if "bw-toggle" in css_class.split():
        attrs["role"] = "switch"
    if field.errors:
        attrs["aria-invalid"] = "true"
    if described_by:
        attrs["aria-describedby"] = " ".join(described_by)
    if readonly:
        attrs["readonly"] = "readonly"

    return field.as_widget(attrs=attrs)


@dataclass(frozen=True)
class RenderedFormRow:
    """One row of ``forms/_form.html``: one or more fields rendered side by
    side. A single-field row (the "stacked" default, and every field not
    named in ``rows``) is indistinguishable in markup from a bare
    ``_field.html`` include; only a genuine grouping row carries more than
    one field."""

    fields: list[BoundField]


def _shape_form_rows(form: Form, rows: Sequence[str | Sequence[str]] | None) -> list[RenderedFormRow]:
    """Group ``form``'s visible fields into rows per FRM-019's ``rows=``
    grouping: a list of field-name lists, e.g.
    ``[["first_name", "last_name"], ["email"]]``. Preserves the form's own
    field ORDER throughout: a named group renders at the position of its
    FIRST member (the earliest point that name appears in ``form``), and any
    field not mentioned in ``rows`` falls back to its own single-field row,
    in its original position, so nothing is silently dropped. ``rows=None``
    (the common case) is every field as its own row, i.e. plain stacked
    order, unchanged.
    """
    visible = list(form.visible_fields())
    if not rows:
        return [RenderedFormRow(fields=[field]) for field in visible]

    by_name = {field.name: field for field in visible}
    grouped_names: set[str] = set()
    row_groups: list[list[str]] = []
    for group in rows:
        names = [group] if isinstance(group, str) else list(group)
        row_groups.append(names)
        grouped_names.update(names)

    # Anchor position: a group renders where its first-declared member sits
    # in the form's own field order, so a rows= grouping reorders fields
    # only relative to each other within the group, never relative to the
    # ungrouped fields around them.
    anchor_index: dict[int, int] = {}
    for row_index, names in enumerate(row_groups):
        for name in names:
            if name in by_name:
                anchor_index[row_index] = visible.index(by_name[name])
                break

    entries: list[tuple[int, RenderedFormRow]] = []
    for row_index, names in enumerate(row_groups):
        fields = [by_name[name] for name in names if name in by_name]
        if not fields:
            continue  # every named field absent from the form: nothing to render
        entries.append((anchor_index.get(row_index, len(visible)), RenderedFormRow(fields=fields)))
    for position, field in enumerate(visible):
        if field.name not in grouped_names:
            entries.append((position, RenderedFormRow(fields=[field])))

    entries.sort(key=lambda entry: entry[0])
    return [row for _, row in entries]


@register.inclusion_tag("brickwork/forms/_form.html")
def bw_form(
    form: Form,
    *,
    layout: str = "stacked",
    grid_columns: int = 2,
    rows: Sequence[str | Sequence[str]] | None = None,
    density: str = "",
    readonly: bool = False,
) -> dict:
    """Render every visible field of ``form``, in order, through the same
    ``_field.html`` chrome a hand-picked per-field include uses (FRM-002), so
    a whole-form call and a per-field include produce identical markup for
    any field common to both. Hidden fields render unwrapped, exactly as
    ``{{ form.hidden_fields }}`` would.

    layout (FRM-003): "stacked" (default, one field per row) or "grid" (an
    N-column CSS grid, ``grid_columns`` wide; fields flow into it in form
    order, left-to-right then wrapping, DOM order unchanged so tab order
    still follows source order under RTL and LTR alike).

    rows (FRM-019): an explicit grouping, e.g.
    ``rows=[["first_name", "last_name"], ["email"]]``, putting named fields
    side by side on one row regardless of ``layout`` (it composes with
    "stacked" as extra row-level grouping, and with "grid" the same way any
    other row would sit in the grid flow). A field not mentioned in any
    group renders on its own row, at its original form-order position,
    never silently dropped. Composes with, and is independent of,
    ``grid_columns``.

    density (FRM-018): sets a scoped ``data-density`` override for this form
    only, composing with (not replacing) the page's own density axis.

    readonly: passed straight through to every field's ``bw_field_widget``
    call (STA-011).

    Preserves the 422 swap contract (BR-BW-HTMX-003) unmodified: this tag
    renders ONLY the fields region (plus ``forms/_form_errors.html`` for
    ``form.non_field_errors``), never a ``<form>`` element. The consumer's
    own ``<form>`` (method, action, hx-post/hx-target/hx-swap, csrf_token,
    submit button) wraps the include, exactly like the existing per-field
    worked example (docs/INTEGRATION.md section 4): swap ``hx-target="this"
    hx-swap="outerHTML"`` on that consumer-owned form re-renders this same
    include on a 422, with every field's ``{{ field.auto_id }}_errors``
    container intact.
    """
    if density and density not in _FORM_DENSITIES:
        raise TemplateSyntaxError(f"bw_form density must be one of {sorted(_FORM_DENSITIES)}, got {density!r}")
    if layout not in _FORM_LAYOUTS:
        raise TemplateSyntaxError(f"bw_form layout must be one of {sorted(_FORM_LAYOUTS)}, got {layout!r}")
    if not isinstance(grid_columns, int) or grid_columns < 1:
        raise TemplateSyntaxError(f"bw_form grid_columns must be a positive int, got {grid_columns!r}")
    return {
        "form": form,
        "form_rows": _shape_form_rows(form, rows),
        "layout": layout,
        "grid_columns": grid_columns,
        "density": density,
        "readonly": readonly,
    }
