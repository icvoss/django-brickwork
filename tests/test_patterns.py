"""Render tests for the three shipped page patterns (0.5.0, spec 04 section 4a).

AC-BW-076 / BR-BW-TPL-006: each pattern renders a complete page when a
consumer extends it with only the required context (every optional region
absent from the output, no placeholder chrome), and renders every documented
region in order when every block is filled. The named blocks are the
semver-public contract (BR-BW-TPL-001), so these tests drive the patterns the
way a consumer does: {% extends %} plus block overrides.
"""

from __future__ import annotations

from django.core.paginator import Paginator
from django.template import Context, Template
from django.template.loader import render_to_string

_COLUMNS = [
    {"label": "Name", "sortable": False},
    {"label": "Status", "sortable": False},
]
_ROWS = [
    {"id": 1, "cells": ["Widget", "Active"]},
    {"id": 2, "cells": ["Gizmo", "Draft"]},
]
_FACTS = [
    {"label": "Slug", "value": "acme"},
    {"label": "Created", "value": "2026-07-31"},
]


def _render(template: str, **ctx: object) -> str:
    return render_to_string(template, ctx)


def _extend(parent: str, blocks: str, **ctx: object) -> str:
    return Template("{% extends '" + parent + "' %}" + blocks).render(Context(ctx))


def _assert_complete_document(html: str) -> None:
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "<html" in html and "</html>" in html
    assert 'id="bw-main"' in html


# --- patterns/list.html -----------------------------------------------------


def test_list_with_only_title_renders_a_complete_working_page() -> None:
    html = _render("brickwork/patterns/list.html", title="Widgets")
    _assert_complete_document(html)
    assert "Widgets" in html  # the page_header default wired from title
    assert "bw-card" in html  # the table card default
    assert "bw-empty-state" in html  # STA-001 via _data_table's own empty handling
    assert "bw-filter-bar" not in html  # optional region renders nothing
    assert "bw-pagination" not in html  # no page_obj -> no controls


def test_list_default_body_wires_rows_and_columns_into_a_table_card() -> None:
    html = _render("brickwork/patterns/list.html", title="Widgets", columns=_COLUMNS, rows=_ROWS)
    assert "Widget" in html and "Gizmo" in html
    assert html.index("bw-card") < html.index("bw-data-table")


def test_list_pagination_defaults_from_page_obj() -> None:
    page_obj = Paginator(list(range(25)), 10).page(1)
    html = _render("brickwork/patterns/list.html", title="Widgets", page_obj=page_obj)
    assert "bw-pagination" in html


def test_list_pagination_renders_nothing_at_one_page() -> None:
    # STA-014, inherited unchanged from _pagination.html.
    page_obj = Paginator(list(range(5)), 10).page(1)
    html = _render("brickwork/patterns/list.html", title="Widgets", page_obj=page_obj)
    assert "bw-pagination" not in html


def test_list_every_region_filled_renders_in_documented_order() -> None:
    html = _extend(
        "brickwork/patterns/list.html",
        "{% block filter_bar %}FILTER-SENTINEL{% endblock %}"
        "{% block list_body %}BODY-SENTINEL{% endblock %}"
        "{% block list_pagination %}PAGINATION-SENTINEL{% endblock %}",
        title="Widgets",
    )
    positions = [
        html.index("Widgets"),
        html.index("FILTER-SENTINEL"),
        html.index("BODY-SENTINEL"),
        html.index("PAGINATION-SENTINEL"),
    ]
    assert positions == sorted(positions), f"list regions out of documented order: {positions}"


def test_list_body_override_replaces_the_default_table_card() -> None:
    # The documented non-table escape hatch: override the whole block while
    # keeping the header/filter/pagination scaffolding.
    html = _extend(
        "brickwork/patterns/list.html",
        "{% block list_body %}CARD-GRID-SENTINEL{% endblock %}",
        title="Widgets",
    )
    assert "CARD-GRID-SENTINEL" in html
    assert "bw-card" not in html
    assert "bw-empty-state" not in html


# --- patterns/detail.html ---------------------------------------------------


def test_detail_with_title_and_rows_renders_the_facts_card_only() -> None:
    html = _render("brickwork/patterns/detail.html", title="Acme", rows=_FACTS)
    _assert_complete_document(html)
    assert "Acme" in html
    assert "bw-data-table--definition" in html  # the definition-variant shape
    assert '<th scope="row"' in html
    assert "acme" in html and "2026-07-31" in html
    # empty optional regions render nothing: no fabricated danger-zone warning
    assert "bw-alert" not in html


def test_detail_sections_and_danger_zone_render_in_order_when_filled() -> None:
    html = _extend(
        "brickwork/patterns/detail.html",
        "{% block detail_sections %}SECTIONS-SENTINEL{% endblock %}"
        "{% block detail_danger_zone %}DANGER-SENTINEL{% endblock %}",
        title="Acme",
        rows=_FACTS,
    )
    positions = [
        html.index("bw-data-table--definition"),
        html.index("SECTIONS-SENTINEL"),
        html.index("DANGER-SENTINEL"),
    ]
    assert positions == sorted(positions), f"detail regions out of documented order: {positions}"


def test_detail_facts_block_can_be_overridden() -> None:
    html = _extend(
        "brickwork/patterns/detail.html",
        "{% block detail_facts %}FACTS-SENTINEL{% endblock %}",
        title="Acme",
        rows=_FACTS,
    )
    assert "FACTS-SENTINEL" in html
    assert "bw-data-table--definition" not in html


# --- patterns/dashboard.html ------------------------------------------------


def test_dashboard_renders_with_no_context_at_all() -> None:
    # Required context: none; every block empties gracefully (AC-BW-076).
    html = _render("brickwork/patterns/dashboard.html")
    _assert_complete_document(html)
    assert "bw-stat__value" not in html  # no stat tile: the stat row is consumer-composed
    assert "bw-data-table-wrap" in html  # the activity table card default
    assert "bw-alert" not in html  # no placeholder chrome anywhere


def test_dashboard_regions_fill_in_documented_order() -> None:
    html = _extend(
        "brickwork/patterns/dashboard.html",
        "{% block dashboard_stats %}"
        '{% include "brickwork/components/_stat.html" with label="Total" value="42" %}'
        "{% endblock %}"
        "{% block dashboard_content %}CONTENT-SENTINEL{% endblock %}"
        "{% block dashboard_activity %}ACTIVITY-SENTINEL{% endblock %}",
        title="Dashboard",
    )
    positions = [
        html.index("bw-stat__value"),
        html.index("CONTENT-SENTINEL"),
        html.index("ACTIVITY-SENTINEL"),
    ]
    assert positions == sorted(positions), f"dashboard regions out of documented order: {positions}"


def test_dashboard_activity_default_wires_rows_and_columns() -> None:
    html = _render("brickwork/patterns/dashboard.html", columns=_COLUMNS, rows=_ROWS)
    assert "Widget" in html and "Gizmo" in html
    assert html.index("bw-card") < html.index("bw-data-table")


def test_dashboard_title_falls_back_to_no_page_header_chrome() -> None:
    # Omitting title is the consumer's own required-context miss on
    # _page_header, not a pattern failure: the page still renders.
    html = _render("brickwork/patterns/dashboard.html")
    _assert_complete_document(html)


# --- every pattern extends the app shell ------------------------------------


def test_patterns_render_through_the_app_shell() -> None:
    for template, ctx in (
        ("brickwork/patterns/list.html", {"title": "T"}),
        ("brickwork/patterns/detail.html", {"title": "T", "rows": _FACTS}),
        ("brickwork/patterns/dashboard.html", {}),
    ):
        html = _render(template, **ctx)
        assert "bw-app" in html and "bw-sidebar" in html and "bw-workspace" in html, (
            f"{template} does not render through shell/app.html"
        )
