"""Modal chrome contract tests (04-interfaces section 4b).

_modal.html is consumed by EXTENDING (unlike most components, which are
{% include %}d): a consumer partial
opens with {% extends "brickwork/components/_modal.html" %} and fills the
named blocks (modal_title, modal_body, modal_footer, all semver-public per
BR-BW-TPL-001). These tests render inline consumer partials through the
template engine, exactly as a consuming project would.

The static markup is the floor: nothing rests display:none, the close
control is ALWAYS rendered (BR-BW-JS-007: a focus trap without a visible
exit is a cage), and the wrapped @alpinejs/focus trap is authored inside
this template only, never by the consumer (BR-BW-JS-003). The
two-render-paths floor (fragment vs full page) is exercised end-to-end in
test_integration.py against the testapp's confirm route.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.template import engines

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"

_CONSUMER = (
    '{% extends "brickwork/components/_modal.html" %}'
    "{% block modal_body %}<p>Body copy.</p>"
    '<form id="demo-form"><input id="demo-input" data-bw-autofocus></form>{% endblock %}'
    '{% block modal_footer %}<footer class="bw-modal__footer">'
    '<button type="submit" form="demo-form">Go</button></footer>{% endblock %}'
)

_NO_FOOTER_CONSUMER = (
    '{% extends "brickwork/components/_modal.html" %}{% block modal_body %}<p>Body only.</p>{% endblock %}'
)


def _render(source: str = _CONSUMER, **ctx: object) -> str:
    ctx.setdefault("title", "Confirm the thing")
    return engines["django"].from_string(source).render(ctx)


def test_dialog_semantics_and_title_wiring() -> None:
    html = _render()
    assert html.count('role="dialog"') == 1
    # the accessible name: aria-labelledby points at the chrome-owned heading
    assert 'aria-labelledby="bw-modal-title"' in html
    assert re.search(r'<h2 class="bw-modal__title" id="bw-modal-title">\s*Confirm the thing', html)


def test_dialog_carries_the_apg_modal_wiring() -> None:
    # the APG Dialog (Modal) pairing on the panel element; the focus-trap
    # behaviour the pairing promises is bwModal's (AC-BW-080 exercises it).
    html = _render()
    assert 'aria-modal="true"' in html


def test_modal_id_argument_derives_the_instance_and_title_ids() -> None:
    html = _render(modal_id="confirm-reset")
    assert 'id="confirm-reset"' in html
    assert 'aria-labelledby="confirm-reset-title"' in html
    assert 'id="confirm-reset-title"' in html


def test_close_control_is_always_rendered_as_an_icon_only_button() -> None:
    # BR-BW-JS-007; ICO-008: the aria-label is wired internally.
    html = _render()
    assert 'class="bw-modal__close' in html
    assert 'aria-label="Close"' in html
    assert "bw-btn--icon-only" in html


def test_close_url_turns_the_close_control_into_a_real_anchor_floor() -> None:
    # AC-BW-086: the floor never shows a dead trigger; with close_url the
    # control is a real link out (the full-page path's exit).
    html = _render(close_url="/interactions/")
    assert re.search(r'<a class="bw-modal__close[^>]*href="/interactions/"', html)
    default = _render()
    assert '<button class="bw-modal__close' in default
    assert 'href="/interactions/"' not in default


def test_size_variants_and_default() -> None:
    assert "bw-modal--md" in _render()  # CMP-020 default
    assert "bw-modal--lg" in _render(size="lg")
    assert "bw-modal--full" in _render(size="full")


def test_backdrop_dismiss_flows_into_the_component_config() -> None:
    assert "backdropDismiss: true" in _render()  # CBH-003 default
    assert "backdropDismiss: false" in _render(backdrop_dismiss=False)


def test_scrim_is_rendered_and_hidden_from_the_accessibility_tree() -> None:
    html = _render()
    assert 'class="bw-modal__scrim"' in html
    assert 'aria-hidden="true"' in html


def test_alpine_component_and_internal_focus_trap_are_authored_here() -> None:
    # bwModal is the semver-public name (BR-BW-JS-004); x-trap is the wrapped
    # upstream directive, allowed ONLY inside this shipped template
    # (BR-BW-JS-003): the consumer partials in these tests author neither.
    html = _render()
    assert 'x-data="bwModal(' in html
    assert "x-trap" in html
    assert "x-trap" not in _CONSUMER and "x-data" not in _CONSUMER


def test_consumer_blocks_render_in_the_chrome() -> None:
    html = _render()
    assert '<div class="bw-modal__body"><p>Body copy.</p>' in html
    assert "data-bw-autofocus" in html
    assert '<footer class="bw-modal__footer">' in html


def test_unfilled_footer_renders_nothing() -> None:
    # the empty-block convention (_card.html precedent): no empty chrome.
    html = _render(_NO_FOOTER_CONSUMER)
    assert "bw-modal__footer" not in html


def test_modal_title_block_override_wins_over_the_title_context() -> None:
    source = (
        '{% extends "brickwork/components/_modal.html" %}'
        "{% block modal_title %}Custom heading{% endblock %}"
        "{% block modal_body %}<p>Body.</p>{% endblock %}"
    )
    html = _render(source, title="Ignored title")
    assert "Custom heading" in html
    assert "Ignored title" not in html


def test_title_context_is_escaped() -> None:
    html = _render(title="<b>bold</b>")
    assert "<b>bold</b>" not in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html


def test_bundle_registers_bwmodal_with_the_documented_events_and_reasons() -> None:
    bundle = _DIST_JS.read_text()
    assert "bwModal" in bundle
    assert "bw:modal:open" in bundle
    assert "bw:modal:close" in bundle
    # every documented dismissal reason survives minification as a literal
    for reason in ("escape", "backdrop", "close-button", "server", "programmatic"):
        assert reason in bundle
