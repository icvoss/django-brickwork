"""``{% bw_attr %}`` contract tests (ADR-097).

The single seam for every consumer value an include-only template places
into HTML attribute position: it emits a complete ``name="value"`` attribute
or nothing at all, in one of three modes (default escape, ``allow=`` closed
vocabulary, ``numeric=`` CSS custom property). See the tag's own docstring in
``brickwork_components.py`` for the full contract; these tests pin it.

Every escaping assertion here follows the discipline ADR-084 section 7 and
ADR-097 section 5 both restate: parse with ``html.parser`` and assert on
real attribute NAMES (never a substring search for ``onclick=``, which
matches the correctly-escaped text inside a clean ``aria-label`` and reports
a false positive), carry a non-vacuity guard (confirm the payload's own
marker text reached the rendered output before trusting an absence), and
carry a known-bad control proving the detector actually fires on genuinely
unprotected output.
"""

from __future__ import annotations

from html.parser import HTMLParser

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError
from django.utils.safestring import mark_safe


def _render(snippet: str, **ctx: object) -> str:
    return Template("{% load brickwork_components %}" + snippet).render(Context(ctx))


def _on_star_attrs(html: str) -> list[tuple[str, str]]:
    """Parse ``html`` and return every ``on*`` attribute actually present on
    any element, using ``html.parser`` rather than a regex/substring search
    (matching ``test_components.py``/``test_dropdown.py``/``test_empty_state.py``'s
    own ``_on_star_attrs`` for #349/#391; not extracted to a shared helper
    here, since that extraction is its own tracked follow-up per ADR-097's
    Affects field, not part of building the seam).

    A regex for ``onclick=`` also matches the correctly-escaped text INSIDE
    an attribute value, which is a false positive on clean output. Parsing
    and checking parsed attribute NAMES is the only technique that tells a
    live handler apart from its escaped, harmless text form.
    """

    class _Finder(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.found: list[tuple[str, str]] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            self.found.extend((tag, name) for name, _value in attrs if name.startswith("on"))

    parser = _Finder()
    parser.feed(html)
    return parser.found


ATTACK = mark_safe('a" onclick="alert(1)')


# --- the known-bad control: proves _on_star_attrs and the non-vacuity
# --- discipline actually detect a live handler, before any test below
# --- trusts a clean result from bw_attr ---------------------------------------


def test_control_known_bad_unprotected_interpolation_is_detected() -> None:
    # A plain, unconstrained interpolation of the same payload, no bw_attr
    # in the way. If this control did not detect a live handler, every
    # "clean" assertion below would be trivially true for the wrong reason
    # (a parser that never finds anything, not a tag that is actually safe).
    control_html = Template('<div aria-label="{{ v }}"></div>').render(Context({"v": ATTACK}))
    assert "alert(1)" in control_html, "the control payload did not even reach the control template's output"
    assert _on_star_attrs(control_html) == [("div", "onclick")]


# --- default mode: escape() unconditionally -----------------------------------


def test_default_mode_mark_safed_payload_cannot_break_out_of_the_attribute() -> None:
    out = _render('<div {% bw_attr "aria-label" v %}></div>', v=ATTACK)
    # Non-vacuity guard: the payload's own marker text must actually reach
    # the rendered output (escaped) before "no live handler" means anything.
    assert "alert(1)" in out, "the payload never reached the render, so the absence check below proves nothing"
    assert _on_star_attrs(out) == []
    assert 'aria-label="a&quot; onclick=&quot;alert(1)"' in out


def test_default_mode_renders_a_legitimate_value_escaped() -> None:
    out = _render('<div {% bw_attr "aria-label" v %}></div>', v="Tom & Jerry")
    assert 'aria-label="Tom &amp; Jerry"' in out


def test_default_mode_non_str_value_is_coerced_via_str() -> None:
    out = _render('<div {% bw_attr "data-count" v %}></div>', v=42)
    assert 'data-count="42"' in out


def test_default_mode_lazy_translation_resolves_before_escaping() -> None:
    from django.utils.translation import gettext_lazy

    out = _render('<div {% bw_attr "aria-label" v %}></div>', v=gettext_lazy("Save"))
    assert 'aria-label="Save"' in out


# --- allow= mode: closed vocabulary, unrecognised value omits the whole
# --- attribute rather than raising or falling back to a guessed default -------


def test_allow_mode_mark_safed_payload_is_omitted_not_rendered() -> None:
    out = _render('<div {% bw_attr "data-variant" v allow="no_data no_results" %}></div>', v=ATTACK)
    # Non-vacuity guard: prove allow= is actually discriminating on this
    # payload rather than the attribute being absent for some unrelated
    # reason (e.g. a typo in the tag call). The attack string is not in the
    # allowed vocabulary, so it must be rejected, and rejection must mean
    # "omit the attribute", not "raise" or "silently substitute a default".
    assert "data-variant" not in out
    assert "alert(1)" not in out
    assert _on_star_attrs(out) == []


def test_allow_mode_renders_a_recognised_value() -> None:
    out = _render('<div {% bw_attr "data-variant" v allow="no_data no_results" %}></div>', v="no_results")
    assert 'data-variant="no_results"' in out


def test_allow_mode_unrecognised_value_omits_the_attribute_entirely() -> None:
    out = _render('<div {% bw_attr "data-variant" v allow="no_data no_results" %}></div>', v="bogus")
    assert "data-variant" not in out
    # Omission, not a fallback: the rendered output carries no trace of the
    # rejected value under any spelling, and none of the allowed values
    # appear either (there is no guessed default to find).
    assert "bogus" not in out
    assert "no_data" not in out
    assert "no_results" not in out


def test_allow_mode_does_not_raise_on_an_unrecognised_value() -> None:
    # Explicit per the brief: allow= never raises on a bad value, unlike
    # numeric=, which does. This is the behavioural discriminator between
    # the two modes' error handling and is worth its own pinned test.
    _render('<div {% bw_attr "data-variant" v allow="no_data no_results" %}></div>', v="anything")


# --- numeric= mode: float() coercion, clamped 0-100, for CSS custom
# --- properties; escaping alone is a no-op on this class of payload -----------


def test_numeric_mode_css_injection_payload_is_rejected_where_escaping_would_be_a_no_op() -> None:
    # ADR-097 section 3's own measured example: this payload carries no
    # quote, < or &, so escape() alone does nothing to it. Only a type
    # coercion closes the CSS-injection hole.
    payload = "50; --bw-color-accent: red; background-image: url(//evil.test/x)"
    with pytest.raises(TemplateSyntaxError):
        _render('<div style="{% bw_attr "--bw-progress-value" v numeric=True %}"></div>', v=payload)


def test_numeric_mode_renders_an_integer_value_without_a_trailing_decimal() -> None:
    out = _render('<div {% bw_attr "data-value" v numeric=True %}></div>', v=50)
    assert 'data-value="50"' in out
    assert 'data-value="50.0"' not in out


def test_numeric_mode_renders_a_fractional_value_with_its_decimal() -> None:
    out = _render('<div {% bw_attr "data-value" v numeric=True %}></div>', v=12.5)
    assert 'data-value="12.5"' in out


def test_numeric_mode_clamps_above_the_upper_bound() -> None:
    out = _render('<div {% bw_attr "data-value" v numeric=True %}></div>', v=150)
    assert 'data-value="100"' in out


def test_numeric_mode_clamps_below_the_lower_bound() -> None:
    out = _render('<div {% bw_attr "data-value" v numeric=True %}></div>', v=-10)
    assert 'data-value="0"' in out


def test_numeric_mode_accepts_a_numeric_string() -> None:
    out = _render('<div {% bw_attr "data-value" v numeric=True %}></div>', v="42")
    assert 'data-value="42"' in out


def test_numeric_mode_non_numeric_value_raises_template_syntax_error() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('<div {% bw_attr "data-value" v numeric=True %}></div>', v="not-a-number")


def test_numeric_mode_infinite_value_raises_template_syntax_error() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('<div {% bw_attr "data-value" v numeric=True %}></div>', v=float("inf"))


def test_numeric_mode_nan_value_raises_template_syntax_error() -> None:
    with pytest.raises(TemplateSyntaxError):
        _render('<div {% bw_attr "data-value" v numeric=True %}></div>', v=float("nan"))


# --- absence: None or "" emits nothing, in every mode --------------------------


def test_none_value_omits_the_attribute_in_default_mode() -> None:
    out = _render('<div {% bw_attr "aria-label" v %}></div>', v=None)
    assert "aria-label" not in out


def test_empty_string_value_omits_the_attribute_in_default_mode() -> None:
    out = _render('<div {% bw_attr "aria-label" v %}></div>', v="")
    assert "aria-label" not in out


def test_none_value_omits_the_attribute_in_allow_mode() -> None:
    out = _render('<div {% bw_attr "data-variant" v allow="no_data no_results" %}></div>', v=None)
    assert "data-variant" not in out


def test_none_value_omits_the_attribute_in_numeric_mode() -> None:
    out = _render('<div {% bw_attr "data-value" v numeric=True %}></div>', v=None)
    assert "data-value" not in out


def test_empty_string_value_omits_the_attribute_in_numeric_mode() -> None:
    # Empty string, not None: numeric= must not try float("") and raise;
    # absence is checked before coercion is attempted.
    out = _render('<div {% bw_attr "data-value" v numeric=True %}></div>', v="")
    assert "data-value" not in out


# --- the format_html regression: this test fails if bw_attr is ever
# --- reimplemented on top of format_html, per ADR-097 section 2 --------------


def test_format_html_would_be_exploitable_here_proving_bw_attr_must_not_use_it() -> None:
    # Not a test of bw_attr's own behaviour: a standing proof, run every
    # time the suite runs, that format_html is the wrong primitive for this
    # seam. If someone "simplifies" bw_attr onto format_html('{}="{}"\',
    # name, value), this control demonstrates exactly what breaks: format_html
    # honours a SafeString's __html__ marker and renders it verbatim, which
    # is the identical trap bw_data_attrs already documents.
    from django.utils.html import format_html

    naive = format_html('{}="{}"', "aria-label", ATTACK)
    assert "alert(1)" in naive
    assert _on_star_attrs(f"<div {naive}></div>") == [("div", "onclick")], (
        "format_html did not reproduce the break-out on this Django version; "
        "if this assertion starts failing, re-verify the regression this "
        "test exists to pin before treating bw_attr's own format_html "
        "prohibition as unnecessary"
    )


def test_bw_attr_itself_is_not_exploitable_by_the_same_payload_format_html_fails_on() -> None:
    # The direct counterpart to the control above: the exact same payload,
    # through bw_attr, in the exact same attribute position, must NOT
    # reproduce the format_html break-out.
    out = _render('<div {% bw_attr "aria-label" v %}></div>', v=ATTACK)
    assert "alert(1)" in out, "non-vacuity: the payload must still reach the render, escaped"
    assert _on_star_attrs(out) == []
