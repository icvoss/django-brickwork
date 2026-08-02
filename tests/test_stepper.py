"""Stepper component tests (04-interfaces section 4b, 0.14.0, brickwork#59).

Renders the shipped _stepper.html include directly (no testapp needed). The
component is purely structural: no Alpine.data component, no bw: event, no
JavaScript at all, so the no-JS floor holds by construction
(BR-BW-HTMX-001/006). Status (complete/current/upcoming) must never be
carried by colour alone (WCAG 2.2): each step's state is conveyed by a
glyph, the CSS state class, AND visually-hidden text.
"""

from __future__ import annotations

from django.template.loader import render_to_string

_STEPS = [
    {"label": "Account", "status": "complete"},
    {"label": "Business details", "status": "current"},
    {"label": "Review", "status": "upcoming"},
]


def _render(**ctx: object) -> str:
    ctx.setdefault("steps", _STEPS)
    return render_to_string("brickwork/components/_stepper.html", ctx)


def test_renders_an_ordered_list_of_all_steps() -> None:
    html = _render()
    assert '<ol class="bw-stepper' in html
    for step in _STEPS:
        assert step["label"] in html


def test_current_step_carries_aria_current_step() -> None:
    html = _render()
    current_index = html.index("bw-stepper__step--current")
    segment = html[current_index : html.index("</li>", current_index)]
    assert 'aria-current="step"' in segment


def test_non_current_steps_do_not_carry_aria_current() -> None:
    html = _render()
    complete_index = html.index("bw-stepper__step--complete")
    segment = html[complete_index : html.index("</li>", complete_index)]
    assert "aria-current" not in segment


def test_complete_step_has_check_glyph_and_hidden_completed_text() -> None:
    html = _render()
    complete_index = html.index("bw-stepper__step--complete")
    segment = html[complete_index : html.index("</li>", complete_index)]
    assert "bw-icon" in segment  # the check glyph
    assert '<span class="bw-visually-hidden">' in segment
    assert "(completed)" in segment
    # the glyph replaces the numbered marker for a complete step
    assert "bw-stepper__marker-number" not in segment


def test_current_step_has_numbered_marker_and_hidden_current_text() -> None:
    html = _render()
    current_index = html.index("bw-stepper__step--current")
    segment = html[current_index : html.index("</li>", current_index)]
    assert "bw-stepper__marker-number" in segment
    assert "(current step)" in segment


def test_upcoming_step_has_numbered_marker_and_hidden_not_started_text() -> None:
    html = _render()
    upcoming_index = html.index("bw-stepper__step--upcoming")
    segment = html[upcoming_index : html.index("</li>", upcoming_index)]
    assert "bw-stepper__marker-number" in segment
    assert "(not started)" in segment


def test_status_is_never_conveyed_by_colour_alone() -> None:
    # Every step must carry BOTH a distinguishing glyph/marker state AND
    # visually-hidden text naming the state in words.
    html = _render()
    assert html.count("bw-visually-hidden") == len(_STEPS)
    for phrase in ("(completed)", "(current step)", "(not started)"):
        assert phrase in html


def test_connectors_between_steps_are_decorative() -> None:
    html = _render()
    assert html.count("bw-stepper__connector") == len(_STEPS) - 1
    for match_start in _connector_positions(html):
        segment = html[match_start : html.index("</li>", match_start)]
        assert 'aria-hidden="true"' in segment


def _connector_positions(html: str) -> list[int]:
    positions = []
    start = 0
    while True:
        idx = html.find("bw-stepper__connector", start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + 1
    return positions


def test_no_connector_after_the_last_step() -> None:
    html = _render()
    last_step_index = html.rindex("bw-stepper__step--")
    assert "bw-stepper__connector" not in html[last_step_index:]


def test_orientation_horizontal_default() -> None:
    html = _render()
    assert "bw-stepper--horizontal" in html


def test_orientation_vertical() -> None:
    html = _render(orientation="vertical")
    assert "bw-stepper--vertical" in html
    assert "bw-stepper--horizontal" not in html


def test_ships_no_javascript_at_all() -> None:
    html = _render()
    assert "x-data" not in html
    assert "<script" not in html.lower()
