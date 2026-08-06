"""Direct render tests for _data_table.html's bulk-selection mode (#54),
the sticky/scroll-container header, and the responsive stack mode, plus the
list_item filter (brickwork_components.py) and _bulk_actions_bar.html.

Covers the selection contract (checkbox name/value/labels, the header
select-all carrying no submit value of its own), the CSS-only sticky/stack
hooks, and the always-rendered bulk-actions bar. A table WITHOUT
selectable=True must render with no checkbox column at all (the regression
guard for test_data_table.py's base variant, confirmed separately in
test_data_table.py itself).
"""

from __future__ import annotations

from django.template.loader import render_to_string

from brickwork.templatetags.brickwork_components import list_item

_COLUMNS = [
    {"label": "Name", "sortable": False},
    {"label": "Status", "sortable": False},
]
_ROWS = [
    {"id": 1, "cells": ["Widget", "Active"]},
    {"id": 2, "cells": ["Gizmo", "Draft"]},
]


def _render(**ctx) -> str:
    return render_to_string("brickwork/components/_data_table.html", ctx)


# --- selectable=True: the checkbox column -----------------------------------


def test_selectable_adds_a_leading_checkbox_column() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS, selectable=True)
    assert "bw-data-table__th--select" in out
    assert "bw-data-table__td--select" in out
    assert out.count("data-bw-row-select") == 2


def test_row_checkbox_carries_name_selected_and_row_id_value() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS, selectable=True)
    assert 'name="selected" value="1"' in out
    assert 'name="selected" value="2"' in out


def test_row_checkbox_has_a_visually_hidden_label() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS, selectable=True)
    assert 'for="gadgets-row-1-select"' in out
    assert 'id="gadgets-row-1-select"' in out
    # the visually-hidden label text ("Select row 1")
    assert "Select row 1" in out


def test_select_all_checkbox_is_present_and_labelled() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS, selectable=True)
    assert 'id="gadgets-select-all"' in out
    assert 'for="gadgets-select-all"' in out
    assert "Select all rows" in out
    assert "data-bw-select-all" in out


def test_select_all_checkbox_carries_no_name_attribute() -> None:
    # the header select-all must never pollute request.POST.getlist("selected")
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS, selectable=True)
    select_all_start = out.index("data-bw-select-all")
    # walk back to the enclosing <input ...> tag and forward to its close
    tag_start = out.rindex("<input", 0, select_all_start)
    tag_end = out.index(">", select_all_start)
    select_all_tag = out[tag_start : tag_end + 1]
    assert "name=" not in select_all_tag


def test_table_without_selectable_has_no_checkbox_column() -> None:
    # regression guard: the base (non-selectable) render carries none of the
    # selection markup at all
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS)
    assert "bw-data-table__th--select" not in out
    assert "bw-data-table__td--select" not in out
    assert "data-bw-row-select" not in out
    assert "data-bw-select-all" not in out
    assert 'name="selected"' not in out


def test_selectable_is_ignored_in_definition_variant() -> None:
    rows = [{"label": "Slug", "value": "acme"}]
    out = _render(table_id="facts", variant="definition", rows=rows, selectable=True)
    assert "data-bw-row-select" not in out
    assert "data-bw-select-all" not in out


# --- sticky header / scroll container ---------------------------------------


def test_sticky_header_adds_the_sticky_wrap_class() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS, sticky_header=True)
    assert "bw-data-table-wrap--sticky" in out


def test_without_sticky_header_no_sticky_class() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS)
    assert "bw-data-table-wrap--sticky" not in out


# --- responsive stack mode ---------------------------------------------------


def test_responsive_stack_stamps_data_label_on_cells() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS, responsive="stack")
    assert 'data-label="Name"' in out
    assert 'data-label="Status"' in out
    assert "bw-data-table-wrap--stack" in out
    assert "bw-data-table--stack" in out


def test_responsive_scroll_default_has_no_data_label() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS)
    assert "data-label=" not in out
    assert "bw-data-table-wrap--stack" not in out
    assert "bw-data-table--stack" not in out


def test_responsive_scroll_explicit_matches_default() -> None:
    out = _render(table_id="gadgets", columns=_COLUMNS, rows=_ROWS, responsive="scroll")
    assert "data-label=" not in out
    assert "bw-data-table-wrap--stack" not in out


# --- list_item filter (brickwork_components.py) -----------------------------


def test_list_item_returns_the_element_at_index() -> None:
    assert list_item(["a", "b", "c"], 1) == "b"


def test_list_item_accepts_string_index_from_forloop_counter() -> None:
    # Django template forloop.counter0 arrives as an int already, but the
    # filter also accepts a numeric string, matching {{ list|slice }}'s
    # tolerance for either.
    assert list_item(["a", "b", "c"], "2") == "c"


def test_list_item_out_of_range_returns_empty_string() -> None:
    assert list_item(["a"], 5) == ""


def test_list_item_negative_index_out_of_declared_use_still_indexes() -> None:
    # Python list semantics: -1 is a valid index (last element). The filter
    # does not special-case negative indices, matching plain sequence access.
    assert list_item(["a", "b"], -1) == "b"


def test_list_item_non_numeric_index_returns_empty_string() -> None:
    assert list_item(["a", "b"], "not-a-number") == ""


def test_list_item_empty_sequence_returns_empty_string() -> None:
    assert list_item([], 0) == ""


# --- _bulk_actions_bar.html ---------------------------------------------------


def _render_bulk_bar(**ctx) -> str:
    from django.template import Context, Template

    source = (
        '{% extends "brickwork/components/_bulk_actions_bar.html" %}'
        "{% block bulk_actions_buttons %}"
        '<button type="submit" name="bulk_action" value="archive">Archive</button>'
        '<button type="submit" name="bulk_action" value="delete">Delete</button>'
        "{% endblock %}"
    )
    return Template(source).render(Context(ctx))


def test_bulk_actions_bar_renders_its_buttons_always() -> None:
    out = _render_bulk_bar()
    assert "Archive" in out and "Delete" in out
    # no-JS floor: never hidden by default
    assert "hidden" not in out


def test_bulk_actions_bar_has_a_live_count_region() -> None:
    out = _render_bulk_bar()
    assert "data-bw-selection-count" in out
    assert 'aria-live="polite"' in out
    assert "data-bw-selection-count-template" in out


def test_bulk_actions_bar_optional_select_all_link() -> None:
    out = _render_bulk_bar(select_all_href="/gadgets/?select_all=1")
    assert 'href="/gadgets/?select_all=1"' in out
    assert "Select all" in out


def test_bulk_actions_bar_without_select_all_href_omits_the_link() -> None:
    out = _render_bulk_bar()
    assert "bw-bulk-actions-bar__select-all" not in out
