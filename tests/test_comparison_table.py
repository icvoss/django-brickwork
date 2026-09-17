"""comparison_table: first-class plan/capability matrix (#626)."""

from __future__ import annotations

from pathlib import Path

from django.template.loader import render_to_string

_DIST_CSS = (
    Path(__file__).resolve().parent.parent / "src" / "brickwork" / "static" / "brickwork" / "dist" / "brickwork.css"
)


def _render(template_name: str, **ctx: object) -> str:
    return render_to_string(template_name, ctx)


def test_comparison_table_yes_no_and_text_cells() -> None:
    out = _render(
        "brickwork/components/_comparison_table.html",
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
    assert "bw-comparison-table__col--highlighted" not in out


def test_comparison_table_highlights_by_zero_based_index() -> None:
    out = _render(
        "brickwork/components/_comparison_table.html",
        plans=["Solo", "Team", "Scale"],
        rows=[{"label": "Users", "cells": ["1", "10", "Unlimited"]}],
        highlighted=1,
    )
    assert out.count("bw-comparison-table__col--highlighted") == 2  # th + td
    assert "(Recommended)" in out
    # Team header carries the class; Solo does not appear with it adjacent.
    assert 'class="bw-comparison-table__col--highlighted"' in out


def test_comparison_table_highlights_by_digit_string_index() -> None:
    out = _render(
        "brickwork/components/_comparison_table.html",
        plans=["Solo", "Team"],
        rows=[{"label": "Users", "cells": ["1", "10"]}],
        highlighted="0",
    )
    assert "bw-comparison-table__col--highlighted" in out
    assert "(Recommended)" in out


def test_comparison_table_highlights_by_plan_name() -> None:
    out = _render(
        "brickwork/components/_comparison_table.html",
        plans=["Solo", "Team", "Scale"],
        rows=[{"label": "Users", "cells": ["1", "10", "Unlimited"]}],
        highlighted="Scale",
        highlighted_label="Best value",
    )
    assert out.count("bw-comparison-table__col--highlighted") == 2
    assert "(Best value)" in out
    assert "(Recommended)" not in out


def test_comparison_table_unknown_highlight_is_silent() -> None:
    out = _render(
        "brickwork/components/_comparison_table.html",
        plans=["Solo", "Team"],
        rows=[{"label": "Users", "cells": ["1", "10"]}],
        highlighted="Enterprise",
    )
    assert "bw-comparison-table__col--highlighted" not in out
    assert "(Recommended)" not in out


def test_marketing_pricing_comparison_wrapper_includes_core() -> None:
    out = _render(
        "brickwork_marketing/components/_pricing_comparison.html",
        heading="Compare",
        plans=["Solo", "Team"],
        rows=[
            {"label": "Reminders", "cells": [{"included": True}, {"included": False}]},
        ],
        highlighted="Team",
    )
    assert "bw-comparison-table__table" in out
    assert "bw-comparison-table__col--highlighted" in out
    assert 'id="bw-pricing-comparison-heading"' in out


def test_comparison_table_css_ships_bem_and_aliases() -> None:
    css = _DIST_CSS.read_text(encoding="utf-8")
    assert ".bw-comparison-table__table" in css
    assert ".bw-pricing-comparison__table" in css
    assert ".bw-comparison-table__col--highlighted" in css
