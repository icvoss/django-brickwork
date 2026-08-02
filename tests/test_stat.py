"""Direct render tests for _stat.html (0.5.0): the KPI tile contract.

Covers AC-BW-073 (label+value floor; a trend always carries an accessible
directional fallback, refined by trend_label), AC-BW-074 (directional meaning
survives with all colour styling stripped), and AC-BW-075 (the value uses
tabular numerals per the CSS contract).

Adopted ruling (spec 04 Stat section, BR-BW-TPL-007): _stat.html ALWAYS
renders a directional glyph plus a visually-hidden text fallback
("increased"/"decreased") whenever trend is present, and trend_label refines
the accessible text when given. Directional meaning therefore never rides on
colour alone BY CONSTRUCTION, so the enforcement mechanism AC-BW-073 left
open resolves to by-construction rendering, not a raise.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.template.loader import render_to_string

from brickwork.icons import get_icon

_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND = _ROOT / "frontend" / "src"

# Matches the fallback text inside a visually-hidden wrapper (any conventional
# screen-reader-only class name), so the fallback is verified as an accessible
# but not visually-doubled channel.
_SR_WRAPPED = r'class="[^"]*(?:sr-only|visually-hidden)[^"]*"[^>]*>\s*%s'


def _render(**ctx: object) -> str:
    return render_to_string("brickwork/components/_stat.html", ctx)


def _frontend_css() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(_FRONTEND.glob("*.css")))


# --- AC-BW-073: the label+value floor and the trend fallback ----------------


def test_label_and_value_only_renders_a_working_tile() -> None:
    out = _render(label="Revenue", value="1,234")
    assert "bw-stat" in out
    assert re.search(r'class="[^"]*bw-stat__label[^"]*"[^>]*>[^<]*Revenue', out)
    assert re.search(r'class="[^"]*bw-stat__value[^"]*"[^>]*>[^<]*1,234', out)
    assert "bw-stat__trend" not in out
    assert "increased" not in out and "decreased" not in out


def test_trend_up_renders_glyph_and_hidden_fallback_without_trend_label() -> None:
    out = _render(label="Active", value="12", trend="up")
    assert get_icon("arrow-up") in out, "no up glyph rendered for trend='up'"
    assert re.search(_SR_WRAPPED % "increased", out), (
        "trend='up' without trend_label must render a visually-hidden 'increased' fallback"
    )


def test_trend_down_renders_glyph_and_hidden_fallback_without_trend_label() -> None:
    out = _render(label="Draft", value="3", trend="down")
    assert get_icon("arrow-down") in out, "no down glyph rendered for trend='down'"
    assert re.search(_SR_WRAPPED % "decreased", out), (
        "trend='down' without trend_label must render a visually-hidden 'decreased' fallback"
    )


def test_trend_flat_renders_no_directional_arrow_or_words() -> None:
    out = _render(label="Archived", value="0", trend="flat")
    assert "bw-stat__trend" in out
    assert get_icon("arrow-up") not in out
    assert get_icon("arrow-down") not in out
    assert "increased" not in out and "decreased" not in out


def test_trend_label_refines_the_accessible_text() -> None:
    out = _render(label="Active", value="12", trend="up", trend_label="Up 12% on last month")
    assert "Up 12% on last month" in out
    # The hidden directional fallback stays even with a trend_label: a
    # consumer's label may not name the direction, and BR-BW-TPL-007 must
    # hold without trusting consumer copy (redundancy is the safe failure).
    assert "increased" in out


# --- AC-BW-074: directional meaning survives with colour stripped -----------


def test_directional_meaning_survives_with_all_colour_styling_stripped() -> None:
    out = _render(label="Active", value="12", trend="up", trend_label="Up 12% on last month")
    # Strip every class and style attribute (the only channels colour rides
    # on in this markup): the paired glyph and the text label must both
    # survive, so direction is never encoded by colour alone (BR-BW-TPL-007).
    stripped = re.sub(r'\s(?:class|style)="[^"]*"', "", out)
    assert "<svg" in stripped, "the directional glyph disappears when styling is stripped"
    assert "Up 12% on last month" in stripped, "the trend text disappears when styling is stripped"


def test_bare_trend_meaning_survives_with_all_colour_styling_stripped() -> None:
    out = _render(label="Active", value="12", trend="down")
    stripped = re.sub(r'\s(?:class|style)="[^"]*"', "", out)
    assert "<svg" in stripped
    assert "decreased" in stripped


# --- AC-BW-075: tabular numerals on the value -------------------------------


def test_value_element_carries_the_value_class() -> None:
    out = _render(label="Revenue", value="1,234")
    assert re.search(r'class="[^"]*bw-stat__value[^"]*"', out)


def test_value_css_declares_tabular_numerals() -> None:
    css = re.sub(r"/\*.*?\*/", "", _frontend_css(), flags=re.S)
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    value_rules = [body for sel, body in rules if "bw-stat__value" in sel]
    assert value_rules, "no .bw-stat__value rule in the authored component CSS"
    assert any("font-variant-numeric" in body and "tabular-nums" in body for body in value_rules), (
        ".bw-stat__value does not declare font-variant-numeric: tabular-nums"
    )


# --- the optional icon / href / loading / size arguments --------------------


def test_icon_renders_decoratively() -> None:
    out = _render(label="Widgets", value="2", icon="folder")
    assert get_icon("folder") in out
    assert 'aria-hidden="true"' in out


def test_href_wraps_the_tile_in_an_anchor() -> None:
    out = _render(label="Widgets", value="2", href="/widgets/")
    assert re.search(r'<a[^>]+class="[^"]*bw-stat', out), "href did not render an anchor tile"
    assert 'href="/widgets/"' in out


def test_without_href_the_tile_is_a_plain_div_never_a_fake_link() -> None:
    # VIZ-024: omitted href renders a non-interactive tile, never a
    # clickable-looking tile with no destination.
    out = _render(label="Widgets", value="2")
    assert re.search(r"<a\b", out) is None
    assert re.search(r'<div[^>]+class="[^"]*bw-stat', out)


def test_loading_shows_a_skeleton() -> None:
    out = _render(label="Widgets", value="2", loading=True)
    assert "bw-skeleton" in out


def test_size_maps_to_modifier_classes() -> None:
    # The modifier is emitted only when supplied: the default (md) tile
    # carries the bare bw-stat class.
    assert "bw-stat--sm" in _render(label="X", value="1", size="sm")
    assert "bw-stat--lg" in _render(label="X", value="1", size="lg")
    assert "bw-stat--" not in _render(label="X", value="1")


# --- sparkline (#60, 0.12.0) -------------------------------------------------


def test_sparkline_renders_the_caller_supplied_markup() -> None:
    # sparkline is documented as a pre-rendered SAFE string (the caller owns
    # escaping, matching row.cells / card block-filler content); mark_safe
    # mirrors what a real caller passes via the |safe filter.
    from django.utils.safestring import mark_safe

    out = _render(label="Revenue", value="1,234", sparkline=mark_safe("<svg><path d='M0 0'></path></svg>"))
    assert re.search(r'<div class="bw-stat__sparkline">\s*<svg><path', out)


def test_sparkline_omitted_renders_no_empty_div() -> None:
    out = _render(label="Revenue", value="1,234")
    assert "bw-stat__sparkline" not in out


def test_sparkline_ignored_while_loading() -> None:
    # loading=True renders the skeleton stand-in for the whole tile; the
    # sparkline (like label/value/trend) must not leak through.
    from django.utils.safestring import mark_safe

    out = _render(label="Revenue", value="1,234", sparkline=mark_safe("<svg></svg>"), loading=True)
    assert "bw-skeleton" in out
    assert "bw-stat__sparkline" not in out
    assert "<svg" not in out
