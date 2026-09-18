"""Render tests for marketing ``_methods.html`` (#675)."""

from __future__ import annotations

from django.template import Context, Template


def _include(**ctx: object) -> str:
    keys = " ".join(f"{k}={k}" for k in ctx)
    return Template("{% include 'brickwork_marketing/components/_methods.html' with " + keys + " %}").render(
        Context(ctx)
    )


def test_methods_with_items_renders_quiet_columns() -> None:
    html = _include(
        heading="Methods",
        items=[
            {
                "heading": "RECE",
                "stages": "Reach · Engage · Convert · Expand",
                "body": "The growth method.",
                "url": "/rece/",
                "link_label": "Read RECE",
            },
            {
                "heading": "PRIME",
                "stages": "Prime · Run · Inspect · Merge · Evolve",
                "body": "The delivery method.",
                "url": "/prime/",
                "link_label": "Read PRIME",
            },
        ],
    )
    assert "bw-section" in html
    assert "bw-methods-section" in html
    assert "bw-methods" in html
    assert html.count("bw-methods__item") == 2
    assert "bw-methods__name" in html
    assert "RECE" in html and "PRIME" in html
    assert "bw-methods__stages" in html
    assert "Reach · Engage · Convert · Expand" in html
    assert 'href="/rece/"' in html and 'href="/prime/"' in html
    assert "bw-methods__link" in html
    assert "Read RECE" in html and "Read PRIME" in html
    # Quiet columns: no feature-card chrome, no whole-column anchors.
    assert "bw-feature-card" not in html
    assert "bw-feature-grid" not in html
    assert html.count("<a ") == 2
    assert '<a class="bw-methods__item' not in html


def test_methods_empty_items_renders_heading_alone() -> None:
    html = _include(heading="Methods")
    assert "bw-methods-section__heading" in html
    assert "Methods" in html
    assert "bw-methods__item" not in html


def test_methods_fully_empty_renders_nothing() -> None:
    html = Template("{% include 'brickwork_marketing/components/_methods.html' %}").render(Context({}))
    assert "bw-methods" not in html
    assert "bw-section" not in html


def test_methods_omits_absent_optional_fields() -> None:
    html = _include(items=[{"heading": "Solo method", "body": "Just a name and body."}])
    assert "bw-methods__stages" not in html
    assert "bw-methods__link" not in html
    assert "<a " not in html
    assert "Solo method" in html
    assert "Just a name and body." in html


def test_methods_url_without_link_label_renders_no_link() -> None:
    html = _include(items=[{"heading": "RECE", "url": "/rece/"}])
    assert "bw-methods__link" not in html
    assert "<a " not in html
    assert "RECE" in html


def test_methods_link_label_without_url_renders_no_link() -> None:
    html = _include(items=[{"heading": "RECE", "link_label": "Read RECE"}])
    assert "bw-methods__link" not in html
    assert "<a " not in html
    assert "Read RECE" not in html
