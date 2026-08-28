"""{% bw_gauge %} contract tests (icvoss/django-brickwork VIZ-007 to VIZ-010).

Covers geometry (min/max/value clamping and percentage, the closed sm/md/lg
size vocabulary), threshold_bands resolution and its closed accent/success/
warning/danger token vocabulary, the gauge_label override seam (a trusted-
markup slot mirroring _stat.html's own sparkline context variable) and its
escaped default, and the shared data-visualisation encoding contract
(ADR-081): the arc is aria-hidden and carries no text of its own, geometry
never rides on an inline width: string, and no per-instance progressbar
semantics leak in (VIZ-015). The contract assertions themselves live in
``tests/_encoding_contract.py``, the same machinery test_ranked_list.py is
proven against, so the family shares one mechanism rather than each member
growing its own regex.
"""

from __future__ import annotations

import re

import pytest
from django.template import engines
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.functional import lazy
from django.utils.safestring import mark_safe

from tests._encoding_contract import (
    assert_bar_is_aria_hidden_and_empty,
    assert_no_progressbar_semantics,
    assert_text_nodes_are_not_aria_hidden,
    assert_text_nodes_carry_no_accessible_name_override,
    assert_text_survives_colour_and_style_stripped,
)


def _render(src: str = "{% bw_gauge value=value %}", **ctx: object) -> str:
    ctx.setdefault("value", 73)
    return engines["django"].from_string("{% load brickwork_components %}" + src).render(ctx)


def _dash_offset(html: str) -> float:
    match = re.search(r"--bw-gauge-dash-offset:\s*([0-9.]+)", html)
    assert match is not None, f"no --bw-gauge-dash-offset found in {html!r}"
    return float(match.group(1))


# --- the floor: an SVG ring plus a visible numeric percentage ---------------


def test_floor_is_a_gauge_with_visible_percentage_text() -> None:
    out = _render()
    assert '<div class="bw-gauge bw-gauge--md"' in out
    assert '<svg class="bw-gauge__svg" viewBox="0 0 100 100" role="img"' in out
    assert '<circle class="bw-gauge__track"' in out
    assert '<circle\n      class="bw-gauge__arc bw-gauge__arc--accent"' in out
    assert '<span class="bw-gauge__label">73%</span>' in out


def test_label_option_sets_the_aria_label() -> None:
    out = _render('{% bw_gauge value=value label="Storage used" %}')
    assert 'aria-label="Storage used"' in out


def test_label_omitted_renders_no_aria_label() -> None:
    out = _render()
    assert "aria-label" not in out


# --- min/max/value geometry: computed in Python, clamped into range --------


def test_default_range_is_zero_to_a_hundred() -> None:
    out = _render(value=25)
    assert '<span class="bw-gauge__label">25%</span>' in out


def test_custom_min_max_computes_the_percentage_of_the_range() -> None:
    # 150 of a 100-200 range is the 50% mark.
    out = _render("{% bw_gauge value=value min=100 max=200 %}", value=150)
    assert '<span class="bw-gauge__label">50%</span>' in out


def test_value_above_max_clamps_to_a_full_ring() -> None:
    out = _render(value=999)
    assert '<span class="bw-gauge__label">100%</span>' in out
    assert _dash_offset(out) == pytest.approx(0.0, abs=0.01)


def test_value_below_min_clamps_to_an_empty_ring() -> None:
    out = _render("{% bw_gauge value=value min=10 %}", value=-5)
    assert '<span class="bw-gauge__label">0%</span>' in out
    circumference_match = re.search(r"--bw-gauge-dash-array:\s*([0-9.]+)", out)
    assert circumference_match is not None
    assert _dash_offset(out) == pytest.approx(float(circumference_match.group(1)), abs=0.01)


def test_max_must_be_strictly_greater_than_min() -> None:
    with pytest.raises(TemplateSyntaxError, match="max"):
        _render("{% bw_gauge value=value min=10 max=5 %}")


def test_max_equal_to_min_is_rejected() -> None:
    with pytest.raises(TemplateSyntaxError, match="max"):
        _render("{% bw_gauge value=value min=10 max=10 %}")


def test_non_numeric_value_is_rejected() -> None:
    with pytest.raises(TemplateSyntaxError, match="value"):
        _render(value="not-a-number")


# --- size: the closed sm/md/lg vocabulary (VIZ-010) -------------------------


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_size_emits_its_modifier_class(size: str) -> None:
    out = _render('{% bw_gauge value=value size="' + size + '" %}')
    assert f"bw-gauge--{size}" in out


def test_size_rejects_anything_outside_the_closed_vocabulary() -> None:
    with pytest.raises(TemplateSyntaxError, match="size"):
        _render('{% bw_gauge value=value size="xl" %}')


# --- threshold_bands (VIZ-009): closed token vocabulary, COL-030 pairing ---


_BANDS = [
    {"max": 50, "token": "danger"},
    {"max": 80, "token": "warning"},
    {"max": 100, "token": "success"},
]


def test_threshold_bands_resolve_the_lowest_matching_band() -> None:
    out = _render("{% bw_gauge value=value threshold_bands=bands %}", value=30, bands=_BANDS)
    assert "bw-gauge__arc--danger" in out


def test_threshold_bands_resolve_across_the_boundary() -> None:
    out = _render("{% bw_gauge value=value threshold_bands=bands %}", value=60, bands=_BANDS)
    assert "bw-gauge__arc--warning" in out


def test_threshold_bands_at_the_exact_boundary_takes_that_band() -> None:
    out = _render("{% bw_gauge value=value threshold_bands=bands %}", value=50, bands=_BANDS)
    assert "bw-gauge__arc--danger" in out


def test_threshold_bands_past_every_max_takes_the_highest_band() -> None:
    out = _render("{% bw_gauge value=value threshold_bands=bands %}", value=100, bands=_BANDS)
    assert "bw-gauge__arc--success" in out


def test_threshold_bands_omitted_defaults_to_accent() -> None:
    out = _render()
    assert "bw-gauge__arc--accent" in out


def test_threshold_bands_empty_list_defaults_to_accent() -> None:
    out = _render("{% bw_gauge value=value threshold_bands=bands %}", bands=[])
    assert "bw-gauge__arc--accent" in out


def test_threshold_bands_rejects_a_non_list() -> None:
    with pytest.raises(TemplateSyntaxError, match="threshold_bands"):
        _render("{% bw_gauge value=value threshold_bands=bands %}", bands="not-a-list")


def test_threshold_bands_rejects_a_non_mapping_entry() -> None:
    with pytest.raises(TemplateSyntaxError, match="threshold_bands"):
        _render("{% bw_gauge value=value threshold_bands=bands %}", bands=["not-a-mapping"])


def test_threshold_bands_rejects_a_token_outside_the_closed_vocabulary() -> None:
    with pytest.raises(TemplateSyntaxError, match="token"):
        _render(
            "{% bw_gauge value=value threshold_bands=bands %}",
            bands=[{"max": 50, "token": "purple"}],
        )


def test_threshold_banded_value_always_carries_its_visible_numeric_label() -> None:
    # COL-030: a threshold colour must never ship without the paired VISIBLE
    # number, at every band, not merely the default accent case. Deliberately
    # NOT a literal '<span class="bw-gauge__label">73%</span>' substring
    # check: that only proves the string is present in the markup, never that
    # it is visible, so a component whose label is hidden entirely (an
    # aria-hidden/hidden/inert/display:none/visibility:hidden label, or the
    # number replaced by textless markup) would still satisfy a substring
    # needle. assert_text_survives_colour_and_style_stripped reads the actual
    # TEXT CONTENT of the bw-gauge__label element, excluding anything hidden
    # by any of those mechanisms on the element's own tag, a nested child, or
    # an ancestor (the same machinery test_ranked_list.py is proven against),
    # so a textless or self-hidden label fails here even though the number
    # still appears as a substring somewhere in the rendered markup.
    for value, expected_percent in ((10, "10"), (60, "60"), (95, "95")):
        out = _render("{% bw_gauge value=value threshold_bands=bands %}", value=value, bands=_BANDS)
        assert_text_survives_colour_and_style_stripped(out, expected_percent, text_classes=("bw-gauge__label",))


def test_threshold_banded_gauge_label_override_still_carries_visible_text() -> None:
    # Pins that a caller-supplied gauge_label cannot defeat the COL-030
    # guarantee above at any band: whichever band resolves, the label element
    # must carry SOME visible text (the caller's override, or the numeric
    # fallback when the override has none), never nothing.
    for value in (10, 60, 95):
        out = _render(
            "{% bw_gauge value=value threshold_bands=bands gauge_label=custom %}",
            value=value,
            bands=_BANDS,
            custom="On track",
        )
        assert_text_survives_colour_and_style_stripped(out, "On track", text_classes=("bw-gauge__label",))


# --- gauge_label (VIZ-008): a trusted-markup slot, escaped default ---------


def test_gauge_label_omitted_defaults_to_the_escaped_percentage() -> None:
    out = _render(value=42)
    assert '<span class="bw-gauge__label">42%</span>' in out


def test_gauge_label_default_is_ordinary_escaped_text_not_markup() -> None:
    # a plain (unmarked) string passed as gauge_label must render exactly as
    # any other Django context variable would: auto-escaped, never treated
    # as trusted markup merely because this seam accepts a SafeString.
    out = _render("{% bw_gauge value=value gauge_label=custom %}", custom="<script>steal()</script>")
    assert "<script>steal()</script>" not in out
    assert "&lt;script&gt;steal()&lt;/script&gt;" in out


def test_gauge_label_accepts_pre_rendered_safe_markup() -> None:
    # mirrors _stat.html's own sparkline seam: a caller-rendered, explicitly
    # mark_safe'd string is trusted and rendered verbatim.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        custom=mark_safe("<strong>42 of 100</strong>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label"><strong>42 of 100</strong></span>' in out


# --- COL-030 defect class: a truthy gauge_label with no VISIBLE text must --
# --- still fall back to the numeric percentage, never render blank --------


def test_gauge_label_none_falls_back_to_the_percentage() -> None:
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom=None)
    assert '<span class="bw-gauge__label">73%</span>' in out


def test_gauge_label_empty_string_falls_back_to_the_percentage() -> None:
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom="")
    assert '<span class="bw-gauge__label">73%</span>' in out


def test_gauge_label_whitespace_only_falls_back_to_the_percentage() -> None:
    # a whitespace-only string is truthy in Python: {% if gauge_label %}
    # alone would render an empty-looking label with no numeric fallback.
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom="   ")
    assert '<span class="bw-gauge__label">73%</span>' in out
    assert '<span class="bw-gauge__label">   </span>' not in out


def test_gauge_label_markup_with_no_text_content_falls_back_to_the_percentage() -> None:
    # mark_safe'd markup is also truthy, and may carry no text of its own;
    # the fallback decision is text CONTENT, not truthiness or markup-ness.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe("<span></span>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label">73%</span>' in out
    assert "<span></span>" not in out


def test_gauge_label_markup_with_text_renders_verbatim_never_falls_back() -> None:
    # the regression guard above must not overcorrect into stripping or
    # rejecting legitimate markup: a label WITH visible text renders the
    # caller's own markup exactly, unescaped, with no fallback.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe("<span>73%</span>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label"><span>73%</span></span>' in out


def test_gauge_label_plain_string_with_text_renders_verbatim_never_falls_back() -> None:
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom="On track")
    assert '<span class="bw-gauge__label">On track</span>' in out


# --- COL-030 defect class, round two: found by adversarial review of the ---
# --- fix above. Two further shapes are truthy, non-whitespace, and STILL --
# --- carry no text a sighted user can see. ----------------------------------


@pytest.mark.parametrize(
    "name,character",
    [
        ("zero-width space", "​"),
        ("zero-width non-joiner", "‌"),
        ("zero-width joiner", "‍"),
        ("byte order mark", "﻿"),
        ("word joiner", "⁠"),
    ],
)
def test_gauge_label_format_character_only_falls_back_to_the_percentage(name: str, character: str) -> None:
    # Unicode category Cf ("format"): renders as literally nothing on
    # screen, the same argument the nbsp (category Zs) handling already
    # makes one category over. .strip() alone does not remove these, unlike
    # an ordinary space or nbsp, which is why they survived the first fix.
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom=character)
    assert '<span class="bw-gauge__label">73%</span>' in out, f"{name} ({character!r}) did not fall back"


def test_gauge_label_format_character_mixed_with_real_text_still_renders_verbatim() -> None:
    # a format character ALONGSIDE real text must not itself trigger a
    # fallback: the rule is "no VISIBLE text at all", not "contains any
    # format character".
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom="​73",
    )
    assert '<span class="bw-gauge__label">​73</span>' in out


def test_gauge_label_svg_title_only_falls_back_to_the_percentage() -> None:
    # <title> inside <svg> is an ACCESSIBLE NAME, announced to a screen
    # reader and never rendered as on-screen text. django.utils.html.strip_tags
    # (this function's first-round mechanism) keeps an element's text content
    # while discarding only its tags, so it could not tell "73%" living
    # inside <title> apart from "73%" living in ordinary flow text: exactly
    # the user this guarantee protects (a sighted user who cannot distinguish
    # the arc colours) is not reached by an accessible name.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe("<svg><title>73%</title></svg>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label">73%</span>' in out
    # Read the rendered text content directly rather than trusting a
    # '>73%<' substring needle: '<title>73%</title>' also contains that
    # exact substring, so a substring check cannot tell the fallback from
    # the caller's own accessible-only markup still being present verbatim.
    assert "<svg>" not in out


def test_gauge_label_template_content_only_falls_back_to_the_percentage() -> None:
    # <template> content is the HTML5 "template contents": an inert
    # DocumentFragment that parsing alone never inserts into the rendered
    # document. Verified directly in Chromium (innerText="", height=0), not
    # merely reasoned from the tag name: a strip-and-scrape approach would
    # have kept this text exactly like the <title>/<svg> case above.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe("<template>73%</template>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label">73%</span>' in out
    assert "<template>" not in out


def test_gauge_label_template_content_mixed_with_real_text_still_renders_verbatim() -> None:
    # the guard above must not overcorrect: real visible text ALONGSIDE a
    # <template> must still render, with no fallback.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe("<template>hidden</template>73%"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label"><template>hidden</template>73%</span>' in out


def test_gauge_label_noscript_content_only_falls_back_to_the_percentage() -> None:
    # <noscript> content is inert TEXT, not markup, whenever the HTML5
    # parsing spec's "scripting flag" is enabled, which is the ordinary case
    # for a real browser with JavaScript on (this package's own target
    # audience). Verified directly in Chromium (innerText="", height=0):
    # only a scripting-disabled browser would ever show this text.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe("<noscript>73%</noscript>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label">73%</span>' in out
    assert "<noscript>" not in out


def test_gauge_label_noscript_content_mixed_with_real_text_still_renders_verbatim() -> None:
    # the guard above must not overcorrect: real visible text ALONGSIDE a
    # <noscript> must still render, with no fallback.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe("<noscript>hidden</noscript>73%"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label"><noscript>hidden</noscript>73%</span>' in out


def test_gauge_label_img_alt_only_falls_back_to_the_percentage() -> None:
    # alt text lives in an ATTRIBUTE, never a text node: an <img> with only
    # an alt carries no visible text of its own, whatever the alt text says.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe('<img alt="73%">'),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label">73%</span>' in out
    assert "<img" not in out


def test_gauge_label_aria_hidden_markup_only_falls_back_to_the_percentage() -> None:
    # text inside aria-hidden="true" is removed from the accessibility tree
    # and is exactly the shape tests/_encoding_contract.py's own hiding-
    # mechanism ladder checks on the RENDERED side of this component family;
    # the fallback decision must agree with that ladder rather than treating
    # hidden text as visible.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe('<span aria-hidden="true">73%</span>'),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label">73%</span>' in out


# --- regression pins: correctly VISIBLE shapes that must stay visible. -----
# --- Over-fixing (excluding text that IS on screen) is the direction -------
# --- nothing currently guards; these pin the boundary against a future ------
# --- widening of the non-visible set. ---------------------------------------


def test_gauge_label_option_text_is_visible_and_never_falls_back() -> None:
    # <option> is NOT in _GAUGE_LABEL_NON_VISIBLE_TEXT_TAGS: outside a
    # <select>, and even inside one, its text is real rendered content
    # (Chromium: innerText="OPTION", height=20.2 for a bare <option>73%
    # </option> fixture), unlike <title>/<template>/<noscript>. A future
    # "tidy the closed-form elements" pass must not fold this in.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe("<option>73%</option>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label"><option>73%</option></span>' in out


def test_gauge_label_role_presentation_text_is_visible_and_never_falls_back() -> None:
    # role="presentation" removes an element from the ACCESSIBILITY tree
    # (nothing is announced) but the element still PAINTS: it is the mirror
    # image of <title>, which is announced but never painted. COL-030
    # protects the SIGHTED user, so role="presentation" text counts as
    # visible, and aria-hidden/hidden (which do remove paint) remain the
    # only attribute-driven hides this function recognises.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe('<span role="presentation">73%</span>'),  # noqa: S308
    )
    assert '<span class="bw-gauge__label"><span role="presentation">73%</span></span>' in out


def test_gauge_label_combining_marks_are_visible_and_never_fall_back() -> None:
    # combining diacritical marks (Unicode category Mn, "mark, nonspacing")
    # render as visible glyphs stacked on the preceding base character; they
    # are not Cf ("format") and must not be swept up by the Cf-only-
    # remainder check that correctly discards zero-width/format characters.
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom="á̂̃")
    assert '<span class="bw-gauge__label">á̂̃</span>' in out


def test_gauge_label_input_value_attribute_is_not_a_text_node_and_falls_back() -> None:
    # an <input value="..."> carries its text in an ATTRIBUTE, never a text
    # NODE, exactly like <img alt="..."> above: whatever the value says, the
    # element has no visible text content of its own.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe('<input value="73%">'),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label">73%</span>' in out
    assert "<input" not in out


def test_gauge_label_nested_markup_with_real_text_renders_verbatim_never_falls_back() -> None:
    # the round-two guards above must not overcorrect into treating every
    # nested element as suspect: ordinary nested inline markup with real
    # visible text (not title/desc/script/style, not aria-hidden) still
    # renders verbatim, with no fallback.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe("<span><em><b>73%</b></em></span>"),  # noqa: S308 (test-authored trusted markup)
    )
    assert '<span class="bw-gauge__label"><span><em><b>73%</b></em></span></span>' in out


def test_gauge_label_plain_string_containing_tag_shaped_text_is_not_parsed_as_markup() -> None:
    # A plain (unmarked) string is never fed to the HTML parser the round-two
    # fix uses for TRUSTED markup: it is only ever going to be rendered as
    # auto-escaped text, whatever characters it contains, so tag-shaped text
    # such as "<script>" inside an ordinary caller-typed string must not be
    # read as a real element and discarded. Regression guard for a defect
    # this fix introduced and caught before landing: an earlier draft ran
    # every gauge_label, safe or not, through the tag-aware extractor, which
    # correctly discards a TRUSTED <script>'s text but wrongly did the same
    # to a plain string that merely contains that substring, forcing an
    # unwanted numeric fallback over the caller's own (soon to be escaped)
    # text.
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom="<script>steal()</script>")
    assert "<script>steal()</script>" not in out
    assert "&lt;script&gt;steal()&lt;/script&gt;" in out


def test_gauge_label_plain_zero_renders_verbatim_never_falls_back() -> None:
    # "0" is falsy-adjacent by convention in many languages but is real,
    # visible text: the guard must key off VISIBLE TEXT CONTENT, never a
    # second truthiness test in disguise.
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom="0")
    assert '<span class="bw-gauge__label">0</span>' in out


# --- COL-030 defect class, round three: a LAZY safe string. The isinstance --
# --- branch test itself was blind to a value that renders as markup while --
# --- failing isinstance(v, SafeString). -------------------------------------


def test_gauge_label_lazy_safe_markup_with_no_text_falls_back_to_the_percentage() -> None:
    # lazy(lambda: mark_safe(...), str)() (the shape gettext_lazy and similar
    # produce) is not itself a SafeString and carries no __html__ of its own,
    # but the TEMPLATE still renders it as unescaped markup once resolved:
    # the fallback decision must resolve laziness the same way the template
    # does, or the two disagree and a threshold-coloured arc ships with no
    # visible number, which is exactly the failure this whole guard exists
    # to prevent.
    lazy_label = lazy(lambda: mark_safe("<svg><title>73%</title></svg>"), str)()  # noqa: S308
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom=lazy_label)
    assert '<span class="bw-gauge__label">73%</span>' in out
    assert "<svg>" not in out


def test_gauge_label_lazy_safe_markup_with_text_renders_verbatim_never_falls_back() -> None:
    # the fix above must not overcorrect into treating every lazy value as
    # suspect: a lazily-wrapped safe string that DOES carry visible text
    # still renders the caller's own markup verbatim, unescaped, with no
    # fallback, and the SafeString marker must survive the resolution.
    lazy_label = lazy(lambda: mark_safe("<strong>On track</strong>"), str)()  # noqa: S308
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom=lazy_label)
    assert '<span class="bw-gauge__label"><strong>On track</strong></span>' in out


def test_gauge_label_lazy_plain_string_renders_verbatim_never_falls_back() -> None:
    # a lazily-wrapped PLAIN string (no mark_safe inside it) must still be
    # treated as plain, auto-escaped text, exactly as an ordinary plain
    # string is: resolving laziness must not accidentally promote a plain
    # value into the markup-parsing branch.
    lazy_label = lazy(lambda: "On track", str)()
    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom=lazy_label)
    assert '<span class="bw-gauge__label">On track</span>' in out


def test_gauge_label_html_only_object_without_mark_safe_is_not_treated_as_markup() -> None:
    # Deliberately NOT a hole, and pinned here so a future "fix" cannot
    # silently invert this: an object defining __html__ but never wrapped in
    # mark_safe or subclassing SafeString is escaped by Django's own template
    # variable rendering (render_value_in_context converts it with a bare
    # str(value) before conditional_escape ever runs, since it is not a str
    # subclass, which discards __html__ before conditional_escape could see
    # it), so this function must agree and decline to fall back: the escaped
    # repr text IS the visible text a sighted user sees.
    class HtmlOnly:
        def __html__(self) -> str:
            return "<svg><title>73%</title></svg>"

    out = _render("{% bw_gauge value=value gauge_label=custom %}", value=73, custom=HtmlOnly())
    assert "<svg>" not in out
    assert "&lt;" in out  # the object's escaped repr, not the fallback percentage
    assert '<span class="bw-gauge__label">73%</span>' not in out


# --- COL-030 defect class, round three: void elements (<br>, <img>, ...) ---
# --- never receive a matching handle_endtag, so a naive push-on-open, -----
# --- pop-on-close stack over-hides everything AFTER them. This fails in ----
# --- the SAFE direction (over-suppresses a caller's label) rather than -----
# --- the COL-030 direction (suppressing the number); tests below pin BOTH -
# --- that specific correctness bug AND the safe-direction property. -------


@pytest.mark.parametrize(
    "markup",
    [
        '<br aria-hidden="true">Visible text after',
        '<img aria-hidden="true" src="x">Ninety used',
        "<input hidden>Still visible",
        '<br aria-hidden="true"/>Visible after',
        '73% <br aria-hidden="true">',
    ],
)
def test_gauge_label_void_element_never_hides_text_that_follows_it(markup: str) -> None:
    # A void element (no closing tag by the HTML5 spec) never receives a
    # handle_endtag call from html.parser: pushing a hidden-state entry for
    # it in handle_starttag and relying on a later pop left the parser's
    # internal stack one entry too deep for the REST OF THE DOCUMENT, so
    # every sibling after a void element carrying aria-hidden/hidden was
    # wrongly excluded from "visible text", forcing an unwanted numeric
    # fallback over a perfectly good caller label.
    #
    # A literal substring check, deliberately, not
    # assert_text_survives_colour_and_style_stripped: that helper's own
    # _visible_text walker asserts every opened tag has a matching close (a
    # correct precondition for this component family's own OUTPUT, which
    # never emits a void element), and fails that precondition on markup
    # containing a genuine void element, which is exactly what this test
    # needs to render. The exact expected markup is fully known here (no
    # ambiguity about what SHOULD render), so asserting the caller's own
    # markup appears verbatim inside the label span is the correct
    # instrument, not a weaker stand-in for one: it also proves no fallback
    # occurred, since a fallback would replace this content entirely rather
    # than merely add to it.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe(markup),  # noqa: S308 (test-authored trusted markup)
    )
    assert f'<span class="bw-gauge__label">{markup}</span>' in out


def test_gauge_label_self_closed_non_void_tag_does_not_hide_text_that_follows_it() -> None:
    # An explicit self-close on a NON-void tag (<span aria-hidden="true"/>,
    # malformed but real markup a caller might still write) reaches
    # handle_startendtag, which the base HTMLParser class already answers
    # correctly by calling handle_starttag then handle_endtag in sequence:
    # this pins that the base class default is not accidentally shadowed or
    # broken by the void-element fix above.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe('<span aria-hidden="true"/>Visible after'),  # noqa: S308
    )
    assert '<span class="bw-gauge__label"><span aria-hidden="true"/>Visible after</span>' in out


@pytest.mark.parametrize(
    "markup",
    [
        "<br>73 after a break",
        '<span aria-hidden="true">x</span>73 real text',
        "<svg><title>73%",  # unclosed <title>: swallows the rest, errs toward the fallback
        "<svg><title><br>73%</title></svg>",  # void element inside title stays excluded
    ],
)
def test_gauge_label_void_element_fix_does_not_invert_the_safe_direction(markup: str) -> None:
    # THE PROPERTY, not the individual cases: whatever a caller writes,
    # malformed or not, the component may legitimately discard the caller's
    # own label text (falling back to the number), but must NEVER render a
    # threshold-coloured arc with NO visible number at all, i.e. an empty
    # label. Every fixture above is deliberately built so the literal "73"
    # sits in the caller's OWN surviving visible text when the label is not
    # dropped (never inside markup this function treats as hidden/
    # non-visible, such as a hidden span or a <title>), so the same needle
    # "73" is also exactly what the numeric fallback renders when the label
    # IS dropped: asserting "73" survives the encoding-contract's
    # visible-text check proves the guarantee holds regardless of which of
    # the two legitimate outcomes (caller text kept, or fallback used)
    # happened for that particular case, without this test needing to know
    # or assert which one occurred.
    #
    # A fixture combining "73" with a void element is deliberately NOT
    # included here: assert_text_survives_colour_and_style_stripped's own
    # _visible_text walker asserts every opened tag has a matching close (see
    # test_gauge_label_void_element_never_hides_text_that_follows_it's own
    # comment), so it cannot be fed void-element markup at all; that fixture
    # shape is already covered precisely by the dedicated test above instead.
    out = _render(
        "{% bw_gauge value=value gauge_label=custom %}",
        value=73,
        custom=mark_safe(markup),  # noqa: S308 (test-authored trusted markup)
    )
    assert_text_survives_colour_and_style_stripped(out, "73", text_classes=("bw-gauge__label",))


# --- data attribute passthrough ---------------------------------------------


def test_data_attrs_render_on_the_gauge_root() -> None:
    out = _render("{% bw_gauge value=value data=data %}", data={"data-testid": "storage-gauge"})
    assert 'class="bw-gauge bw-gauge--md" data-testid="storage-gauge"' in out


def test_gauge_root_is_a_div_not_a_span() -> None:
    # the label span nests INSIDE the root: a <span> root would collide with
    # tests/_encoding_contract.py's own documented "leaf tag" assumption for
    # same-tag element matching (_find_elements is not a nested-tag parser),
    # so the root is deliberately a <div>, matching _stat.html's own root
    # element choice for exactly this reason.
    out = _render()
    assert out.lstrip().startswith('<div class="bw-gauge')
    assert out.rstrip().endswith("</div>")


# --- encoding contract (ADR-081): shared with every viz family member ------


def test_arc_and_track_are_aria_hidden_and_carry_no_visible_text_of_their_own() -> None:
    out = _render()
    assert_bar_is_aria_hidden_and_empty(out, bar_class="bw-gauge__arc", tag="circle", expected_count=1)
    assert_bar_is_aria_hidden_and_empty(out, bar_class="bw-gauge__track", tag="circle", expected_count=1)


def test_no_progressbar_role_leaks_onto_the_gauge_root() -> None:
    # VIZ-015: a gauge here is one already-resolved reading, not a live task
    # tracked toward completion, so it deliberately carries none of
    # _progress.html's own progressbar vocabulary.
    out = _render()
    assert_no_progressbar_semantics(out, component_tag="div", component_class="bw-gauge")


def test_label_text_element_is_never_hidden_from_the_accessibility_tree() -> None:
    out = _render()
    assert_text_nodes_are_not_aria_hidden(out, text_classes=("bw-gauge__label",), expected_count=1)


def test_label_text_element_carries_no_accessible_name_override() -> None:
    out = _render()
    assert_text_nodes_carry_no_accessible_name_override(out, text_classes=("bw-gauge__label",))


def test_dash_offset_is_a_bare_unitless_number_never_a_percent_or_px_string() -> None:
    # This component's geometry is real SVG user-space units (stroke-dasharray/
    # -dashoffset), not the 0-100-riding-a-calc() convention _progress.html and
    # _ranked_list.html share, so assert_geometry_is_a_unitless_custom_property
    # does not apply verbatim (it specifically forbids a width: declaration on
    # the SAME element, which is not this component's own risk); this asserts
    # the equivalent property directly: both custom properties are bare
    # fixed-point numbers, and neither a %, "px", nor any other unit ever rides
    # along, so the arc's geometry stays inspectable data rather than opaque
    # layout, matching the family's shared "safe by construction" contract.
    out = _render(value=37)
    style_match = re.search(r'<circle\s+class="bw-gauge__arc[^"]*"[^>]*style="([^"]+)"', out)
    assert style_match is not None, f"no bw-gauge__arc style attribute found in {out!r}"
    style_value = style_match.group(1)
    dash_array_match = re.search(r"--bw-gauge-dash-array:\s*([^;]+)", style_value)
    dash_offset_match = re.search(r"--bw-gauge-dash-offset:\s*([^;]+)", style_value)
    assert dash_array_match is not None
    assert dash_offset_match is not None
    for raw_value in (dash_array_match.group(1).strip(), dash_offset_match.group(1).strip()):
        assert re.fullmatch(r"-?\d+\.\d{2}", raw_value), (
            f"{raw_value!r} is not a bare fixed-2dp unitless number: a %/px suffix would mean the "
            "arc's geometry rode on a unit rather than a plain figure"
        )
    assert "width:" not in style_value


# --- documented composition: gauge markup dropped into _stat.html's own ---
# --- sparkline seam (a claim in bw_gauge's own docstring, executed here) ---


def test_documented_stat_tile_composition_actually_renders() -> None:
    # _stat.html's sparkline context variable accepts any pre-rendered safe
    # markup (its own contract, mirrored by bw_gauge's gauge_label docstring
    # above): a gauge is exactly the kind of compact visual this seam is for.
    # A documented composition that only ever lived in prose, never executed,
    # is how a sibling component shipped a docstring example that raised
    # TemplateSyntaxError; this proves the claim by rendering it.
    gauge_markup = (
        engines["django"]
        .from_string('{% load brickwork_components %}{% bw_gauge value=73 size="sm" label="Storage used" %}')
        .render({})
    )
    out = render_to_string(
        "brickwork/components/_stat.html",
        {
            "label": "Storage",
            "value": "73%",
            "sparkline": mark_safe(gauge_markup),  # noqa: S308 (test-authored trusted markup)
        },
    )
    assert 'class="bw-stat__sparkline"' in out
    assert 'class="bw-gauge bw-gauge--sm"' in out
    assert '<span class="bw-gauge__label">73%</span>' in out
