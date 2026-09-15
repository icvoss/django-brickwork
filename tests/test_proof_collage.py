"""Render tests for marketing ``_proof_collage.html`` (#572)."""

from __future__ import annotations

from django.template import Context, Template
from django.utils.safestring import mark_safe


def _include(**ctx: object) -> str:
    keys = " ".join(f"{k}={k}" for k in ctx)
    return Template(
        "{% include 'brickwork_marketing/components/_proof_collage.html' with " + keys + " %}"
    ).render(Context(ctx))


def test_collage_layout_wraps_items_in_preview_frames() -> None:
    html = _include(
        heading="The kit is the product",
        layout="collage",
        items=[
            {"label": "Actions", "content": mark_safe('<button class="bw-btn bw-btn--primary">Go</button>')},
            {"label": "Status", "content": mark_safe('<span class="bw-badge">Live</span>')},
        ],
    )
    assert "bw-proof-collage--collage" in html
    assert "bw-preview-frame--card" in html
    assert "bw-btn--primary" in html
    assert "Actions" in html


def test_page_layout_uses_full_scale_frame() -> None:
    html = _include(
        layout="page",
        scrollable=True,
        items=[{"content": mark_safe("<article><h3>Pricing</h3></article>")}],
    )
    assert "bw-proof-collage--page" in html
    assert "bw-preview-frame--scrollable" in html
    assert "bw-preview-frame--card" not in html


def test_empty_items_with_heading_only_is_graceful() -> None:
    html = _include(heading="Proof")
    assert "bw-proof-collage__heading" in html
    assert "bw-proof-collage__grid" not in html


def test_completely_empty_collapses() -> None:
    html = Template("{% include 'brickwork_marketing/components/_proof_collage.html' %}").render(Context({}))
    assert "bw-proof-collage" not in html
    assert html.strip() == ""
