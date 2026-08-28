"""Direct render tests for _trend_indicator.html (VIZ-017).

VIZ-017 extracted _stat.html's own trend block (VIZ-002, BR-BW-TPL-007,
AC-BW-073/074) into a standalone partial so a table cell or scorecard can
reuse the same accessible trend contract without the whole KPI tile. Since
icvoss/django-brickwork#334, _stat.html itself {% include %}s this partial
rather than keeping its own inline copy, so the tests below mirror
test_stat.py's own trend assertions one-for-one against _trend_indicator.html
directly (the standalone-consumer contract: a table cell or scorecard
including this partial on its own gets the full accessible trend contract).

What the tests in this file do NOT prove any more: a "does _stat.html's own
render match _trend_indicator.html's own render" comparison is now
tautological, because _stat.html's trend row IS _trend_indicator.html's
render, reached via {% include %} rather than a second copy of the markup.
Comparing the two is comparing the partial against itself through two call
sites, which cannot fail short of Django's own {% include %} implementation
breaking. The real acceptance criterion for #334 (byte-identical _stat.html
output before and after the switch, across every documented trend case) is
covered instead by
test_stat_trend_output_is_unchanged_by_the_switch_to_include below, which
pins _stat.html's post-#334 output against the literal pre-#334 output,
captured by rendering the inline block that shipped up to and including
commit 65a4c78 (icvoss/django-brickwork#337, the last commit before #334)
outside the normal template loader. The only two differences are the
announced class rename (bw-stat__trend -> bw-trend, template header comment)
and insignificant inter-tag whitespace introduced by the {% include %}
template-file boundary (compared with Django's own whitespace collapsed);
the accessible glyph/hidden-text/visible-label markup, its ordering, and its
presence-or-absence per case are unchanged bytes.
"""

from __future__ import annotations

import re

import pytest
from django.template.loader import render_to_string

from brickwork.icons import get_icon

# Matches the fallback text inside a visually-hidden wrapper, mirroring
# test_stat.py's own pattern exactly.
_SR_WRAPPED = r'class="[^"]*(?:sr-only|visually-hidden)[^"]*"[^>]*>\s*%s'


def _render(**ctx: object) -> str:
    return render_to_string("brickwork/components/_trend_indicator.html", ctx)


# --- the documented usage example (header comment) must actually render -----


def test_documented_table_cell_usage_renders() -> None:
    from django.template import engines

    html = (
        engines["django"]
        .from_string(
            '{% include "brickwork/components/_trend_indicator.html" with trend="up" trend_label="12% on last month" %}'
        )
        .render({})
    )
    assert "bw-trend" in html
    assert "12% on last month" in html


# --- AC-BW-073: the trend fallback, mirroring test_stat.py's own cases ------


def test_trend_up_renders_glyph_and_hidden_fallback_without_trend_label() -> None:
    out = _render(trend="up")
    assert get_icon("arrow-up") in out, "no up glyph rendered for trend='up'"
    assert re.search(_SR_WRAPPED % "increased", out), (
        "trend='up' without trend_label must render a visually-hidden 'increased' fallback"
    )


def test_trend_down_renders_glyph_and_hidden_fallback_without_trend_label() -> None:
    out = _render(trend="down")
    assert get_icon("arrow-down") in out, "no down glyph rendered for trend='down'"
    assert re.search(_SR_WRAPPED % "decreased", out), (
        "trend='down' without trend_label must render a visually-hidden 'decreased' fallback"
    )


def test_trend_flat_renders_no_directional_arrow_or_words() -> None:
    out = _render(trend="flat")
    assert "bw-trend" in out
    assert get_icon("arrow-up") not in out
    assert get_icon("arrow-down") not in out
    assert "increased" not in out and "decreased" not in out


def test_trend_label_refines_the_accessible_text() -> None:
    out = _render(trend="up", trend_label="Up 12% on last month")
    assert "Up 12% on last month" in out
    # The hidden directional fallback stays even with a trend_label, matching
    # _stat.html's own redundancy-is-the-safe-failure rule (BR-BW-TPL-007).
    assert "increased" in out


def test_any_other_trend_value_takes_the_flat_treatment() -> None:
    # _stat.html's own {% if %}/{% elif %}/{% else %} ladder falls through to
    # the flat branch for any unrecognised value, with no raise: the
    # extraction must preserve that exact fallback rather than adding new
    # validation _stat.html never had.
    out = _render(trend="sideways")
    assert get_icon("minus") in out
    assert re.search(_SR_WRAPPED % "unchanged", out)


# --- colour channel: the bw-trend--<state> modifier class -------------------
#
# The three fallback tests above pin the glyph and hidden-text channels but
# never mention the modifier class, so a template that stopped emitting
# bw-trend--up/--down/--flat, or emitted the wrong one for a given trend,
# would leave every test above still green. These assertions pin the third
# channel directly and in the same render as the glyph and hidden text, so
# the "three redundant channels" claim (template header comment,
# changelog.d/trend-indicator.added.md) is verified together rather than
# only via the styling-stripped tests (which strip class/style entirely and
# so cannot see the modifier either) or only via the cross-template
# equivalence tests below (which only prove this partial agrees with
# _stat.html, not that either is correct against the absolute up/down/flat
# contract, and would stay green if both templates were wrong identically).


def test_trend_up_emits_the_up_modifier_class_with_glyph_and_hidden_text() -> None:
    out = _render(trend="up")
    assert 'class="bw-trend bw-trend--up"' in out
    assert get_icon("arrow-up") in out
    assert re.search(_SR_WRAPPED % "increased", out)


def test_trend_down_emits_the_down_modifier_class_with_glyph_and_hidden_text() -> None:
    out = _render(trend="down")
    assert 'class="bw-trend bw-trend--down"' in out
    assert get_icon("arrow-down") in out
    assert re.search(_SR_WRAPPED % "decreased", out)


def test_trend_flat_emits_the_flat_modifier_class_with_glyph_and_hidden_text() -> None:
    out = _render(trend="flat")
    assert 'class="bw-trend bw-trend--flat"' in out
    assert get_icon("minus") in out
    assert re.search(_SR_WRAPPED % "unchanged", out)


def test_up_and_down_modifier_classes_are_not_interchangeable() -> None:
    # A template that swapped the up/down branches of the modifier ladder
    # (while leaving the glyph and hidden-text ladders untouched) would pass
    # every fallback test above. This asserts the state class actually
    # differs per state and matches the trend it was rendered for, so such a
    # swap fails here even if it fails nowhere else.
    up_out = _render(trend="up")
    down_out = _render(trend="down")
    assert "bw-trend--up" in up_out and "bw-trend--down" not in up_out
    assert "bw-trend--down" in down_out and "bw-trend--up" not in down_out


# --- AC-BW-074: directional meaning survives with colour stripped -----------


def test_directional_meaning_survives_with_all_colour_styling_stripped() -> None:
    out = _render(trend="up", trend_label="Up 12% on last month")
    stripped = re.sub(r'\s(?:class|style)="[^"]*"', "", out)
    assert "<svg" in stripped, "the directional glyph disappears when styling is stripped"
    assert "Up 12% on last month" in stripped, "the trend text disappears when styling is stripped"


def test_bare_trend_meaning_survives_with_all_colour_styling_stripped() -> None:
    out = _render(trend="down")
    stripped = re.sub(r'\s(?:class|style)="[^"]*"', "", out)
    assert "<svg" in stripped
    assert "decreased" in stripped


# --- #334's own acceptance criterion: _stat.html unchanged by the switch ---
#
# _stat.html now {% include %}s _trend_indicator.html rather than rendering
# its own copy of the trend block, so comparing the two templates' output to
# each other (the shape the tests above this comment took prior to #334)
# would compare the partial's render against itself through two call sites:
# it cannot fail short of Django's {% include %} tag itself breaking. The
# real question #334 must answer is different: does _stat.html's OWN output
# still carry the same accessibility contract it carried before the switch?
#
# _GOLDEN_TREND_UP/_DOWN/_FLAT/_NONE below are the literal trend fragments
# _stat.html rendered from its inline block at commit 65a4c78 (the last
# commit before #334, icvoss/django-brickwork#337), captured by rendering
# that commit's _stat.html outside the normal template loader. They pin two
# things at once: the announced class rename (bw-stat__trend -> bw-trend,
# the only intentional difference, reasoned about in _stat.html's and
# _trend_indicator.html's own header comments) is applied to the golden
# strings before comparison, and insignificant inter-tag whitespace (the
# {% include %} template-file boundary adds newlines/indentation the inline
# block never had) is collapsed on both sides. Everything that carries
# meaning -- which glyph the SVG resolves to, the hidden fallback word, the
# visible trend_label text, element nesting and ordering, and whether the
# row renders at all -- is compared exactly, so a dropped guard, a swapped
# glyph, or a lost trend_label fails here even though {% include %} itself
# working correctly means the tautological old comparison could not have
# caught it.


def _apply_permitted_differences(golden: str) -> str:
    """Apply the ENUMERATED permitted differences to a pre-#334 golden.

    The acceptance criterion (icvoss/django-brickwork#334) is byte-identity
    with an explicit exception list, deliberately not a normalisation
    function: a list is a criterion, because anything not on it fails, while
    a normalisation grows silently whenever something else stops matching.

    Exactly two differences are permitted, and nothing else:

    1. The ``bw-trend`` class tokens are ADDED before the retained
       ``bw-stat__trend`` ones. Both families ship (#334 retains the alias
       and its modifiers), so the golden's own classes must still be present
       rather than renamed away.
    2. The newline-and-indent introduced at the ``{% include %}`` template
       boundary, and only there: the blank line before the closing tag of
       the trend row. Every other byte of whitespace is compared exactly,
       because whitespace at an include boundary is precisely where a
       faithless extraction would show up.
    """
    direction = "up" if "--up" in golden else "down" if "--down" in golden else "flat"
    with_alias = golden.replace(
        f'<span class="bw-stat__trend bw-stat__trend--{direction}">',
        f'<span class="bw-trend bw-trend--{direction} bw-stat__trend bw-stat__trend--{direction}">',
        1,
    )
    # Difference 2, named exactly and MEASURED rather than assumed: at the
    # include boundary the blank line before the row's closing tag carries
    # the includer's two-space indent, so "</span>\n\n</span>" becomes
    # "</span>\n  \n</span>". Anchored to that exact position and that exact
    # string, never a general whitespace collapse.
    return with_alias.replace("</span>\n\n</span>", "</span>\n  \n</span>", 1)


# Captured verbatim from commit 65a4c78's _stat.html (pre-#334), rendered
# with label="Active" value="12" and the trend/trend_label shown, using
# bw-stat__trend (renamed to bw-trend below before comparison, matching the
# one announced difference).
_GOLDEN_TREND_UP_WITH_LABEL = """
<span class="bw-stat__trend bw-stat__trend--up">
  <svg class="bw-icon" style="--bw-icon-size: var(--bw-component-icon-size-sm)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="var(--bw-component-icon-stroke-width, 2)" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 7-7 7 7" /> <path d="M12 19V5" /></svg>
  <span class="bw-visually-hidden">increased</span>
  <span>17 days faster</span>
</span>
"""

_GOLDEN_TREND_DOWN_NO_LABEL = """
<span class="bw-stat__trend bw-stat__trend--down">
  <svg class="bw-icon" style="--bw-icon-size: var(--bw-component-icon-size-sm)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="var(--bw-component-icon-stroke-width, 2)" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14" /> <path d="m19 12-7 7-7-7" /></svg>
  <span class="bw-visually-hidden">decreased</span>

</span>
"""

_GOLDEN_TREND_FLAT_NO_LABEL = """
<span class="bw-stat__trend bw-stat__trend--flat">
  <svg class="bw-icon" style="--bw-icon-size: var(--bw-component-icon-size-sm)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="var(--bw-component-icon-stroke-width, 2)" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14" /></svg>
  <span class="bw-visually-hidden">unchanged</span>

</span>
"""


@pytest.mark.parametrize(
    ("ctx", "golden"),
    [
        ({"trend": "up", "trend_label": "17 days faster"}, _GOLDEN_TREND_UP_WITH_LABEL),
        ({"trend": "down"}, _GOLDEN_TREND_DOWN_NO_LABEL),
        ({"trend": "flat"}, _GOLDEN_TREND_FLAT_NO_LABEL),
    ],
)
def test_stat_trend_output_is_unchanged_by_the_switch_to_include(ctx: dict[str, object], golden: str) -> None:
    out = render_to_string("brickwork/components/_stat.html", {"label": "Active", "value": "12", **ctx})
    match = re.search(r'<span class="bw-trend[^"]*">.*?</span>\s*</span>', out, re.DOTALL)
    assert match is not None, "no bw-trend fragment found in _stat.html's rendered output"
    assert match.group(0) == _apply_permitted_differences(golden).strip()


# --- the falsy trend guard: no data means no trend row, not "unchanged" -----
#
# _stat.html's include of _trend_indicator.html carries trend/trend_label
# straight through with no guard of its own, so this asserts directly on
# _stat.html's own output: no trend markup at all for None, "", 0, False,
# and the key absent entirely, so a dropped guard (in either template) fails
# here even though the tautological old comparison against
# _trend_indicator.html's own render could not have caught it.


@pytest.mark.parametrize("trend_value", [None, "", 0, False])
def test_falsy_trend_renders_no_trend_row_on_stat_html(trend_value: object) -> None:
    stat_out = render_to_string(
        "brickwork/components/_stat.html", {"label": "Active", "value": "12", "trend": trend_value}
    )
    assert "bw-trend" not in stat_out, f"_stat.html rendered a trend row for trend={trend_value!r}"


def test_absent_trend_key_renders_no_trend_row_on_stat_html() -> None:
    stat_out = render_to_string("brickwork/components/_stat.html", {"label": "Active", "value": "12"})
    assert "bw-trend" not in stat_out, "_stat.html rendered a trend row with the 'trend' key absent entirely"
