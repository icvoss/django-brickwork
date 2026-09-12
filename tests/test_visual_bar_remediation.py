"""Regression contracts for Phase 5 visual-bar substrate fixes (#519 to #526).

Assert against the compiled stylesheet and rendered templates: a rule present
only in frontend/src is not what consumers get until npm run build lands it.
"""

from __future__ import annotations

from pathlib import Path

from django import forms
from django.template import Context, Template

_ROOT = Path(__file__).resolve().parent.parent
_COMPILED_CSS = (_ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text(encoding="utf-8")


class _MemoForm(forms.Form):
    memo = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))


def test_compiled_css_hides_close_icon_with_compound_closed_state_selector() -> None:
    # #519: single-class .bw-mobile-nav-toggle__icon--close lost to .bw-icon.
    assert ".bw-mobile-nav-toggle:not([open]) .bw-mobile-nav-toggle__icon--close" in _COMPILED_CSS


def test_compiled_css_carves_textarea_out_of_fixed_input_block_size() -> None:
    # #521: .bw-input fixed block-size must not win on textareas.
    assert "textarea.bw-input" in _COMPILED_CSS
    idx = _COMPILED_CSS.index("textarea.bw-input")
    chunk = _COMPILED_CSS[idx : idx + 280]
    assert "block-size:auto" in chunk.replace(" ", "")
    assert "min-block-size:" in chunk


def test_compiled_css_stacks_scorecard_below_app_breakpoint() -> None:
    # #525: span-2 must not open an implicit second track on phone.
    assert ".bw-scorecard__item--span-2" in _COMPILED_CSS
    assert "grid-column:auto" in _COMPILED_CSS.replace(" ", "") or "grid-column: auto" in _COMPILED_CSS


def test_bw_form_textarea_keeps_bw_input_and_rows() -> None:
    out = Template("{% load brickwork_forms %}{% bw_form form %}").render(Context({"form": _MemoForm()}))
    assert 'rows="3"' in out
    assert 'class="bw-input"' in out
    assert "<textarea" in out


def test_docs_article_example_fills_site_header() -> None:
    from tests.test_examples import _EXAMPLE_CONTEXTS, _example_engine

    html = _example_engine().get_template("docs/article.html").render(Context(_EXAMPLE_CONTEXTS["docs/article.html"]))
    assert "bw-docs-site-header" in html
    assert "Northwind docs" in html


def test_landing_fixtures_use_real_tokens_and_inline_logos() -> None:
    from tests.test_examples import _EXAMPLE_CONTEXTS

    ctx = _EXAMPLE_CONTEXTS["marketing/landing.html"]
    assert len(ctx["logos"]) >= 3
    assert all(str(logo["src"]).startswith("data:image/svg+xml,") for logo in ctx["logos"])
    assert "surface-subtle" not in str(ctx["hero_media"])
    assert "surface-raised" in str(ctx["hero_media"])


def test_detail_example_danger_zone_is_a_card_not_a_full_bleed_button() -> None:
    from tests.test_examples import _EXAMPLE_CONTEXTS, _example_engine

    html = _example_engine().get_template("app/detail.html").render(Context(_EXAMPLE_CONTEXTS["app/detail.html"]))
    assert 'class="bw-card"' in html
    assert "danger-zone-heading" in html
    assert html.index("bw-card") < html.index("Void invoice")
