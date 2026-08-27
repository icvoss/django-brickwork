"""{% bw_gauge %} contract tests (icvoss/django-brickwork VIZ-007 to VIZ-010).

Covers geometry (min/max/value clamping and percentage, the closed sm/md/lg
size vocabulary), threshold_bands resolution and its closed accent/success/
warning/danger token vocabulary, the gauge_label override seam (a trusted-
markup slot mirroring _stat.html's own sparkline context variable) and its
escaped default, and the shared data-visualisation encoding contract
(ADR-081): the arc is aria-hidden and carries no text of its own, geometry
never rides on an inline width: string, and no per-instance progressbar
semantics leak in (VIZ-015). The contract assertions themselves live in
``tests/_encoding_contract.py``, the same machinery test_ranked_list.py is
proven against, so the family shares one mechanism rather than each member
growing its own regex.
"""

from __future__ import annotations

import re

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from tests._encoding_contract import (
    assert_bar_is_aria_hidden_and_empty,
    assert_no_progressbar_semantics,
    assert_text_nodes_are_not_aria_hidden,
    assert_text_nodes_carry_no_accessible_name_override,
)


def _render(src: str = "{% bw_gauge value=value %}", **ctx: object) -> str:
    ctx.setdefault("value", 73)
    return engines["django"].from_string("{% load brickwork_components %}" + src).render(ctx)


def _dash_offset(html: str) -> float:
    match = re.search(r"--bw-gauge-dash-offset:\s*([0-9.]+)", html)
    assert match is not None, f"no --bw-gauge-dash-offset found in {html!r}"
    return float(match.group(1))


# --- the floor: an SVG ring plus a visible numeric percentage ---------------


def test_floor_is_a_gauge_with_visible_percentage_text() -> None:
    out = _render()
    assert '<div class="bw-gauge bw-gauge--md"' in out
    assert '<svg class="bw-gauge__svg" viewBox="0 0 100 100" role="img"' in out
    assert '<circle class="bw-gauge__track"' in out
    assert '<circle\n      class="bw-gauge__arc bw-gauge__arc--accent"' in out
    assert '<span class="bw-gauge__label">73%</span>' in out


def test_label_option_sets_the_aria_label() -> None:
    out = _render('{% bw_gauge value=value label="Storage used" %}')
    assert 'aria-label="Storage used"' in out


def test_label_omitted_renders_no_aria_label() -> None:
    out = _render()
    assert "aria-label" not in out


# --- min/max/value geometry: computed in Python, clamped into range --------


def test_default_range_is_zero_to_a_hundred() -> None:
    out = _render(value=25)
    assert '<span class="bw-gauge__label">25%</span>' in out


def test_custom_min_max_computes_the_percentage_of_the_range() -> None:
    # 150 of a 100-200 range is the 50% mark.
    out = _render("{% bw_gauge value=value min=100 max=200 %}", value=150)
    assert '<span class="bw-gauge__label">50%</span>' in out


def test_value_above_max_clamps_to_a_full_ring() -> None:
    out = _render(value=999)
    assert '<span class="bw-gauge__label">100%</span>' in out
    assert _dash_offset(out) == pytest.approx(0.0, abs=0.01)


def test_value_below_min_clamps_to_an_empty_ring() -> None:
    out = _render("{% bw_gauge value=value min=10 %}", value=-5)
    assert '<span class="bw-gauge__label">0%</span>' in out
    circumference_match = re.search(r"--bw-gauge-dash-array:\s*([0-9.]+)", out)
    assert circumference_match is not None
    assert _dash_offset(out) == pytest.approx(float(circumference_match.group(1)), abs=0.01)


def test_max_must_be_strictly_greater_than_min() -> None:
    with pytest.raises(TemplateSyntaxError, match="max"):
        _render("{% bw_gauge value=value min=10 max=5 %}")


def test_max_equal_to_min_is_rejected() -> None:
    with pytest.raises(TemplateSyntaxError, match="max"):
        _render("{% bw_gauge value=value min=10 max=10 %}")


def test_non_numeric_value_is_rejected() -> None:
    with pytest.raises(TemplateSyntaxError, match="value"):
        _render(value="not-a-number")


# --- size: the closed sm/md/lg vocabulary (VIZ-010) -------------------------


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_size_emits_its_modifier_class(size: str) -> None:
    out = _render('{% bw_gauge value=value size="' + size + '" %}')
    assert f"bw-gauge--{size}" in out


def test_size_rejects_anything_outside_the_closed_vocabulary() -> None:
    with pytest.raises(TemplateSyntaxError, match="size"):
        _render('{% bw_gauge value=value size="xl" %}')


# --- threshold_bands (VIZ-009): closed token vocabulary, COL-030 pairing ---


_BANDS = [
    {"max": 50, "token": "danger"},
    {"max": 80, "token": "warning"},
    {"max": 100, "token": "success"},
]


def test_threshold_bands_resolve_the_lowest_matching_band() -> None:
    out = _render("{% bw_gauge value=value threshold_bands=bands %}", value=30, bands=_BANDS)
    assert "bw-gauge__arc--danger" in out


def test_threshold_bands_resolve_across_the_boundary() -> None:
    out = _render("{% bw_gauge value=value threshold_bands=bands %}", value=60, bands=_BANDS)
    assert "bw-gauge__arc--warning" in out


def test_threshold_bands_at_the_exact_boundary_takes_that_band() -> None:
    out = _render("{% bw_gauge value=value threshold_bands=bands %}", value=50, bands=_BANDS)
    assert "bw-gauge__arc--danger" in out


def test_threshold_bands_past_every_max_takes_the_highest_band() -> None:
    out = _render("{% bw_gauge value=value threshold_bands=bands %}", value=100, bands=_BANDS)
    assert "bw-gauge__arc--success" in out


def test_threshold_bands_omitted_defaults_to_accent() -> None:
    out = _render()
    assert "bw-gauge__arc--accent" in out


def test_threshold_bands_empty_list_defaults_to_accent() -> None:
    out = _render("{% bw_gauge value=value threshold_bands=bands %}", bands=[])
    assert "bw-gauge__arc--accent" in out


def test_threshold_bands_rejects_a_non_list() -> None:
    with pytest.raises(TemplateSyntaxError, match="threshold_bands"):
        _render("{% bw_gauge value=value threshold_bands=bands %}", bands="not-a-list")


def test_threshold_bands_rejects_a_non_mapping_entry() -> None:
    with pytest.raises(TemplateSyntaxError, match="threshold_bands"):
        _render("{% bw_gauge value=value threshold_bands=bands %}", bands=["not-a-mapping"])


def test_threshold_bands_rejects_a_token_outside_the_closed_vocabulary() -> None:
    with pytest.raises(TemplateSyntaxError, match="token"):
        _render(
            "{% bw_gauge value=value threshold_bands=bands %}",
            bands=[{"max": 50, "token": "purple"}],
        )


def test_threshold_banded_value_always_carries_its_visible_numeric_label() -> None:
    # COL-030: a threshold colour must never ship without the paired visible
    # number, at every band, not merely the default accent case.
    for value, expected_percent in ((10, "10"), (60, "60"), (95, "95")):
        out = _render("{% bw_gauge value=value threshold_bands=bands %}", value=value, bands=_BANDS)
        assert f'<span class="bw-gauge__label">{expected_percent}%</span>' in out


# --- gauge_label (VIZ-008): a trusted-markup slot, escaped default ---------


def test_gauge_label_omitted_defaults_to_the_escaped_percentage() -> None:
    out = _render(value=42)
    assert '<span class="bw-gauge__label">42%</span>' in out


def test_gauge_label_default_is_ordinary_escaped_text_not_markup() -> None:
    # a plain (unmarked) string passed as gauge_label must render exactly as
    # any other Django context variable would: auto-escaped, never treated
    # as trusted markup merely because this seam accepts a SafeString.
    out = _render("{% bw_gauge value=value gauge_label=custom %}", custom="<script>steal()</script>")
    assert "<script>steal()</script>" not in out
    assert "&lt;script&gt;steal()&lt;/script&gt;" in out


def test_gauge_label_accepts_pre_rendered_safe_markup() -> None:
    # mirrors _stat.html's own sparkline seam: a caller-rendered, explicitly
    # mark_safe'd string is trusted and rendered verbatim.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        custom=mark_safe("<strong>42 of 100</strong>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label"><strong>42 of 100</strong></span>' in out


# --- data attribute passthrough ---------------------------------------------


def test_data_attrs_render_on_the_gauge_root() -> None:
    out = _render("{% bw_gauge value=value data=data %}", data={"data-testid": "storage-gauge"})
    assert 'class="bw-gauge bw-gauge--md" data-testid="storage-gauge"' in out


def test_gauge_root_is_a_div_not_a_span() -> None:
    # the label span nests INSIDE the root: a <span> root would collide with
    # tests/_encoding_contract.py's own documented "leaf tag" assumption for
    # same-tag element matching (_find_elements is not a nested-tag parser),
    # so the root is deliberately a <div>, matching _stat.html's own root
    # element choice for exactly this reason.
    out = _render()
    assert out.lstrip().startswith('<div class="bw-gauge')
    assert out.rstrip().endswith("</div>")


# --- encoding contract (ADR-081): shared with every viz family member ------


def test_arc_and_track_are_aria_hidden_and_carry_no_visible_text_of_their_own() -> None:
    out = _render()
    assert_bar_is_aria_hidden_and_empty(out, bar_class="bw-gauge__arc", tag="circle", expected_count=1)
    assert_bar_is_aria_hidden_and_empty(out, bar_class="bw-gauge__track", tag="circle", expected_count=1)


def test_no_progressbar_role_leaks_onto_the_gauge_root() -> None:
    # VIZ-015: a gauge here is one already-resolved reading, not a live task
    # tracked toward completion, so it deliberately carries none of
    # _progress.html's own progressbar vocabulary.
    out = _render()
    assert_no_progressbar_semantics(out, component_tag="div", component_class="bw-gauge")


def test_label_text_element_is_never_hidden_from_the_accessibility_tree() -> None:
    out = _render()
    assert_text_nodes_are_not_aria_hidden(out, text_classes=("bw-gauge__label",), expected_count=1)


def test_label_text_element_carries_no_accessible_name_override() -> None:
    out = _render()
    assert_text_nodes_carry_no_accessible_name_override(out, text_classes=("bw-gauge__label",))


def test_dash_offset_is_a_bare_unitless_number_never_a_percent_or_px_string() -> None:
    # This component's geometry is real SVG user-space units (stroke-dasharray/
    # -dashoffset), not the 0-100-riding-a-calc() convention _progress.html and
    # _ranked_list.html share, so assert_geometry_is_a_unitless_custom_property
    # does not apply verbatim (it specifically forbids a width: declaration on
    # the SAME element, which is not this component's own risk); this asserts
    # the equivalent property directly: both custom properties are bare
    # fixed-point numbers, and neither a %, "px", nor any other unit ever rides
    # along, so the arc's geometry stays inspectable data rather than opaque
    # layout, matching the family's shared "safe by construction" contract.
    out = _render(value=37)
    style_match = re.search(r'<circle\s+class="bw-gauge__arc[^"]*"[^>]*style="([^"]+)"', out)
    assert style_match is not None, f"no bw-gauge__arc style attribute found in {out!r}"
    style_value = style_match.group(1)
    dash_array_match = re.search(r"--bw-gauge-dash-array:\s*([^;]+)", style_value)
    dash_offset_match = re.search(r"--bw-gauge-dash-offset:\s*([^;]+)", style_value)
    assert dash_array_match is not None
    assert dash_offset_match is not None
    for raw_value in (dash_array_match.group(1).strip(), dash_offset_match.group(1).strip()):
        assert re.fullmatch(r"-?\d+\.\d{2}", raw_value), (
            f"{raw_value!r} is not a bare fixed-2dp unitless number: a %/px suffix would mean the "
            "arc's geometry rode on a unit rather than a plain figure"
        )
    assert "width:" not in style_value


# --- documented composition: gauge markup dropped into _stat.html's own ---
# --- sparkline seam (a claim in bw_gauge's own docstring, executed here) ---


def test_documented_stat_tile_composition_actually_renders() -> None:
    # _stat.html's sparkline context variable accepts any pre-rendered safe
    # markup (its own contract, mirrored by bw_gauge's gauge_label docstring
    # above): a gauge is exactly the kind of compact visual this seam is for.
    # A documented composition that only ever lived in prose, never executed,
    # is how a sibling component shipped a docstring example that raised
    # TemplateSyntaxError; this proves the claim by rendering it.
    gauge_markup = (
        engines["django"]
        .from_string('{% load brickwork_components %}{% bw_gauge value=73 size="sm" label="Storage used" %}')
        .render({})
    )
    out = render_to_string(
        "brickwork/components/_stat.html",
        {
            "label": "Storage",
            "value": "73%",
            "sparkline": mark_safe(gauge_markup),  # noqa: S308 (test-authored trusted markup)
        },
    )
    assert 'class="bw-stat__sparkline"' in out
    assert 'class="bw-gauge bw-gauge--sm"' in out
    assert '<span class="bw-gauge__label">73%</span>' in out
