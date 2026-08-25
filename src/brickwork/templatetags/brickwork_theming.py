"""``{% bw_theme_switch %}``: the live root-level control over the shell's axes.

icvoss/django-brickwork#117, owner ruling 2026-08-07 (option 3: ship the tag
AND document the recipe in docs/BRANDING.md). The four axes (theme, density,
direction, brand) are runtime attributes on the shell root <html>, and the
live color-mix() derivation means switching any of them re-themes the page
instantly with no rebuild. This tag is the shipped, tested control that
demonstrates that property, so every consumer does not hand-roll the a11y
semantics (a fieldset of radios, not buttons; each axis announced; no focus
trap) themselves and get some of them wrong.

Root-level: the tag writes attributes onto <html>, exactly where the shell
already reads bw_theme / bw_density / bw_dir / bw_brand from context and
where the compiled tokens.css derives every colour (owner ruling
2026-08-25, issue comment #5411464485: this is the whole of #117's scope).

``axes`` (ADR-060: a closed, space-separated vocabulary, one name per
concept, no new axis invented): "theme density dir" by default, per the
ruling's constraint that brand is opt-in, never a default axis (a
data-bw-brand switch is only meaningful once the consumer has authored a
[data-bw-brand=...] stylesheet, BRANDING.md Recipe 3; offering it by default
would render a control that does nothing on most sites). Requesting "brand"
requires ``brands=`` (brickwork cannot invent brand slugs a consumer never
declared).

No-JS floor (BR-BW-HTMX-001, ONE deliberate departure from the package's
usual "the floor renders a real working control" doctrine, per the ruling):
the server-rendered page is ALREADY correctly themed, so a theme switch with
no JS is a control that visibly does nothing, which is worse than absent.
The floor here is therefore "render nothing" rather than "render a working
no-JS control": the fieldset ships with the hidden attribute (the same
hidden-until-init shape bw_alert/bw_badge's dismiss button and bw_toggle's
sibling dismissible amendment use, frontend/src/js/dismissible.js), and
bwThemeSwitch removes it at init. A JS-disabled visitor, and one whose
JavaScript has not yet run, sees nothing: not a dead fieldset, not an
unstyled flash of controls with no behaviour behind them.

Persistence (SHL-003, applied here per the ruling, generalising
frontend/src/js/sidebar_collapse.js's own rule): localStorage is this
component's OWN DEFAULT persistence, itself overridable by the host. The
precedence resolves per axis, using bw_theme_locked_axes (from
brickwork.context_processors.theme, #117): an axis the resolver itself
asserted this request renders as a disabled radio group (a real server
preference exists and a client default must never clobber it); every other
axis is a free client toggle that persists to localStorage.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from django import template
from django.template.exceptions import TemplateSyntaxError
from django.utils.translation import gettext

register = template.Library()

# ADR-060: one name per concept. "brand" stays opt-in per the ruling; the
# other three are the always-available axes. Order here is the order the
# fieldsets render in (theme, density, direction, brand), independent of
# axes='s own token order or the shell's <html> attribute-writing order, so
# two calls naming the same set never disagree on layout.
_AXES = ("theme", "density", "dir", "brand")

# Each axis's closed vocabulary, matching brickwork's own settings
# (BRICKWORK_DEFAULT_THEME/-DENSITY/-DIR in conf.py) and BRANDING.md's
# documented four-axis contract. brand has no closed set here: its values
# are the consumer's own slugs, supplied via brands=.
_AXIS_VALUES = {
    "theme": ("light", "dark"),
    "density": ("compact", "comfortable", "spacious"),
    "dir": ("ltr", "rtl"),
}

# gettext() calls are made INSIDE bw_theme_switch(), never at module import
# time here: a module-level gettext() call resolves once, at process start,
# against whichever locale happened to be active then, and never again (the
# bw_search precedent in brickwork_components.py makes the same choice for
# the same reason). These are plain functions returning the translatable
# strings on demand, not pre-resolved values.
def _axis_label(axis: str) -> str:
    return {
        "theme": gettext("Theme"),
        "density": gettext("Density"),
        "dir": gettext("Direction"),
        "brand": gettext("Brand"),
    }[axis]


def _value_label(axis: str, value: str) -> str:
    return {
        "theme": {"light": gettext("Light"), "dark": gettext("Dark")},
        "density": {
            "compact": gettext("Compact"),
            "comfortable": gettext("Comfortable"),
            "spacious": gettext("Spacious"),
        },
        "dir": {"ltr": gettext("Left to right"), "rtl": gettext("Right to left")},
    }[axis][value]


def _parse_axes(axes: str) -> tuple[str, ...]:
    tokens = axes.split()
    if not tokens:
        raise TemplateSyntaxError("bw_theme_switch axes= must name at least one axis.")
    seen: list[str] = []
    for token in tokens:
        if token not in _AXES:
            raise TemplateSyntaxError(f"bw_theme_switch axes= must be drawn from {sorted(_AXES)}, got {token!r}.")
        if token in seen:
            raise TemplateSyntaxError(f"bw_theme_switch axes= names {token!r} more than once.")
        seen.append(token)
    # Render in the conventional theme/density/dir/brand order regardless of
    # the caller's axes= ordering, so two calls with the same set never
    # disagree on layout.
    return tuple(axis for axis in _AXES if axis in seen)


@register.inclusion_tag("brickwork/components/_theme_switch.html")
def bw_theme_switch(
    *,
    axes: str = "theme density dir",
    brands: Mapping[str, str] | None = None,
    label: str = "",
    locked_axes: str = "",
) -> dict:
    """The live root-level axis switch (icvoss/django-brickwork#117).

    ``axes`` (ADR-060 closed vocabulary, space-separated): which of
    theme/density/dir/brand this instance offers. Default "theme density
    dir"; "brand" is opt-in only (the ruling's constraint) and requires
    ``brands=``.

    ``brands``: required when "brand" is in ``axes``, a mapping of
    ``{slug: display label}`` for the consumer's own data-bw-brand values
    (brickwork ships no brand slugs of its own to offer).

    ``label``: optional accessible name for the control's own landmark;
    falls back to a translated default ("Display settings").

    ``locked_axes``: normally ``bw_theme_locked_axes`` from
    ``brickwork.context_processors.theme`` (a space-separated string), never
    set by hand in ordinary use. An axis named here renders as a disabled
    radio group: a real server-resolved preference exists for it this
    request, and the client must never offer to override it (SHL-003
    precedence, #117 ruling).
    """
    axis_list = _parse_axes(axes)
    if "brand" in axis_list:
        if not brands:
            raise TemplateSyntaxError(
                'bw_theme_switch axes= includes "brand", which requires brands= (a mapping of '
                "{slug: label} for the consumer's own data-bw-brand values; brickwork ships none "
                "of its own)."
            )
        if not isinstance(brands, Mapping):
            raise TemplateSyntaxError(f"bw_theme_switch brands= must be a mapping of slug -> label, got {brands!r}")

    locked = set(locked_axes.split())
    unknown_locked = locked - set(_AXES)
    if unknown_locked:
        raise TemplateSyntaxError(f"bw_theme_switch locked_axes= names an unknown axis: {sorted(unknown_locked)}")

    instance_id = f"bw-theme-switch-{uuid4().hex[:10]}"

    groups = []
    for axis in axis_list:
        if axis == "brand":
            values = list(brands.items())  # type: ignore[union-attr]  # guarded above
        else:
            values = [(value, _value_label(axis, value)) for value in _AXIS_VALUES[axis]]
        groups.append(
            {
                "axis": axis,
                "legend": _axis_label(axis),
                "name": f"{instance_id}-{axis}",
                "locked": axis in locked,
                "options": [{"value": value, "label": value_label} for value, value_label in values],
            }
        )

    return {
        "instance_id": instance_id,
        "label": label or gettext("Display settings"),
        "groups": groups,
    }
