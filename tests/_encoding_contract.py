"""Shared machinery for the data-visualisation encoding contract
(ADR-081; icvoss/django-brickwork#183 for the first member, bw_ranked_list).

Every member of the sparkline/trend-indicator/gauge/ranked-list group shares
FOUR universal properties: the decorative geometry (a bar, line or arc) is
aria-hidden and carries no text of its own; the label and value are present
as VISIBLE text nodes; numeric meaning never rides on bar length or colour
alone (COL-030); and geometry is a UNITLESS CSS custom property computed in
Python, never a ``width:``/``%`` string built in the template, with
deliberately NO per-row ``role="progressbar"``/``role="meter"``/
``role="slider"``/``aria-valuetext`` (VIZ-015: that vocabulary's contract is
one quantity's progress toward a known target, not an N-way comparison).
``_progress.html`` legitimately carries full progressbar semantics and is
outside this group; these helpers assert the group's rows/items, never a
blanket ban across every component in the package.

A FIFTH helper, ``assert_ordered_list_element_survives_stripping``, is
SHAPE-SPECIFIC rather than universal: rank order is part of the encoding
contract only for a component whose rows genuinely have an order (ranked
list). A sparkline, trend indicator or gauge has no rank order to lose, so
that helper does not apply to them; it stays in this module because rank
order genuinely is part of ranked_list's own contract and belongs with the
rest of the contract machinery, not because every family member uses it.

Extracted so the SAME assertions run against every family member's own test
file rather than each one growing a slightly different regex that drifts
from its siblings, mirroring `_class_contract.py`'s extraction reasoning
(icvoss/django-brickwork#120).

CRITICAL, and the reason every helper below takes an element-selecting
keyword rather than scanning the whole document: a whole-document substring
or regex scan can be satisfied by an element the assertion was never about
(an unrelated href, a sibling <ol>, an ancestor's own inline width, a bar
that was never checked). Every helper below locates the specific element(s)
the property is about FIRST, then asserts the property on those elements
alone, never on the document as a whole. Each helper also asserts its own
precondition, i.e. that its own scoped search actually matched something and
that a strip actually changed the scoped text, before asserting the property
that match is meant to prove: a search or strip that matched nothing would
otherwise report a false pass, proving nothing about the property it claims
to guard. That vacuity is a known defect class in this repo (icvoss/
django-brickwork#276, #249, #272, #285), so each helper below fails loudly,
with a clear message, rather than silently asserting nothing or silently
checking fewer elements than exist.
"""

from __future__ import annotations

import re

# --- COL-030: numeric meaning survives with colour/style stripped -----------

_ATTR_STRIP = re.compile(r'\s(?:class|style)="[^"]*"')


def assert_text_survives_colour_and_style_stripped(
    html: str,
    *needles: str,
    text_classes: tuple[str, ...],
) -> None:
    """Assert every string in ``needles`` (label and value text, typically)
    is still present as the TEXT CONTENT of the elements carrying
    ``text_classes``, once class=/style= attributes are stripped from those
    elements' own opening tags.

    Scoped to the named text-bearing elements: a needle that only appears
    inside an unrelated ``href``, a ``data-*`` attribute value, or a sibling
    element's markup must NOT be able to satisfy this assertion, which a
    whole-document substring scan cannot tell apart from the real text node.

    Asserts its own precondition first: stripping must actually have changed
    at least one of the named elements' own opening tags, or the "survives
    stripping" property below is unproven (the check would pass identically
    against the untouched ``html``, which is not what COL-030 claims)."""
    changed_any_element = False
    text_content: list[str] = []
    for text_class in text_classes:
        matches = list(re.finditer(rf'<span class="{re.escape(text_class)}"[^>]*>(.*?)</span>', html, re.DOTALL))
        assert matches, f"no <span class={text_class!r}> element found in the rendered html"
        for match in matches:
            opening_tag = match.group(0)[: match.group(0).index(">") + 1]
            if _ATTR_STRIP.sub("", opening_tag) != opening_tag:
                changed_any_element = True
            text_content.append(match.group(1))

    assert changed_any_element, (
        "the class=/style= strip did not change any of the named text "
        "elements' own opening tags: this helper's own precondition failed, "
        "so the assertions below would prove nothing about COL-030 even if "
        "they passed"
    )
    joined = " ".join(text_content)
    for needle in needles:
        assert needle in joined, (
            f"{needle!r} was not found in the text content of {text_classes!r}; "
            "an attribute value elsewhere in the document does not count"
        )


# --- decorative geometry: aria-hidden, no text, no progressbar role ---------


def assert_bar_is_aria_hidden_and_empty(
    html: str,
    *,
    bar_class: str,
    tag: str = "span",
    expected_count: int | None = None,
) -> None:
    """Assert every decorative geometry element (default ``<span>``; pass
    ``tag`` for a sparkline's ``<line>``/``<path>`` or a gauge's ``<circle>``)
    carrying ``bar_class`` is both ``aria-hidden="true"`` and an empty
    element (no visible text of its own to duplicate or contradict the
    label/value text nodes).

    Checks EVERY matching element, not just the first: a component that
    renders several bars/rows and only aria-hides the first one is a partial
    regression, which ``re.search`` alone would miss. If ``expected_count``
    is given, also asserts exactly that many elements were found, so a
    caller can pin "three bars, all aria-hidden" and catch a helper silently
    checking fewer elements than the component actually renders."""
    bar_matches = list(re.finditer(rf'<{tag} class="{re.escape(bar_class)}"[^>]*></{tag}>', html))
    assert bar_matches, f"no empty <{tag} class={bar_class!r}> element found in the rendered html"
    if expected_count is not None:
        assert len(bar_matches) == expected_count, (
            f"expected {expected_count} <{tag} class={bar_class!r}> element(s), found {len(bar_matches)}"
        )
    for match in bar_matches:
        assert 'aria-hidden="true"' in match.group(0), f"{bar_class!r} element is not aria-hidden: {match.group(0)!r}"


def assert_no_progressbar_semantics(html: str) -> None:
    """Assert none of the single-quantity-progress ARIA vocabulary
    (``role="progressbar"``, ``role="meter"``, ``role="slider"``,
    ``aria-valuenow``, ``aria-valuemin``, ``aria-valuemax``,
    ``aria-valuetext``) leaks into an N-way comparison component (VIZ-015).
    Case-insensitive, quote-agnostic and whitespace-tolerant, so
    ``role='progressbar'``, ``ROLE="METER"`` and ``role = "slider"`` are all
    caught, not just the single canonical spelling.

    Scoped to the caller's own rendered fragment: it does not, and cannot,
    assert anything about ``_progress.html``, which legitimately carries
    this vocabulary as the one component built for that contract."""
    lowered = html.lower()
    role_matches = re.findall(r'role\s*=\s*[\'"]\s*(progressbar|meter|slider)\s*[\'"]', lowered)
    assert not role_matches, f"forbidden progressbar/meter/slider role(s) found: {role_matches}"
    for forbidden in ("aria-valuenow", "aria-valuemin", "aria-valuemax", "aria-valuetext"):
        assert forbidden not in lowered, f"forbidden {forbidden!r} attribute found"


def assert_text_nodes_are_not_aria_hidden(html: str, *, text_classes: tuple[str, ...]) -> None:
    """Assert none of the visible label/value text elements (selected by
    their own ``class="..."`` values in ``text_classes``) carry
    ``aria-hidden``: only the decorative geometry element should, and a
    regression that copies aria-hidden onto the text itself would silently
    remove the one channel COL-030 depends on.

    Checks EVERY matching element for each class, not just the first."""
    for text_class in text_classes:
        text_matches = list(re.finditer(rf'<span class="{re.escape(text_class)}"[^>]*>', html))
        assert text_matches, f"no <span class={text_class!r}> element found in the rendered html"
        for match in text_matches:
            assert "aria-hidden" not in match.group(0), f"{text_class!r} text element must never be aria-hidden"


# --- geometry is a unitless custom property, never width:/% -----------------


def assert_geometry_is_a_unitless_custom_property(
    html: str,
    *,
    property_name: str,
    geometry_class: str,
    tag: str = "span",
) -> None:
    """Assert every occurrence of the CSS custom property ``property_name``
    on the geometry element(s) carrying ``geometry_class`` is a bare integer
    (0-100), never a ``%`` or ``px``-suffixed value, and that no ``width:``
    declaration rides in that SAME element's own ``style`` attribute.
    Geometry computed as a plain number in Python and turned into a length
    only by the compiled CSS's own ``calc()`` is what keeps the value
    inspectable as data (a consumer can read the number) rather than opaque
    layout.

    Scoped to the geometry element's own ``style`` attribute: an ancestor's
    unrelated ``max-width``/``min-width``/``width`` (a page layout wrapper,
    an embedded ``<style>`` block) must NOT be able to fail this assertion,
    and a property sitting on some OTHER element must not satisfy it either.

    Asserts its own precondition first: the property must actually appear at
    least once on a geometry element, or "every occurrence is unitless" is
    vacuously true of zero occurrences and proves nothing about this
    component's geometry at all.
    """
    geometry_matches = list(re.finditer(rf'<{tag} class="{re.escape(geometry_class)}"[^>]*>', html))
    assert geometry_matches, f"no <{tag} class={geometry_class!r}> geometry element found in the rendered html"

    found_property = False
    for element_match in geometry_matches:
        style_match = re.search(r'style="([^"]*)"', element_match.group(0))
        if style_match is None:
            continue
        style_value = style_match.group(1)
        prop_matches = re.findall(rf"{re.escape(property_name)}:\s*([^;\"]+)", style_value)
        for raw_value in prop_matches:
            found_property = True
            value = raw_value.strip()
            assert re.fullmatch(r"-?\d+(?:\.\d+)?", value), (
                f"{property_name!r} emitted {value!r} on a {geometry_class!r} element, which is not a bare "
                "unitless number (a %/px suffix would mean the geometry rode on a unit rather than a plain figure)"
            )
        assert "width:" not in style_value, (
            f"a width: declaration was found in a {geometry_class!r} element's own style attribute; "
            "geometry must never ride on an inline width string"
        )

    assert found_property, (
        f"{property_name!r} was never emitted on a {geometry_class!r} element: this helper's own precondition failed"
    )


# --- rank order is itself meaning: <ol> survives stripping ------------------
# (shape-specific: applies only to components whose rows have a genuine rank
# order, e.g. bw_ranked_list; a sparkline/trend-indicator/gauge has no
# equivalent and does not use this helper. See the module docstring.)


def assert_ordered_list_element_survives_stripping(html: str, *, list_class: str) -> None:
    """Assert the SAME element carrying ``list_class`` is still a genuine
    ``<ol ...>`` after class=/style= attributes are stripped from that
    element's own opening tag, not merely that its text content is unchanged
    and not merely that SOME ``<ol>`` exists somewhere in the document. An
    ``<ol>`` demoted to a ``<div>`` or ``<ul>`` by a future edit would
    silently discard the rank order as meaning while every label/value
    string still passed the text checks above, and a page carrying an
    unrelated ``<ol class="site-toc">`` (breadcrumb, table of contents) must
    not be able to satisfy this check in its place."""
    element_match = re.search(rf'<(\w+)((?:\s[^>]*)?\sclass="{re.escape(list_class)}"[^>]*)>', html)
    assert element_match is not None, f"no element carrying class={list_class!r} found in the rendered html"
    original_tag, attrs = element_match.group(1), element_match.group(2)
    stripped_attrs = _ATTR_STRIP.sub("", attrs)
    assert stripped_attrs != attrs, (
        "the class=/style= strip did not change this element's own opening "
        "tag: this helper's own precondition failed, so the ordering check "
        "below would prove nothing"
    )
    assert original_tag == "ol", (
        f"the element carrying class={list_class!r} is a <{original_tag}>, not an <ol>: "
        "rank order must be encoded by the element itself, and must survive with class=/style= stripped"
    )
