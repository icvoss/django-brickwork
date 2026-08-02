"""Direct render tests for _data_table.html's shapes and states.

Covers the record/definition variants, the clickable-row link (#10), the
definition-list mode (#18), and the empty/loading branches, by rendering the
template with context rather than driving a full page (the integration suite
covers the end-to-end server-side sort).
"""

from __future__ import annotations

from django.template.loader import render_to_string
from django.test import RequestFactory


def _render(request=None, **ctx) -> str:
    return render_to_string("brickwork/components/_data_table.html", ctx, request=request)


_COLUMNS = [
    {"label": "Name", "sortable": False},
    {"label": "Status", "sortable": False},
]
_ROWS = [
    {"id": 1, "cells": ["Widget", "Active"]},
    {"id": 2, "cells": ["Gizmo", "Draft"]},
]


# --- record variant (default) ---------------------------------------------


def test_records_render_rows_with_stable_ids() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS)
    assert 'id="gadgets-row-1"' in out
    assert 'id="gadgets-row-2"' in out
    assert "Widget" in out and "Draft" in out


def test_row_without_url_renders_no_link() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS)
    assert "bw-data-table__row-link" not in out
    assert "bw-data-table__row--linked" not in out


def test_selected_row_carries_the_selected_class() -> None:
    rows = [
        {"id": 1, "cells": ["Widget", "Active"], "selected": True},
        {"id": 2, "cells": ["Gizmo", "Draft"]},
    ]
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=rows)
    # only the selected row gets the modifier
    assert out.count("bw-data-table__row--selected") == 1
    selected_row = out[out.index('id="gadgets-row-1"') : out.index('id="gadgets-row-2"')]
    assert "bw-data-table__row--selected" in selected_row


# --- clickable rows (#10) --------------------------------------------------


def test_row_with_url_links_the_first_cell() -> None:
    rows = [{"id": 1, "cells": ["Widget", "Active"], "url": "/gadgets/1/"}]
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=rows)
    assert 'class="bw-data-table__row-link" href="/gadgets/1/"' in out
    assert "bw-data-table__row--linked" in out
    # only the FIRST cell is the link; the second cell is plain text
    assert ">Active<" in out


def test_only_the_first_cell_is_linked() -> None:
    rows = [{"id": 1, "cells": ["Widget", "Active"], "url": "/x/"}]
    out = _render(table_id="t", columns=_COLUMNS, rows=rows)
    # exactly one row link anchor, not one per cell
    assert out.count("bw-data-table__row-link") == 1


# --- definition-list mode (#18) -------------------------------------------


def test_definition_mode_renders_label_value_rows() -> None:
    rows = [
        {"label": "Slug", "value": "acme"},
        {"label": "Created", "value": "2026-07-31"},
    ]
    out = _render(table_id="facts", variant="definition", rows=rows)
    assert "bw-data-table--definition" in out
    # the label is a row header (scope=row), semantically a definition table
    assert '<th scope="row"' in out
    assert "Slug" in out and "acme" in out
    assert "Created" in out and "2026-07-31" in out


def test_definition_mode_has_no_column_headers_or_sort() -> None:
    rows = [{"label": "Slug", "value": "acme"}]
    out = _render(table_id="facts", variant="definition", rows=rows)
    assert "<thead" not in out
    assert "bw-data-table__sort" not in out
    assert 'scope="col"' not in out


def test_definition_mode_empty_shows_empty_state() -> None:
    out = _render(
        table_id="facts",
        variant="definition",
        rows=[],
        empty_heading="No facts",
        empty_body="Nothing to show.",
    )
    assert "bw-empty-state" in out
    assert "No facts" in out


# --- shared states ---------------------------------------------------------


def test_empty_records_shows_empty_state() -> None:
    out = _render(
        table_id="gadgets",
        columns=_COLUMNS,
        rows=[],
        empty_heading="No gadgets",
        empty_body="Create one.",
    )
    assert "bw-empty-state" in out
    assert "No gadgets" in out


def test_loading_shows_skeleton() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS, loading=True)
    assert "bw-data-table__skeleton" in out
    assert "bw-skeleton--row" in out


# --- derived sort toggle from sort_key + current_sort only (#23) ----------

_SORTABLE = [{"label": "Name", "sortable": True, "sort_key": "name"}]


def test_unsorted_column_first_click_sorts_ascending() -> None:
    # consumer supplies ONLY sort_key; no sort_key_desc / next_sort needed
    out = _render(table_id="t", columns=_SORTABLE, rows=_ROWS)
    assert 'href="?sort=name"' in out
    assert "aria-sort" not in out  # nothing sorted yet


def test_ascending_column_toggles_to_descending() -> None:
    out = _render(table_id="t", columns=_SORTABLE, rows=_ROWS, current_sort="name")
    assert 'aria-sort="ascending"' in out
    # the next click must go to the DESCENDING key, derived as -name
    assert 'href="?sort=-name"' in out


def test_descending_column_toggles_to_ascending() -> None:
    out = _render(table_id="t", columns=_SORTABLE, rows=_ROWS, current_sort="-name")
    assert 'aria-sort="descending"' in out
    # the next click returns to ascending
    assert 'href="?sort=name"' in out


def test_querystring_is_threaded_through_the_sort_link() -> None:
    out = _render(table_id="t", columns=_SORTABLE, rows=_ROWS, querystring="status=active")
    assert 'href="?sort=name&status=active"' in out


def test_explicit_next_sort_still_overrides_when_unsorted() -> None:
    # back-compat: a consumer may still pin the first-click target
    cols = [{"label": "Name", "sortable": True, "sort_key": "name", "next_sort": "-name"}]
    out = _render(table_id="t", columns=cols, rows=_ROWS)
    assert 'href="?sort=-name"' in out


# --- #41: request-aware querystring split (sort drops page, keeps filters) --


def test_sort_with_request_drops_page_and_keeps_filters_descending() -> None:
    # currently ascending on "name" -> next click sorts descending, page dropped
    req = RequestFactory().get("/?sort=name&page=3&status=active")
    out = _render(req, table_id="t", columns=_SORTABLE, rows=_ROWS, current_sort="name")
    assert "?sort=-name&amp;status=active" in out
    assert "page=" not in out


def test_sort_with_request_unsorted_to_ascending_drops_page_and_keeps_filters() -> None:
    # no current_sort -> first click sorts ascending, page still dropped
    req = RequestFactory().get("/?sort=name&page=3&status=active")
    out = _render(req, table_id="t", columns=_SORTABLE, rows=_ROWS)
    assert "?sort=name&amp;status=active" in out
    assert "page=" not in out


def test_sort_with_request_descending_to_ascending_drops_page_and_keeps_filters() -> None:
    # currently descending on "name" -> next click returns to ascending
    req = RequestFactory().get("/?sort=-name&page=3&status=active")
    out = _render(req, table_id="t", columns=_SORTABLE, rows=_ROWS, current_sort="-name")
    assert "?sort=name&amp;status=active" in out
    assert "page=" not in out


def test_sort_without_request_falls_back_to_raw_querystring_var() -> None:
    # regression guard: the request-free render contract is byte-identical to
    # the pre-#41 behaviour, no "&amp;" HTML-escaping from {% querystring %}.
    out = _render(table_id="t", columns=_SORTABLE, rows=_ROWS, querystring="status=active")
    assert 'href="?sort=name&status=active"' in out
    assert "&amp;" not in out
