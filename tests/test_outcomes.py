"""Render tests for marketing ``_outcomes.html`` (#696)."""

from __future__ import annotations

from django.template import Context, Template


def _include(**ctx: object) -> str:
    keys = " ".join(f"{k}={k}" for k in ctx)
    return Template("{% include 'brickwork_marketing/components/_outcomes.html' with " + keys + " %}").render(
        Context(ctx)
    )


def test_outcomes_with_items_renders_quiet_columns() -> None:
    html = _include(
        heading="What I do",
        items=[
            {"heading": "Positioning", "body": "A clear offer."},
            {"heading": "Delivery", "body": "Shipped work."},
        ],
        url="/services/",
        link_label="All services",
    )
    assert "bw-section" in html
    assert "bw-outcomes-section" in html
    assert "bw-section__heading" in html
    assert "bw-outcomes" in html
    assert html.count("bw-outcomes__item") == 2
    assert "bw-outcomes__name" in html
    assert "Positioning" in html and "Delivery" in html
    assert "bw-outcomes__body" in html
    assert 'href="/services/"' in html
    assert "bw-outcomes-section__link" in html
    assert "All services" in html
    # Quiet columns: no feature-card chrome, no whole-column anchors, no
    # methods stages / per-column links.
    assert "bw-feature-card" not in html
    assert "bw-feature-grid" not in html
    assert "bw-methods" not in html
    assert html.count("<a ") == 1
    assert '<a class="bw-outcomes__item' not in html


def test_outcomes_empty_items_renders_heading_alone() -> None:
    html = _include(heading="What I do")
    assert "bw-section__heading" in html
    assert "What I do" in html
    assert "bw-outcomes__item" not in html


def test_outcomes_fully_empty_renders_nothing() -> None:
    html = Template("{% include 'brickwork_marketing/components/_outcomes.html' %}").render(Context({}))
    assert "bw-outcomes" not in html
    assert "bw-section" not in html


def test_outcomes_omits_absent_optional_body() -> None:
    html = _include(items=[{"heading": "Solo outcome"}])
    assert "bw-outcomes__body" not in html
    assert "Solo outcome" in html
    assert "<a " not in html


def test_outcomes_url_without_link_label_renders_no_foot_link() -> None:
    html = _include(heading="What I do", items=[{"heading": "A"}], url="/services/")
    assert "bw-outcomes-section__link" not in html
    assert "<a " not in html


def test_outcomes_link_label_without_url_renders_no_foot_link() -> None:
    html = _include(heading="What I do", items=[{"heading": "A"}], link_label="All services")
    assert "bw-outcomes-section__link" not in html
    assert "<a " not in html
    assert "All services" not in html


def test_outcomes_foot_link_alone_still_renders_section() -> None:
    html = _include(url="/services/", link_label="All services")
    assert "bw-outcomes-section" in html
    assert "bw-outcomes-section__link" in html
    assert "bw-outcomes__item" not in html
