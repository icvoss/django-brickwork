"""Shared machinery for the data-visualisation encoding contract
(ADR-081; icvoss/django-brickwork#183 for the first member, bw_ranked_list).

Every member of the sparkline/trend-indicator/gauge/ranked-list group shares
one contract: the decorative geometry (a bar, line or arc) is aria-hidden and
carries no text of its own; the label and value are present as VISIBLE text
nodes; numeric meaning never rides on bar length or colour alone (COL-030);
geometry is a UNITLESS CSS custom property computed in Python, never a
``width:``/``%`` string built in the template; and there is deliberately NO
per-row ``role="progressbar"`` (VIZ-015: that role's contract is one
quantity's progress toward a known target, not an N-way comparison).
``_progress.html`` legitimately carries full progressbar semantics and is
outside this group; these helpers assert the group's rows/items, never a
blanket ban across every component in the package.

Extracted so the SAME assertions run against every family member's own test
file rather than each one growing a slightly different regex that drifts
from its siblings, mirroring `_class_contract.py`'s extraction reasoning
(icvoss/django-brickwork#120).

CRITICAL: every helper here that strips or regex-matches asserts its own
precondition first, i.e. that the pattern actually matched something, before
asserting the property that match is meant to prove. A strip helper whose
regex matches zero attributes would otherwise report a false pass: the
"stripped" string is identical to the input, and the label/value assertions
that follow would have passed on the UNSTRIPPED html just as well, proving
nothing about COL-030 at all. That vacuity is a known defect class in this
repo (icvoss/django-brickwork#276, #249, #272), so each helper below fails
loudly, with a clear message, rather than silently asserting nothing.
"""

from __future__ import annotations

import re

# --- COL-030: numeric meaning survives with colour/style stripped -----------


def assert_text_survives_colour_and_style_stripped(html: str, *needles: str) -> None:
    """Assert every string in ``needles`` (label and value text, typically)
    is still present after every ``class="..."`` and ``style="..."``
    attribute is removed from ``html``.

    Asserts its own precondition first: the strip must actually have removed
    at least one attribute, or the "survives stripping" property below is
    unproven (the check would pass identically against the untouched
    ``html``, which is not what COL-030 claims)."""
    stripped = re.sub(r'\s(?:class|style)="[^"]*"', "", html)
    assert stripped != html, (
        "the class=/style= strip matched nothing: this helper's own "
        "precondition failed, so the assertions below would prove nothing "
        "about COL-030 even if they passed"
    )
    for needle in needles:
        assert needle in stripped, f"{needle!r} did not survive class=/style= stripping"


# --- decorative geometry: aria-hidden, no text, no progressbar role ---------


def assert_bar_is_aria_hidden_and_empty(html: str, *, bar_class: str) -> None:
    """Assert the decorative geometry element carrying ``bar_class`` is both
    ``aria-hidden="true"`` and an empty element (no visible text of its own
    to duplicate or contradict the label/value text nodes)."""
    bar_match = re.search(rf'<span class="{re.escape(bar_class)}"[^>]*></span>', html)
    assert bar_match is not None, f"no empty <span class={bar_class!r}> element found in the rendered html"
    assert 'aria-hidden="true"' in bar_match.group(0), f"{bar_class!r} element is not aria-hidden"


def assert_no_progressbar_semantics(html: str) -> None:
    """Assert none of the single-quantity-progress ARIA vocabulary
    (``role="progressbar"``, ``aria-valuenow``, ``aria-valuemin``,
    ``aria-valuemax``) leaks into an N-way comparison component (VIZ-015).
    Scoped to the caller's own rendered fragment: it does not, and cannot,
    assert anything about ``_progress.html``, which legitimately carries
    every one of these attributes as the one component built for that
    contract."""
    assert 'role="progressbar"' not in html
    assert "aria-valuenow" not in html
    assert "aria-valuemin" not in html
    assert "aria-valuemax" not in html


def assert_text_nodes_are_not_aria_hidden(html: str, *, text_classes: tuple[str, ...]) -> None:
    """Assert none of the visible label/value text elements (selected by
    their own ``class="..."`` values in ``text_classes``) carry
    ``aria-hidden``: only the decorative geometry element should, and a
    regression that copies aria-hidden onto the text itself would silently
    remove the one channel COL-030 depends on."""
    for text_class in text_classes:
        text_match = re.search(rf'<span class="{re.escape(text_class)}"[^>]*>', html)
        assert text_match is not None, f"no <span class={text_class!r}> element found in the rendered html"
        assert "aria-hidden" not in text_match.group(0), f"{text_class!r} text element must never be aria-hidden"


# --- geometry is a unitless custom property, never width:/% -----------------


def assert_geometry_is_a_unitless_custom_property(html: str, *, property_name: str) -> None:
    """Assert every occurrence of the CSS custom property ``property_name``
    in ``html`` is a bare integer (0-100), never a ``%`` or ``px``-suffixed
    value, and that no ``width:`` declaration rides alongside it. Geometry
    computed as a plain number in Python and turned into a length only by
    the compiled CSS's own ``calc()`` is what keeps the value inspectable as
    data (a consumer can read the number) rather than opaque layout.

    Asserts its own precondition first: the property must actually appear at
    least once, or "every occurrence is unitless" is vacuously true of zero
    occurrences and proves nothing about this component's geometry at all.
    """
    matches = re.findall(rf"{re.escape(property_name)}:\s*([^;\"]+)", html)
    assert matches, f"{property_name!r} was never emitted: this helper's own precondition failed"
    for raw_value in matches:
        value = raw_value.strip()
        assert re.fullmatch(r"-?\d+(?:\.\d+)?", value), (
            f"{property_name!r} emitted {value!r}, which is not a bare unitless number "
            "(a %/px suffix would mean the geometry rode on a unit rather than a plain figure)"
        )
    assert "width:" not in html, (
        "a width: declaration was found alongside the custom property; "
        "geometry must never ride on an inline width string"
    )


# --- rank order is itself meaning: <ol> survives stripping ------------------


def assert_ordered_list_element_survives_stripping(html: str, *, list_class: str) -> None:
    """Assert the element carrying ``list_class`` is still a genuine
    ``<ol ...>`` (not merely that its text content is unchanged) after
    class=/style= stripping. An ``<ol>`` demoted to a ``<div>`` or ``<ul>``
    by a future edit would silently discard the rank order as meaning while
    every label/value string still passed the text checks above."""
    assert f'class="{list_class}"' in html, f"no element carrying class={list_class!r} found in the rendered html"
    stripped = re.sub(r'\s(?:class|style)="[^"]*"', "", html)
    assert stripped != html, (
        "the class=/style= strip matched nothing: this helper's own "
        "precondition failed, so the ordering check below would prove "
        "nothing"
    )
    assert re.search(r"<ol(?:\s[^>]*)?>", stripped) is not None, (
        f"no <ol> element survived stripping for {list_class!r}: "
        "rank order must never depend on a class= or style= attribute"
    )
