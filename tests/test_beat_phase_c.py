"""Beat Phase C variant depth (icvoss/django-brickwork#543)."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

_ROOT = Path(__file__).resolve().parent.parent
_DIST_CSS = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist" / "brickwork.css"


def _render(path: str, **ctx: object) -> str:
    return render_to_string(path, ctx)


# --- features -----------------------------------------------------------------


def test_feature_rows_render_items() -> None:
    media = mark_safe('<svg aria-hidden="true"></svg>')
    out = _render(
        "brickwork_marketing/components/_feature_rows.html",
        heading="Capabilities",
        items=[{"heading": "Reminders", "body": "On a schedule.", "media": media}],
    )
    assert "bw-feature-rows" in out
    assert "bw-feature-row__title" in out
    assert "Reminders" in out
    assert "<svg" in out


def test_feature_list_ticks_strings() -> None:
    out = _render(
        "brickwork_marketing/components/_feature_list.html",
        heading="Included",
        items=["Unlimited invoices", "Automatic reminders"],
    )
    assert "bw-feature-list" in out
    assert "Unlimited invoices" in out
    assert out.count("bw-feature-list__item") == 2


# --- CTA siblings -------------------------------------------------------------


def test_cta_split_requires_heading() -> None:
    assert "bw-cta-split" not in _render("brickwork_marketing/components/_cta_split.html")


def test_cta_split_renders_actions() -> None:
    out = _render(
        "brickwork_marketing/components/_cta_split.html",
        heading="Try the demo",
        body="Import a CSV.",
        primary_cta_label="Run",
        primary_cta_href="/demo/",
    )
    assert "bw-cta-split" in out
    assert 'href="/demo/"' in out


def test_cta_bleed_inverse_band() -> None:
    out = _render(
        "brickwork_marketing/components/_cta_bleed.html",
        heading="Start this month",
        primary_cta_label="Sign up",
        primary_cta_href="/signup/",
        secondary_cta_label="Pricing",
        secondary_cta_href="/pricing/",
    )
    assert "bw-cta-bleed" in out
    assert "bw-section" in out
    assert "bw-section--bleed" in out
    assert "bw-cta-bleed__link" in out
    assert 'href="/pricing/"' in out


# --- pricing comparison -------------------------------------------------------


def test_pricing_comparison_yes_no_and_text_cells() -> None:
    out = _render(
        "brickwork_marketing/components/_pricing_comparison.html",
        heading="Compare",
        plans=["Solo", "Team"],
        rows=[
            {"label": "Users", "cells": ["1", "10"]},
            {"label": "Reminders", "cells": [{"included": True}, {"included": False}]},
        ],
    )
    assert "bw-comparison-table__table" in out
    assert "bw-comparison-table__yes" in out
    assert "bw-comparison-table__no" in out
    assert "Included" in out
    assert "Not included" in out
    assert "Users" in out


# --- empty_state / page_header / table / list / modal -------------------------


def test_empty_state_plain_surface() -> None:
    out = _render(
        "brickwork/components/_empty_state.html",
        heading="Nothing here",
        body="Add a record.",
        surface="plain",
    )
    assert "bw-empty-state--surface-plain" in out


def test_empty_state_invalid_surface_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="surface"):
        _render(
            "brickwork/components/_empty_state.html",
            heading="X",
            body="Y",
            surface="raised",
        )


def test_page_header_tint_surface() -> None:
    out = _render("brickwork/components/_page_header.html", title="Invoices", surface="tint")
    assert "bw-page-header--surface-tint" in out


def test_data_table_compact_density() -> None:
    out = _render(
        "brickwork/components/_data_table.html",
        table_id="t1",
        columns=[{"label": "Name"}],
        rows=[{"id": "1", "cells": ["Ada"]}],
        density="compact",
    )
    assert "bw-data-table-wrap--density-compact" in out


def test_list_item_compact_density() -> None:
    out = _render(
        "brickwork/components/_list_item.html",
        title="Row",
        density="compact",
    )
    assert "bw-list-item--density-compact" in out


def test_modal_header_recipe_muted() -> None:
    out = _render(
        "brickwork/components/_modal.html",
        title="Confirm",
        header_recipe="muted",
        footer_recipe="actions",
    )
    assert "bw-modal--header-muted" in out
    assert "bw-modal__header--muted" in out
    assert "bw-modal--footer-actions" in out


def test_modal_invalid_header_recipe_raises() -> None:
    with pytest.raises(TemplateSyntaxError, match="header_recipe"):
        _render("brickwork/components/_modal.html", title="X", header_recipe="accent")


def test_phase_c_css_ships_new_modifiers() -> None:
    css = _DIST_CSS.read_text(encoding="utf-8")
    assert ".bw-empty-state--surface-plain" in css
    assert ".bw-page-header--surface-tint" in css
    assert ".bw-data-table-wrap--density-compact" in css
    assert ".bw-list-item--density-compact" in css
    assert ".bw-modal__header--muted" in css
    assert ".bw-feature-rows" in css
    assert ".bw-cta-split" in css
    assert ".bw-cta-bleed" in css
    assert ".bw-comparison-table__table" in css
    assert ".bw-pricing-comparison__table" in css
