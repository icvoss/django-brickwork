"""Slide-over chrome contract tests (04-interfaces section 4b, 0.14.0, #55).

_slide_over.html is consumed by EXTENDING, exactly like _modal.html: a
consumer partial opens with
{% extends "brickwork/components/_slide_over.html" %} and fills the named
blocks (slide_over_title, slide_over_body, slide_over_footer, all
semver-public per BR-BW-TPL-001). These tests render inline consumer
partials through the template engine, exactly as a consuming project would.

The static markup is the floor: nothing rests display:none, the close
control is ALWAYS rendered (BR-BW-JS-007), and the wrapped @alpinejs/focus
trap is authored inside this template only, never by the consumer
(BR-BW-JS-003). #bw-slide-over-root is a DEDICATED root from #bw-modal-root
(shell/base.html, 0.14.0) so a modal and a slide-over can coexist open.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.template import engines
from django.template.loader import render_to_string

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"

_CONSUMER = (
    '{% extends "brickwork/components/_slide_over.html" %}'
    "{% block slide_over_body %}<p>Body copy.</p>"
    '<form id="demo-form"><input id="demo-input" data-bw-autofocus></form>{% endblock %}'
    '{% block slide_over_footer %}<footer class="bw-slide-over__footer">'
    '<button type="submit" form="demo-form">Go</button></footer>{% endblock %}'
)

_NO_FOOTER_CONSUMER = (
    '{% extends "brickwork/components/_slide_over.html" %}{% block slide_over_body %}<p>Body only.</p>{% endblock %}'
)


def _render(source: str = _CONSUMER, **ctx: object) -> str:
    ctx.setdefault("title", "Edit the thing")
    return engines["django"].from_string(source).render(ctx)


def test_dialog_semantics_and_title_wiring() -> None:
    html = _render()
    assert html.count('role="dialog"') == 1
    assert 'aria-labelledby="bw-slide-over-title"' in html
    assert re.search(r'<h2 class="bw-slide-over__title" id="bw-slide-over-title">\s*Edit the thing', html)


def test_dialog_carries_the_apg_modal_wiring() -> None:
    html = _render()
    assert 'aria-modal="true"' in html


def test_slide_over_id_argument_derives_the_instance_and_title_ids() -> None:
    html = _render(slide_over_id="edit-widget")
    assert 'id="edit-widget"' in html
    assert 'aria-labelledby="edit-widget-title"' in html
    assert 'id="edit-widget-title"' in html


def test_close_control_is_always_rendered_as_an_icon_only_button() -> None:
    html = _render()
    assert 'class="bw-slide-over__close' in html
    assert 'aria-label="Close"' in html
    assert "bw-btn--icon-only" in html


def test_close_href_turns_the_close_control_into_a_real_anchor_floor() -> None:
    html = _render(close_href="/interactions/")
    assert re.search(r'<a class="bw-slide-over__close[^>]*href="/interactions/"', html)
    default = _render()
    assert '<button class="bw-slide-over__close' in default
    assert 'href="/interactions/"' not in default


def test_size_variants_and_default() -> None:
    assert "bw-slide-over--md" in _render()
    assert "bw-slide-over--lg" in _render(size="lg")
    assert "bw-slide-over--sm" in _render(size="sm")


def test_placement_variants_and_default() -> None:
    assert "bw-slide-over--end" in _render()  # default: inline-end
    assert "bw-slide-over--start" in _render(placement="start")


def test_backdrop_dismiss_flows_into_the_component_config() -> None:
    assert "backdropDismiss: true" in _render()
    assert "backdropDismiss: false" in _render(backdrop_dismiss=False)


def test_scrim_is_rendered_and_hidden_from_the_accessibility_tree() -> None:
    html = _render()
    assert 'class="bw-slide-over__scrim"' in html
    assert 'aria-hidden="true"' in html


def test_alpine_component_and_internal_focus_trap_are_authored_here() -> None:
    html = _render()
    assert 'x-data="bwSlideOver(' in html
    assert "x-trap" in html
    assert "x-trap" not in _CONSUMER and "x-data" not in _CONSUMER


def test_consumer_blocks_render_in_the_chrome() -> None:
    html = _render()
    assert '<div class="bw-slide-over__body"><p>Body copy.</p>' in html
    assert "data-bw-autofocus" in html
    assert '<footer class="bw-slide-over__footer">' in html


def test_unfilled_footer_renders_nothing() -> None:
    html = _render(_NO_FOOTER_CONSUMER)
    assert "bw-slide-over__footer" not in html


def test_slide_over_title_block_override_wins_over_the_title_context() -> None:
    source = (
        '{% extends "brickwork/components/_slide_over.html" %}'
        "{% block slide_over_title %}Custom heading{% endblock %}"
        "{% block slide_over_body %}<p>Body.</p>{% endblock %}"
    )
    html = _render(source, title="Ignored title")
    assert "Custom heading" in html
    assert "Ignored title" not in html


def test_title_context_is_escaped() -> None:
    html = _render(title="<b>bold</b>")
    assert "<b>bold</b>" not in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html


def test_no_js_floor_never_rests_display_none() -> None:
    # AC-BW-085/086-shaped: the floor markup renders in-flow, not hidden
    # behind a JS-set open state.
    html = _render()
    assert "display:none" not in html.replace(" ", "")
    assert "display: none" not in html


def test_bundle_registers_bwslideover_with_the_documented_events_and_reasons() -> None:
    bundle = _DIST_JS.read_text()
    assert "bwSlideOver" in bundle
    assert "bw:slide-over:open" in bundle
    assert "bw:slide-over:close" in bundle
    for reason in ("escape", "backdrop", "close-button", "server", "programmatic"):
        assert reason in bundle


# --- shell root (BR-BW-HTMX-005) --------------------------------------------


def test_shell_ships_a_dedicated_zero_footprint_slide_over_root() -> None:
    html = render_to_string("brickwork/shell/app.html", {})
    assert '<div id="bw-slide-over-root"></div>' in html
    # a SEPARATE root from the modal's, so both can be open at once
    assert '<div id="bw-modal-root"></div>' in html


def test_slide_over_root_is_zero_footprint_in_css() -> None:
    css = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.css"
    text = css.read_text()
    rule = re.search(r"#bw-slide-over-root\s*\{([^}]*)\}", text)
    assert rule is not None
    assert "display:contents" in rule.group(1).replace(" ", "")
