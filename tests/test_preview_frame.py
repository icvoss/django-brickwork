"""Render tests for ``_preview_frame.html`` (ILL-026, #269)."""

from __future__ import annotations

from django.template import Context, Template
from django.utils.safestring import mark_safe


def _include(**ctx: object) -> str:
    keys = " ".join(f"{k}={k}" for k in ctx)
    return Template("{% include 'brickwork/components/_preview_frame.html' with " + keys + " %}").render(
        Context(ctx)
    )


def _extend(blocks: str, **ctx: object) -> str:
    return Template("{% extends 'brickwork/components/_preview_frame.html' %}" + blocks).render(Context(ctx))


def test_include_path_renders_surface_guarded_viewport_with_live_content() -> None:
    html = _include(
        content=mark_safe('<button class="bw-btn bw-btn--primary">Save</button>'),
        caption="Primary button",
    )
    assert 'class="bw-preview-frame"' in html
    assert "bw-preview-frame__viewport" in html
    assert "bw-btn--primary" in html
    assert "Primary button" in html
    assert 'role="region"' in html
    assert "tabindex" not in html


def test_card_scale_and_scrollable_modifiers() -> None:
    html = _include(
        content=mark_safe("<p>Specimen</p>"),
        scale="card",
        scrollable=True,
    )
    assert "bw-preview-frame--card" in html
    assert "bw-preview-frame--scrollable" in html
    assert 'tabindex="0"' in html


def test_extends_path_fills_preview_block() -> None:
    html = _extend(
        "{% block preview %}<span class='live-shell'>Shell</span>{% endblock %}",
        caption="Shell preview",
    )
    assert "live-shell" in html
    assert "Shell preview" in html


def test_compiled_css_keeps_surface_fill_not_raised() -> None:
    from pathlib import Path

    css = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "brickwork"
        / "static"
        / "brickwork"
        / "dist"
        / "brickwork.css"
    ).read_text(encoding="utf-8")
    # The guard is the package knowledge: surface, never raised.
    assert "bw-preview-frame__viewport" in css
    assert "--bw-color-surface)" in css or "--bw-color-surface;" in css
    # Product chrome remains a separate surface (raised) for marketing media.
    assert "bw-product-chrome" in css
