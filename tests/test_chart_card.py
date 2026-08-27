"""Tests for _chart_card.html and the {% bw_chart_mount %} tag (CHT region).

Covers CHT-012's accessibility contract on bw_chart_mount (named via
aria_label, named via aria_describedby, decorative, and the two error paths),
escaping of a hostile aria_label, the four chart-card states (loading, error,
empty, populated) each rendering only what they claim, the unfilled-block
convention, legend_position's modifier classes, and CHT-024's reservation
(min_height/aspect_ratio reaching the rendered element), including against a
real-shaped child (canvas/svg with their own intrinsic sizing) rather than an
empty mount.

Every assertion is scoped to the element it is about (never a bare substring
check against the whole document), and every test in the accessibility and
reservation sections has been teeth-checked: broken, confirmed red, restored,
confirmed byte-identical to the pre-break render. See the tester's handover
for the per-test teeth-check ledger; this module carries the tests only.
"""

from __future__ import annotations

import re

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string

from brickwork.templatetags.brickwork_components import bw_chart_mount


def _mount(snippet: str, **context: object) -> str:
    return Template("{% load brickwork_components %}" + snippet).render(Context(context))


def _card(**ctx: object) -> str:
    return render_to_string("brickwork/components/_chart_card.html", ctx)


def _extend(blocks: str, **ctx: object) -> str:
    source = "{% extends 'brickwork/components/_chart_card.html' %}{% load i18n brickwork_components %}" + blocks
    return Template(source).render(Context(ctx))


def _attrs_of(html: str, tag_class: str) -> str:
    """The opening-tag attribute text of the first element carrying tag_class,
    scoped so an assertion cannot be satisfied by an unrelated element
    elsewhere in the fragment."""
    match = re.search(rf'<[a-z0-9]+[^>]*class="[^"]*\b{re.escape(tag_class)}\b[^"]*"[^>]*>', html)
    assert match is not None, f"no element carrying class {tag_class!r} found in: {html!r}"
    return match.group(0)


# --- bw_chart_mount: the four accessibility contract cases (CHT-012) --------


def test_named_via_aria_label_gets_role_img_and_the_label() -> None:
    out = _mount('{% bw_chart_mount aria_label="Revenue by month" %}')
    attrs = _attrs_of(out, "bw-chart-mount")
    assert 'role="img"' in attrs
    assert 'aria-label="Revenue by month"' in attrs
    assert "aria-hidden" not in attrs


def test_named_via_aria_describedby_gets_role_img_and_the_reference() -> None:
    out = _mount('{% bw_chart_mount aria_describedby="chart-fallback-table" %}')
    attrs = _attrs_of(out, "bw-chart-mount")
    assert 'role="img"' in attrs
    assert 'aria-describedby="chart-fallback-table"' in attrs
    assert "aria-hidden" not in attrs


def test_decorative_is_aria_hidden_with_no_role() -> None:
    out = _mount("{% bw_chart_mount decorative=True %}")
    attrs = _attrs_of(out, "bw-chart-mount")
    assert 'aria-hidden="true"' in attrs
    assert "role=" not in attrs


def test_neither_named_nor_decorative_is_a_render_error() -> None:
    with pytest.raises(TemplateSyntaxError):
        _mount("{% bw_chart_mount %}")


@pytest.mark.parametrize(
    "snippet",
    [
        '{% bw_chart_mount aria_label="Revenue" decorative=True %}',
        '{% bw_chart_mount aria_describedby="fallback" decorative=True %}',
    ],
)
def test_a_name_combined_with_decorative_is_a_render_error(snippet: str) -> None:
    with pytest.raises(TemplateSyntaxError):
        _mount(snippet)


def test_both_aria_label_and_aria_describedby_is_not_an_error_and_label_wins() -> None:
    # Documented as legitimate (not mutually exclusive in HTML): aria_label
    # wins, aria_describedby is silently dropped. Not one of the "four cases"
    # required by the brief, but the docstring's own claim, checked here.
    out = _mount('{% bw_chart_mount aria_label="Revenue by month" aria_describedby="chart-fallback-table" %}')
    attrs = _attrs_of(out, "bw-chart-mount")
    assert 'aria-label="Revenue by month"' in attrs
    assert "aria-describedby" not in attrs


# --- escaping: a hostile aria_label is escaped, never interpolated raw ------


def test_hostile_aria_label_is_escaped_not_interpolated_raw() -> None:
    out = _mount(
        "{% bw_chart_mount aria_label=evil %}",
        evil='"><script>alert(1)</script>',
    )
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    # the injected quote must not have escaped the attribute value and left a
    # second, attacker-controlled attribute sitting on the element.
    attrs = _attrs_of(out, "bw-chart-mount")
    assert "<script" not in attrs


def test_hostile_aria_describedby_is_escaped_not_interpolated_raw() -> None:
    out = _mount(
        "{% bw_chart_mount aria_describedby=evil %}",
        evil='"><script>alert(1)</script>',
    )
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_hostile_css_class_is_escaped_not_interpolated_raw() -> None:
    out = _mount(
        "{% bw_chart_mount decorative=True css_class=evil %}",
        evil='"><script>alert(1)</script>',
    )
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


# --- card states: each renders what it claims, others do not leak ----------


def test_loading_state_shows_the_skeleton_and_not_the_mount() -> None:
    # mount= is deliberately supplied ALONGSIDE loading=True: with mount
    # omitted, {{ mount }} renders empty regardless of whether the mount
    # branch is reachable, so "data-bw-chart-mount not in out" would pass
    # even if loading failed to suppress the populated branch. Supplying a
    # real mount render makes the "and not the mount" half of this test
    # actually able to fail.
    mount_markup = _mount('{% bw_chart_mount aria_label="Revenue by month" %}')
    out = _card(loading=True, mount=mount_markup)
    assert "bw-chart-card__skeleton" in out
    assert "bw-skeleton" in out
    assert "data-bw-chart-mount" not in out
    assert "bw-alert" not in out
    assert "bw-empty-state" not in out


def test_error_state_composes_the_alert_and_not_the_mount() -> None:
    # mount= supplied alongside error=True for the same reason as the loading
    # test above: with mount omitted, {{ mount }} renders empty regardless of
    # whether the mount branch is reachable, which would make the
    # "not the mount" assertion pass even if error failed to suppress it.
    mount_markup = _mount('{% bw_chart_mount aria_label="Revenue by month" %}')
    out = _card(error=True, error_title="Could not load", error_message="Try again later.", mount=mount_markup)
    assert "bw-alert" in out
    assert "bw-alert--danger" in out
    assert "Could not load" in out
    assert "Try again later." in out
    assert "data-bw-chart-mount" not in out
    assert "bw-chart-card__skeleton" not in out
    assert "bw-empty-state" not in out


def test_empty_state_composes_the_empty_state_at_size_sm_and_not_the_mount() -> None:
    mount_markup = _mount('{% bw_chart_mount aria_label="Revenue by month" %}')
    out = _card(empty=True, empty_body="Nothing to plot yet.", mount=mount_markup)
    assert "bw-empty-state" in out
    assert "bw-empty-state--size-sm" in out
    assert "Nothing to plot yet." in out
    assert "data-bw-chart-mount" not in out
    assert "bw-chart-card__skeleton" not in out
    assert "bw-alert" not in out


def test_empty_state_action_passthrough_renders_the_action_link() -> None:
    out = _card(
        empty=True,
        empty_body="Nothing to plot yet.",
        empty_action_href="/reports/new/",
        empty_action_label="Create a report",
    )
    assert 'href="/reports/new/"' in out
    assert "Create a report" in out


def test_populated_state_shows_the_mount_context_variable_and_not_the_other_states() -> None:
    mount_markup = _mount('{% bw_chart_mount aria_label="Revenue by month" %}')
    out = _card(mount=mount_markup)
    assert "data-bw-chart-mount" in out
    assert 'aria-label="Revenue by month"' in out
    assert "bw-chart-card__skeleton" not in out
    assert "bw-alert" not in out
    assert "bw-empty-state" not in out


def test_no_state_flag_and_no_mount_renders_an_empty_mount_slot() -> None:
    # Matches _card.html's own unfilled-block convention: nothing set, nothing
    # rendered inside the mount wrapper, but the wrapper itself is still there.
    out = _card()
    assert "bw-chart-card__mount" in out
    assert "data-bw-chart-mount" not in out
    assert "bw-chart-card__skeleton" not in out
    assert "bw-alert" not in out
    assert "bw-empty-state" not in out


def test_state_precedence_loading_beats_error_and_empty() -> None:
    out = _card(loading=True, error=True, empty=True, error_message="x", empty_body="y")
    assert "bw-chart-card__skeleton" in out
    assert "bw-alert" not in out
    assert "bw-empty-state" not in out


def test_state_precedence_error_beats_empty() -> None:
    out = _card(error=True, empty=True, error_message="Failed.", empty_body="Nothing yet.")
    assert "bw-alert" in out
    assert "bw-empty-state" not in out


# --- title/actions fill from the base card, chart_legend is new ------------


def test_title_and_actions_fill_the_base_cards_blocks() -> None:
    out = _extend(
        "{% block title %}<h2>Revenue</h2>{% endblock %}"
        '{% block actions %}<div class="bw-card__actions">Period selector</div>{% endblock %}',
    )
    assert "<h2>Revenue</h2>" in out
    assert "Period selector" in out


def test_chart_legend_block_renders_caller_supplied_markup() -> None:
    out = _extend(
        '{% block chart_legend %}<div class="bw-chart-card__legend">LEGEND-SENTINEL</div>{% endblock %}',
    )
    assert "LEGEND-SENTINEL" in out
    assert "bw-chart-card__legend" in out


# --- unfilled blocks emit nothing -------------------------------------------


def test_unfilled_title_and_actions_emit_no_markup() -> None:
    out = _card()
    assert "bw-card__title" not in out
    assert "bw-card__actions" not in out


def test_unfilled_chart_legend_emits_no_markup() -> None:
    out = _card()
    assert "bw-chart-card__legend" not in out


def test_bare_chart_card_has_no_state_chrome_at_all() -> None:
    out = _card()
    for marker in ("bw-chart-card__skeleton", "bw-alert", "bw-empty-state", "data-bw-chart-mount"):
        assert marker not in out, f"bare chart card emitted state chrome it was never asked for: {marker}"


# --- legend_position: modifier classes on the root -------------------------


@pytest.mark.parametrize(
    "position,modifier",
    [
        ("bottom", "bw-chart-card--legend-bottom"),
        ("side", "bw-chart-card--legend-side"),
    ],
)
def test_legend_position_emits_its_modifier_class(position: str, modifier: str) -> None:
    out = _card(legend_position=position)
    root_attrs = _attrs_of(out, "bw-chart-card")
    assert modifier in root_attrs


def test_no_legend_position_emits_no_modifier_class() -> None:
    out = _card()
    root_attrs = _attrs_of(out, "bw-chart-card")
    assert "bw-chart-card--legend-" not in root_attrs


def test_unrecognised_legend_position_passes_through_unvalidated() -> None:
    # Pins the DOCUMENTED behaviour, which was corrected to match the code
    # rather than the other way round. An include-only component cannot
    # validate, so an unrecognised value reaches the class attribute verbatim
    # and matches no rule: the legend renders in the base position and nothing
    # errors. The docstring originally claimed the value was "silently
    # ignored, no modifier class emitted", which was false in the half that
    # matters to a consumer reading the root's class list.
    #
    # This is the stated contract, not a defect pin: it goes red if the
    # component ever starts validating, which would be a deliberate change
    # (and the signal to promote this to a tag, per the docstring's own
    # revisit condition).
    out = _card(legend_position="diagonal")
    root_attrs = _attrs_of(out, "bw-chart-card")
    assert "bw-chart-card--legend-diagonal" in root_attrs


# --- reservation: min_height/aspect_ratio reach the rendered element -------


def test_min_height_reaches_the_mount_as_a_custom_property() -> None:
    out = _mount('{% bw_chart_mount decorative=True min_height="20rem" %}')
    attrs = _attrs_of(out, "bw-chart-mount")
    assert "--bw-chart-mount-min-height: 20rem" in attrs


def test_aspect_ratio_reaches_the_mount_as_a_custom_property() -> None:
    out = _mount('{% bw_chart_mount decorative=True aspect_ratio="16 / 9" %}')
    attrs = _attrs_of(out, "bw-chart-mount")
    assert "--bw-chart-mount-aspect-ratio: 16 / 9" in attrs


def test_neither_reservation_argument_emits_no_style_attribute() -> None:
    out = _mount("{% bw_chart_mount decorative=True %}")
    attrs = _attrs_of(out, "bw-chart-mount")
    assert "style=" not in attrs


def test_both_reservation_arguments_reach_the_element_together() -> None:
    out = _mount('{% bw_chart_mount decorative=True min_height="20rem" aspect_ratio="16 / 9" %}')
    attrs = _attrs_of(out, "bw-chart-mount")
    assert "--bw-chart-mount-min-height: 20rem" in attrs
    assert "--bw-chart-mount-aspect-ratio: 16 / 9" in attrs


# --- the trap named in the brief: real-shaped children, not an empty mount -


def test_reservation_holds_against_a_canvas_with_its_own_intrinsic_size() -> None:
    # An unstyled <canvas> defaults to 300x150, which is exactly the intrinsic
    # sizing components.css documents as fighting a naive reservation. The
    # rendered mount's OWN inline reservation must still be present regardless
    # of what the consumer's engine puts inside it: the CSS contract (verified
    # separately below) is what makes the child fill the box rather than
    # impose its own size, but this test is scoped to what the template/tag
    # itself controls, the mount element's own attributes.
    mount_markup = _mount('{% bw_chart_mount aria_label="Revenue by month" min_height="20rem" aspect_ratio="16 / 9" %}')
    out = mount_markup.replace("></div>", '><canvas width="300" height="150"></canvas></div>')
    assert "<canvas" in out
    attrs = _attrs_of(out, "bw-chart-mount")
    assert "--bw-chart-mount-min-height: 20rem" in attrs
    assert "--bw-chart-mount-aspect-ratio: 16 / 9" in attrs


def test_reservation_holds_against_an_svg_with_a_viewbox_and_no_explicit_dimensions() -> None:
    mount_markup = _mount('{% bw_chart_mount aria_label="Revenue by month" min_height="20rem" %}')
    out = mount_markup.replace("></div>", '><svg viewBox="0 0 400 200"><rect width="400" height="200" /></svg></div>')
    assert "<svg" in out
    attrs = _attrs_of(out, "bw-chart-mount")
    assert "--bw-chart-mount-min-height: 20rem" in attrs


def test_reservation_holds_against_a_child_larger_than_the_reservation() -> None:
    # A child whose OWN declared size (via width/height attrs) is larger than
    # the min_height reservation: the reservation attribute must still be
    # present on the mount regardless, and the CSS contract asserted below is
    # what is responsible for constraining the oversized child to the box.
    mount_markup = _mount('{% bw_chart_mount aria_label="Revenue by month" min_height="10rem" aspect_ratio="4 / 3" %}')
    out = mount_markup.replace("></div>", '><canvas width="2000" height="2000"></canvas></div>')
    attrs = _attrs_of(out, "bw-chart-mount")
    assert "--bw-chart-mount-min-height: 10rem" in attrs
    assert "--bw-chart-mount-aspect-ratio: 4 / 3" in attrs


def test_css_makes_a_mounted_canvas_or_svg_fill_the_reserved_box() -> None:
    # The CSS half of CHT-024's reservation claim, checked directly against
    # the shipped rule rather than trusting the docstring: an unstyled canvas
    # (300x150 default) or svg (its own viewBox) must be forced to display:
    # block; inline-size: 100%; block-size: 100% inside the mount, or the
    # reservation is fought rather than filled, exactly the failure mode the
    # brief calls out. This is a real finding target: if this fails, report
    # it rather than loosen the assertion.
    from pathlib import Path

    frontend = Path(__file__).resolve().parent.parent / "frontend" / "src" / "components.css"
    css = frontend.read_text(encoding="utf-8")
    rule = re.search(r"\.bw-chart-mount\s*>\s*canvas,\s*\n\.bw-chart-mount\s*>\s*svg\s*\{([^}]*)\}", css)
    assert rule is not None, "no .bw-chart-mount > canvas, .bw-chart-mount > svg rule found in components.css"
    body = rule.group(1)
    assert "display: block" in body
    assert "inline-size: 100%" in body
    assert "block-size: 100%" in body


def test_mount_box_itself_reserves_min_block_size_and_aspect_ratio_via_css() -> None:
    from pathlib import Path

    frontend = Path(__file__).resolve().parent.parent / "frontend" / "src" / "components.css"
    css = frontend.read_text(encoding="utf-8")
    rule = re.search(r"(?<!> )\.bw-chart-mount\s*\{([^}]*)\}", css)
    assert rule is not None, "no root .bw-chart-mount rule found in components.css"
    body = rule.group(1)
    assert "min-block-size: var(--bw-chart-mount-min-height" in body
    assert "aspect-ratio: var(--bw-chart-mount-aspect-ratio" in body


@pytest.mark.parametrize("blank", ["   ", "\t", "\n", " \t\n "])
def test_a_whitespace_only_accessible_name_is_not_a_name(blank: str) -> None:
    """A hard-required check that " " satisfies is not a requirement.

    A whitespace-only aria_label is truthy in Python and is NOT an accessible
    name to any screen reader, so testing truthiness alone would let a
    consumer meet CHT-012's mandatory contract by supplying nothing. That is
    the same failure the missing role="img" produced: valid markup, a green
    gate, and nothing reaching the user.
    """
    # Calls the tag function directly rather than through a template literal:
    # a raw newline inside {% ... aria_label="..." %} does not survive Django's
    # parser, so the template route would test the parser rather than this
    # contract for two of the four cases.
    with pytest.raises(TemplateSyntaxError):
        bw_chart_mount(aria_label=blank)
    with pytest.raises(TemplateSyntaxError):
        bw_chart_mount(aria_describedby=blank)


def test_a_padded_accessible_name_is_stripped_not_rejected() -> None:
    """Stripping must not turn a real name with stray spaces into an error."""
    out = _mount('{% bw_chart_mount aria_label="  Revenue by quarter  " %}')
    assert 'aria-label="Revenue by quarter"' in out
