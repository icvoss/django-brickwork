"""Direct render tests for the 0.12.0 feedback + dashboard components
(issues #56 and #60): skeleton (STA-004 public wrapper), tooltip (0.12.0,
supersedes STA-015's title-only baseline) and progress (STA-007).

Skeleton is a tag ({% bw_skeleton %}, templatetags/brickwork_components.py):
these tests exercise the tag directly, mirroring test_components.py's
_render() helper. Tooltip is extends-consumed (like _modal.html): these
tests render an inline consumer partial through the template engine,
mirroring test_modal.py's pattern. Progress is a plain {% include %}: these
tests render the component template directly, mirroring test_stat.py's
_render() helper.
"""

from __future__ import annotations

import re

import pytest
from django.template import Context, Template, engines
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string

# --- skeleton ({% bw_skeleton %}) -------------------------------------------


def _render_skeleton(snippet: str = "{% bw_skeleton %}", **ctx: object) -> str:
    return Template("{% load brickwork_components %}" + snippet).render(Context(ctx))


def test_skeleton_default_renders_one_text_shape() -> None:
    out = _render_skeleton()
    assert out.count("bw-skeleton bw-skeleton--text") == 1
    assert out.count("bw-skeleton--") == 1


def test_skeleton_count_renders_that_many_shapes() -> None:
    out = _render_skeleton("{% bw_skeleton count=3 %}")
    assert out.count("bw-skeleton bw-skeleton--text") == 3


@pytest.mark.parametrize("variant", ["text", "title", "row", "block"])
def test_skeleton_variant_produces_its_class(variant: str) -> None:
    out = _render_skeleton(f'{{% bw_skeleton variant="{variant}" %}}')
    assert f"bw-skeleton--{variant}" in out


def test_skeleton_invalid_variant_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render_skeleton('{% bw_skeleton variant="nope" %}')


def test_skeleton_zero_count_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render_skeleton("{% bw_skeleton count=0 %}")


def test_skeleton_negative_count_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render_skeleton("{% bw_skeleton count=-1 %}")


def test_skeleton_group_carries_aria_busy_and_hidden_loading_text() -> None:
    out = _render_skeleton()
    assert re.search(r'<div class="bw-skeleton-group" aria-busy="true">', out)
    assert re.search(r'class="[^"]*bw-visually-hidden[^"]*"[^>]*>\s*Loading', out)


def test_skeleton_shapes_are_aria_hidden() -> None:
    out = _render_skeleton("{% bw_skeleton count=2 %}")
    # each shape div carries aria-hidden="true"; the group root does not (it
    # carries aria-busy instead), so this counts only the shape occurrences
    shape_hidden = re.findall(r'<div class="bw-skeleton[^"]*"[^>]*aria-hidden="true">', out)
    assert len(shape_hidden) == 2


def test_skeleton_width_and_height_set_custom_properties() -> None:
    out = _render_skeleton('{% bw_skeleton width="12rem" height="2rem" %}')
    assert "--bw-skeleton-w: 12rem" in out
    assert "--bw-skeleton-h: 2rem" in out
    assert 'style="--bw-skeleton-w: 12rem; --bw-skeleton-h: 2rem"' in out


def test_skeleton_omitted_width_height_renders_no_style_attribute() -> None:
    out = _render_skeleton()
    assert "style=" not in out


# --- tooltip (extends-consumed) ---------------------------------------------

_TOOLTIP_CONSUMER = (
    '{% extends "brickwork/components/_tooltip.html" %}'
    "{% block tooltip_trigger %}"
    '<button type="button">Info</button>'
    "{% endblock %}"
)


def _render_tooltip(source: str = _TOOLTIP_CONSUMER, **ctx: object) -> str:
    ctx.setdefault("id", "help-tip")
    ctx.setdefault("text", "More information")
    return engines["django"].from_string(source).render(ctx)


def test_tooltip_bubble_has_role_and_matching_id() -> None:
    html = _render_tooltip(id="help-tip", text="More information")
    assert re.search(r'<span class="bw-tooltip__bubble"\s+id="help-tip"\s+role="tooltip"', html)


def test_tooltip_trigger_has_aria_describedby_and_title_no_js_floor() -> None:
    html = _render_tooltip(id="help-tip", text="More information")
    trigger_wrap = re.search(
        r'<span data-bw-tooltip-trigger aria-describedby="help-tip" title="More information">', html
    )
    assert trigger_wrap, "trigger wrapper must carry aria-describedby + the native title no-JS floor"


def test_tooltip_bubble_carries_hidden_attribute() -> None:
    html = _render_tooltip()
    bubble = re.search(r'<span class="bw-tooltip__bubble"[^>]*>', html)
    assert bubble
    # hidden is on its own line in the source; confirm it appears before the
    # closing '>' of the bubble's opening tag by checking the wider match
    assert re.search(r'<span class="bw-tooltip__bubble"[\s\S]*?hidden>', html)


def test_tooltip_wrapper_root_id_is_id_root() -> None:
    html = _render_tooltip(id="help-tip")
    assert re.search(r'<span class="bw-tooltip[^"]*"\s+id="help-tip-root"', html)


def test_tooltip_bubble_text_matches_trigger_title() -> None:
    html = _render_tooltip(id="help-tip", text="Same text everywhere")
    assert 'title="Same text everywhere"' in html
    assert re.search(r'role="tooltip"[^>]*>\s*Same text everywhere', html)


@pytest.mark.parametrize("placement", ["top", "bottom", "start", "end"])
def test_tooltip_placement_sets_the_modifier_class(placement: str) -> None:
    html = _render_tooltip(placement=placement)
    assert f"bw-tooltip bw-tooltip--{placement}" in html


def test_tooltip_default_placement_is_top() -> None:
    html = _render_tooltip()
    assert "bw-tooltip bw-tooltip--top" in html


def test_tooltip_never_carries_dialog_or_modal_semantics() -> None:
    # a tooltip is not a dialog (WAI-ARIA APG Tooltip pattern): it must never
    # trap focus or claim modal/dialog roles.
    html = _render_tooltip()
    assert 'role="dialog"' not in html
    assert "aria-modal" not in html


# --- progress ----------------------------------------------------------------


def _render_progress(**ctx: object) -> str:
    return render_to_string("brickwork/components/_progress.html", ctx)


def test_determinate_progress_has_full_aria_wiring() -> None:
    out = _render_progress(label="Import progress", value=42)
    assert 'role="progressbar"' in out
    assert 'aria-valuenow="42"' in out
    assert 'aria-valuemin="0"' in out
    assert 'aria-valuemax="100"' in out
    assert 'aria-label="Import progress"' in out


def test_determinate_progress_fill_carries_the_custom_property() -> None:
    out = _render_progress(label="Import progress", value=42)
    assert "--bw-progress-value: 42" in out


def test_indeterminate_progress_has_no_aria_valuenow() -> None:
    out = _render_progress(label="Loading")
    assert "aria-valuenow" not in out
    assert "bw-progress--indeterminate" in out


def test_determinate_progress_is_not_marked_indeterminate() -> None:
    out = _render_progress(label="Import progress", value=42)
    assert "bw-progress--indeterminate" not in out


def test_show_value_renders_visible_percent_when_determinate() -> None:
    out = _render_progress(label="Import progress", value=42, show_value=True)
    assert re.search(r'class="[^"]*bw-progress__value[^"]*"[^>]*>\s*42%', out)


def test_show_value_false_renders_no_percent_text() -> None:
    out = _render_progress(label="Import progress", value=42, show_value=False)
    assert "bw-progress__value" not in out


def test_show_value_ignored_when_indeterminate() -> None:
    out = _render_progress(label="Loading", show_value=True)
    assert "bw-progress__value" not in out
    assert "%" not in out


def test_required_label_is_the_accessible_name() -> None:
    out = _render_progress(label="Widget export", value=10)
    assert 'aria-label="Widget export"' in out
