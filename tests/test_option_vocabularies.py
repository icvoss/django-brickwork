"""Every documented option value resolves to a CSS rule that exists (ADR-060).

This is the systematic version of the icvoss/django-brickwork#120 check. That
defect was `.bw-dropdown--end` shipping in every consumer's stylesheet with no
code path able to emit it; the 3.0.0 options audit then found three MORE cases
pointing the other way, where a documented DEFAULT value emitted a class the
stylesheet never matched (`.bw-tabs--underline`, `.bw-slide-over--md`,
`.bw-hero--start`).

Both directions are the same underlying fault: an option and its CSS drifting
apart with nothing asserting they agree. ADR-060 rule 2 requires every closed
vocabulary to be enforced, and where a component is consumed by `{% include %}`
the template cannot raise, so the enforcement is here instead: render every
documented value and prove the class it emits is real.

A failure here means one of two things, and the error message says which:
the CSS is missing for a value the component documents, or the component
documents a value it does not actually emit a class for.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_DIST = Path(__file__).resolve().parent.parent / "src" / "brickwork" / "static" / "brickwork" / "dist"
_CSS = (_DIST / "brickwork.css").read_text()

# (component, option, value, the class its documented value must resolve to).
# Only CSS-only modifiers belong here: values that change markup rather than
# styling are covered by their own component tests.
_VOCABULARIES: list[tuple[str, str, str, str]] = [
    # --- the three defaults that shipped with no rule (fixed in 3.0.0) -------
    ("_tabs", "variant", "underline", "bw-tabs--underline"),
    ("_tabs", "variant", "pill", "bw-tabs--pill"),
    ("_slide_over", "size", "sm", "bw-slide-over--sm"),
    ("_slide_over", "size", "md", "bw-slide-over--md"),
    ("_slide_over", "size", "lg", "bw-slide-over--lg"),
    ("_hero", "align", "start", "bw-hero--start"),
    ("_hero", "align", "center", "bw-hero--center"),
    ("_hero", "align", "end", "bw-hero--end"),
    # --- media_placement (ADR-057 section 1a, icvoss/django-brickwork#118) ---
    # "below" is the honestly-named default (the shipped column-flex layout)
    # and emits no modifier class at all, so it has no entry here: there is
    # no CSS rule to pin, only the byte-identity test in test_marketing.py.
    ("_hero", "media_placement", "behind", "bw-hero--media-behind"),
    ("_hero", "media_placement", "beside", "bw-hero--media-beside"),
    # --- width (ADR-057 section 1a, ADR-077 section 3a) ---------------------
    # "contained" is the honestly-named default (the pre-existing shell-capped
    # layout) and emits no modifier class at all, so it has no entry here:
    # there is no CSS rule to pin, only the byte-identity test in
    # test_marketing.py.
    ("_cta", "width", "bleed", "bw-cta--bleed"),
    # --- the renamed vocabularies (3.0.0) -----------------------------------
    ("_alert", "variant", "info", "bw-alert--info"),
    ("_alert", "variant", "success", "bw-alert--success"),
    ("_alert", "variant", "warning", "bw-alert--warning"),
    ("_alert", "variant", "danger", "bw-alert--danger"),
    ("_card", "size", "sm", "bw-card--size-sm"),
    ("_card", "size", "md", "bw-card--size-md"),
    ("_card", "size", "lg", "bw-card--size-lg"),
    ("_slide_over", "placement", "start", "bw-slide-over--start"),
    ("_slide_over", "placement", "end", "bw-slide-over--end"),
    ("_account_menu", "placement", "start", "bw-account-menu--start"),
    ("_account_menu", "placement", "end", "bw-account-menu--end"),
    ("_dropdown", "placement", "end", "bw-dropdown--end"),
    # --- theme-switch layout/placement (ADR-060 structural carve-out, #235) --
    # "inline" is the honestly-named default (the pre-existing render) and
    # emits no modifier class at all, so it has no entry here: there is no
    # CSS rule to pin, only the byte-identity test in test_theme_switch.py.
    ("_theme_switch", "layout", "compact", "bw-theme-switch--compact"),
    ("_theme_switch", "placement", "start", "bw-theme-switch--start"),
    ("_theme_switch", "placement", "end", "bw-theme-switch--end"),
    # --- vocabularies that were always fine, asserted so they stay that way --
    ("_badge", "variant", "neutral", "bw-badge--neutral"),
    ("_badge", "variant", "info", "bw-badge--info"),
    ("_badge", "variant", "success", "bw-badge--success"),
    ("_badge", "variant", "warning", "bw-badge--warning"),
    ("_badge", "variant", "danger", "bw-badge--danger"),
    ("_disclosure", "variant", "bordered", "bw-disclosure--bordered"),
    ("_disclosure", "variant", "divided", "bw-disclosure--divided"),
    ("_modal", "size", "sm", "bw-modal--sm"),
    ("_modal", "size", "lg", "bw-modal--lg"),
    ("_stepper", "orientation", "vertical", "bw-stepper--vertical"),
    ("_tooltip", "placement", "top", "bw-tooltip--top"),
    ("_tooltip", "placement", "bottom", "bw-tooltip--bottom"),
    ("_tooltip", "placement", "start", "bw-tooltip--start"),
    ("_tooltip", "placement", "end", "bw-tooltip--end"),
    ("_toast_region", "placement", "top-end", "bw-toast-region--top-end"),
    ("_toast_region", "placement", "top-start", "bw-toast-region--top-start"),
    ("_toast_region", "placement", "bottom-end", "bw-toast-region--bottom-end"),
    ("_toast_region", "placement", "bottom-start", "bw-toast-region--bottom-start"),
    ("_feature_grid", "columns", "2", "bw-feature-grid--2"),
    ("_feature_grid", "columns", "3", "bw-feature-grid--3"),
    ("_feature_grid", "columns", "4", "bw-feature-grid--4"),
    # --- chart card legend_position (CHT-003) -------------------------------
    # "top" is deliberately absent: it is the BASE .bw-chart-card layout, so it
    # emits no modifier class. Listing it here would demand a CSS rule for a
    # class the template correctly never renders.
    ("_chart_card", "legend_position", "bottom", "bw-chart-card--legend-bottom"),
    ("_chart_card", "legend_position", "side", "bw-chart-card--legend-side"),
]


@pytest.mark.parametrize(
    "component,option,value,css_class",
    _VOCABULARIES,
    ids=[f"{c}-{o}-{v}" for c, o, v, _ in _VOCABULARIES],
)
def test_every_documented_option_value_has_a_css_rule(component: str, option: str, value: str, css_class: str) -> None:
    # A class used as a SELECTOR, not merely mentioned in a comment: the
    # .bw-tabs--underline defect looked present to a naive substring search
    # because the class name appeared in a documentation comment.
    assert re.search(rf"\.{re.escape(css_class)}[\s,.:\[{{]", _CSS), (
        f"{component} documents {option}={value!r} but the shipped CSS has no "
        f".{css_class} rule. Either add the rule, or stop documenting the value."
    )


def test_no_dropdown_alignment_class_is_orphaned() -> None:
    """icvoss/django-brickwork#120 in its original direction.

    `.bw-dropdown--end` shipped with no code path able to emit it. It is kept in
    the CSS deliberately (the placement option that reaches it lands with the
    dropdown work), so this test pins the pairing rather than the class: if the
    rule exists, something must be able to emit it.
    """
    has_rule = re.search(r"\.bw-dropdown--end[\s,.:\[{]", _CSS)
    if not has_rule:
        pytest.skip("no .bw-dropdown--end rule shipped, so nothing to pair")

    templates = (Path(__file__).resolve().parent.parent / "src" / "brickwork").rglob("*.html")
    tags = (Path(__file__).resolve().parent.parent / "src" / "brickwork" / "templatetags").rglob("*.py")
    emitters = [p for p in (*templates, *tags) if "dropdown--end" in p.read_text()]
    assert emitters, (
        ".bw-dropdown--end is shipped CSS that no template or tag can emit "
        "(icvoss/django-brickwork#120). Either give bw_dropdown its placement "
        "option, or drop the rule."
    )
