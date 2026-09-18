"""Render tests for marketing ``_case_list.html`` (#674)."""

from __future__ import annotations

from django.template import Context, Template


def _include(**ctx: object) -> str:
    keys = " ".join(f"{k}={k}" for k in ctx)
    return Template("{% include 'brickwork_marketing/components/_case_list.html' with " + keys + " %}").render(
        Context(ctx)
    )


def test_case_list_with_items_renders_ruled_rows() -> None:
    html = _include(
        heading="Selected work",
        items=[
            {
                "result": "3.2x",
                "heading": "Receivables cycle",
                "body": "Median days-to-cash after the chase sequence shipped.",
                "url": "/work/receivables/",
            },
            {
                "result": "14 days",
                "heading": "Onboarding",
                "body": "Time from signup to first reconciled month.",
            },
        ],
    )
    assert "bw-section" in html
    assert "bw-section__inner" in html
    assert "bw-case-list-section" in html
    assert "<ul" in html and "bw-case-list" in html
    assert "bw-case-list__result" in html
    assert "3.2x" in html
    assert "14 days" in html
    assert "Receivables cycle" in html
    assert "Onboarding" in html
    assert 'href="/work/receivables/"' in html
    assert "bw-case-list__row--link" in html
    assert "bw-case-list__item--result" in html
    assert "bw-feature-card" not in html


def test_case_list_empty_items_renders_intro_alone() -> None:
    html = _include(heading="Selected work")
    assert "bw-case-list-section__heading" in html
    assert "Selected work" in html
    assert "bw-case-list__item" not in html


def test_case_list_fully_empty_renders_nothing() -> None:
    html = Template("{% include 'brickwork_marketing/components/_case_list.html' %}").render(Context({}))
    assert "bw-case-list" not in html
    assert "bw-section" not in html


def test_case_list_omits_absent_optional_fields() -> None:
    html = _include(items=[{"heading": "Plain case", "body": "No figure, no link."}])
    assert "bw-case-list__result" not in html
    assert "bw-case-list__item--result" not in html
    assert "bw-case-list__row--link" not in html
    assert "<a " not in html
    assert "Plain case" in html


def test_case_list_linked_row_aria_label_overrides_accessible_name() -> None:
    html = _include(
        items=[
            {
                "result": "2x",
                "heading": "Throughput",
                "body": "Tickets closed per week.",
                "url": "/work/throughput/",
                "aria_label": "Read the throughput case study",
            }
        ]
    )
    assert 'aria-label="Read the throughput case study"' in html


def test_case_list_aria_label_without_url_is_ignored() -> None:
    html = _include(
        items=[
            {
                "heading": "Unlinked",
                "body": "Still a note.",
                "aria_label": "Should not appear",
            }
        ]
    )
    assert "aria-label" not in html
    assert "Should not appear" not in html
