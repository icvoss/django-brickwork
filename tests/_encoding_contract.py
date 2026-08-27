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

Two further defect instances, both found by an adversarial second pass over
this module's own first fix and reproduced against the shipped template
before being closed here:

Checking only the FIRST of several matching elements is the same vacuity in
a different shape. A caller that renders a single-row fixture cannot tell
"every element" from "the first element", since ``re.finditer`` and
``re.search`` agree on one match. Every call site asserting an "every
element" guarantee must render a fixture with more than one matching
element and pin the count with ``expected_count``, never a single-row
fixture: rendering only one row was how a template that aria-hid just the
first bar (``{% if forloop.first %}``) passed every test in this file.

Nested markup inside a text-bearing element defeats a check that only reads
that element's own opening tag or a naive inter-tag substring capture.
Text wrapped in a hidden child (``<span class="bw-x__label"><span
aria-hidden="true">Acme Corp</span></span>``) is present as a substring but
genuinely absent from the accessibility tree, so "survives stripping" and
"is not aria-hidden" must both look at the element's full subtree, not just
its own tag or a raw substring capture that a nested tag can ride inside.

Element matching itself (self-closing vs paired tags, single vs double
quotes, attribute order, multi-class values) is shared machinery below
(``_find_elements``) rather than each helper growing its own slightly
different tag regex, which is exactly how ``assert_geometry_is_a_unitless_custom_property``
and ``assert_bar_is_aria_hidden_and_empty`` previously ended up disagreeing
with each other on which elements they could even see.
"""

from __future__ import annotations

import re

# --- shared element matching (self-closing/paired, quote/order-agnostic) ----

_ATTR_STRIP = re.compile(r'\s(?:class|style)="[^"]*"')


def _class_token_regex(class_name: str) -> str:
    """Build a regex fragment matching ``class_name`` as one whitespace-
    delimited token inside a ``class`` attribute value, single- or
    double-quoted, so a multi-class value (``class="bw-x__bar bw-x__bar--hot"``)
    or a class listed after other attributes still matches, rather than
    demanding ``class`` be the sole, first, exact-value attribute."""
    escaped = re.escape(class_name)
    return rf'class\s*=\s*(["\'])(?:(?!\1).)*?\b{escaped}\b(?:(?!\1).)*?\1'


def _find_elements(html: str, *, tag: str, class_name: str) -> list[re.Match[str]]:
    """Find every element ``<tag ...>...</tag>`` or self-closing ``<tag .../>``
    carrying ``class_name`` as one token of its ``class`` attribute,
    regardless of attribute order or quote style. Returns the full element
    (opening tag through matching close, or the self-closing tag alone) so
    callers can inspect its complete subtree, not just the opening tag.

    A tag with no other element of the same name nested inside it is enough
    for every current family member (bars, lines, arcs are always leaves);
    this is not a general nested-tag parser."""
    class_regex = _class_token_regex(class_name)
    pattern = (
        rf"<{tag}\b(?:[^>]*?{class_regex}[^>]*?)"
        rf"(?:/>"
        rf"|>(?:(?!</?{tag}\b).)*?</{tag}>)"
    )
    return list(re.finditer(pattern, html, re.DOTALL))


def _find_text_elements(html: str, *, class_name: str) -> list[str]:
    """Find every ``<span ...>...</span>`` carrying ``class_name`` as one
    class token, returning each element's FULL text (opening tag through
    its OWN matching close), correctly skipping over any nested ``<span>``
    rather than stopping at the first ``</span>`` a naive non-greedy
    ``(.*?)</span>`` capture would find. A text-bearing element that nests
    a hidden child span (``<span class="bw-x__label"><span
    aria-hidden="true">Acme Corp</span></span>``) needs its OUTER close, or
    the capture ends mid-subtree with a dangling, unclosed inner tag that no
    later check can reason about correctly."""
    class_regex = _class_token_regex(class_name)
    elements: list[str] = []
    for start_match in re.finditer(rf"<span\b(?:[^>]*?{class_regex}[^>]*?)>", html, re.DOTALL):
        depth = 1
        cursor = start_match.end()
        while depth > 0:
            next_open = re.search(r"<span\b[^>]*>", html[cursor:], re.IGNORECASE)
            next_close = re.search(r"</span>", html[cursor:], re.IGNORECASE)
            assert next_close is not None, (
                f"<span class={class_name!r}> element has no matching </span> in the rendered html"
            )
            if next_open is not None and next_open.start() < next_close.start():
                depth += 1
                cursor += next_open.end()
            else:
                depth -= 1
                cursor += next_close.end()
        elements.append(html[start_match.start() : cursor])
    return elements


_NESTED_ARIA_HIDDEN_ELEMENT = re.compile(r"<(\w+)\b[^>]*\baria-hidden\s*=\s*[\"']true[\"'][^>]*>.*?</\1>", re.DOTALL)


def _visible_text(inner_html: str) -> str:
    """Return ``inner_html`` with any nested ``aria-hidden="true"`` element
    (and its own subtree) removed entirely, so text that is only present
    inside a hidden descendant cannot be mistaken for text genuinely visible
    to the accessibility tree. ``<span aria-hidden="true">Acme Corp</span>``
    nested inside a label element must not be able to satisfy a "text
    survives" needle: the substring is there, but it is hidden from
    assistive technology, which is exactly the state COL-030 forbids."""
    return _NESTED_ARIA_HIDDEN_ELEMENT.sub("", inner_html)


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
    Text present only inside a NESTED ``aria-hidden="true"`` child is also
    excluded before matching: that text is a substring of the captured
    content but genuinely absent from the accessibility tree, so it must not
    be able to satisfy a needle in its place.

    Asserts its own precondition first: stripping must actually have changed
    at least one of the named elements' own opening tags, or the "survives
    stripping" property below is unproven (the check would pass identically
    against the untouched ``html``, which is not what COL-030 claims)."""
    changed_any_element = False
    text_content: list[str] = []
    for text_class in text_classes:
        elements = _find_text_elements(html, class_name=text_class)
        assert elements, f"no <span class={text_class!r}> element found in the rendered html"
        for element in elements:
            opening_tag = element[: element.index(">") + 1]
            inner = element[len(opening_tag) : -len("</span>")]
            if _ATTR_STRIP.sub("", opening_tag) != opening_tag:
                changed_any_element = True
            text_content.append(_visible_text(inner))

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
    ``tag`` for a sparkline's self-closing ``<line/>``/``<path/>`` or a
    gauge's ``<circle/>``) carrying ``bar_class`` is both
    ``aria-hidden="true"`` and an empty element (no visible text of its own
    to duplicate or contradict the label/value text nodes).

    Matches self-closing and paired forms, single or double quotes,
    attribute order, and multi-class values (``bar_class`` need not be the
    sole or first class token), via the shared ``_find_elements``.

    Checks EVERY matching element, not just the first: a component that
    renders several bars/rows and only aria-hides the first one is a partial
    regression, which ``re.search`` alone would miss, and a caller MUST
    render more than one matching element (never a single-row fixture) and
    pass ``expected_count`` to prove this helper actually looked at more
    than one: a one-element fixture makes ``re.finditer`` and ``re.search``
    indistinguishable, silently exercising nothing about the "every
    element" guarantee. If ``expected_count`` is given, also asserts exactly
    that many elements were found, so a caller can pin "three bars, all
    aria-hidden" and catch a helper silently checking fewer elements than
    the component actually renders."""
    bar_matches = _find_elements(html, tag=tag, class_name=bar_class)
    assert bar_matches, f"no <{tag} class={bar_class!r}> element found in the rendered html"
    if expected_count is not None:
        assert len(bar_matches) == expected_count, (
            f"expected {expected_count} <{tag} class={bar_class!r}> element(s), found {len(bar_matches)}"
        )
    for match in bar_matches:
        element = match.group(0)
        # quote-agnostic, matching what _find_elements itself accepts: the
        # element matcher tolerates single quotes, so a double-quoted
        # substring check here would reject markup the matcher just found
        # and report it as "not aria-hidden" when it plainly is.
        assert re.search(r'aria-hidden\s*=\s*["\']?\s*true', element, re.IGNORECASE) is not None, (
            f"{bar_class!r} element is not aria-hidden: {element!r}"
        )
        if not element.endswith("/>"):
            inner = element[element.index(">") + 1 : element.rindex("<")]
            assert inner == "", f"{bar_class!r} element carries visible text of its own: {inner!r}"


_FORBIDDEN_PROGRESS_ROLES = ("progressbar", "meter", "slider", "spinbutton", "scrollbar")


def assert_no_progressbar_semantics(html: str) -> None:
    """Assert none of the single-quantity-progress ARIA vocabulary leaks
    into an N-way comparison component (VIZ-015): the ``<progress>``/
    ``<meter>`` elements themselves; ``role`` of ``progressbar``, ``meter``,
    ``slider``, ``spinbutton`` or ``scrollbar`` (each carries an implicit or
    explicit numeric value, the thing VIZ-015 forbids per row), including as
    ONE TOKEN of a role token list (``role="presentation progressbar"`` is
    legal ARIA and must still be caught); ``aria-valuenow``/-valuemin``/
    -valuemax``/-valuetext``; and ``aria-roledescription="progress bar"``.
    Case-insensitive, quote-agnostic (including entirely unquoted attribute
    values) and whitespace-tolerant, so ``role='progressbar'``,
    ``ROLE="METER"``, ``role = slider`` and ``role=progressbar`` are all
    caught, not just the single canonical spelling.

    Deliberately OUT OF SCOPE: ``role="img"`` paired with a progress-shaped
    ``aria-label`` (e.g. "42% complete") is a semantic judgement about what
    the label text MEANS, which a mechanical regex over markup cannot make;
    catching that would need reading and understanding label text, not
    matching structure, so it is not attempted here.

    Scoped to the caller's own rendered fragment: it does not, and cannot,
    assert anything about ``_progress.html``, which legitimately carries
    this vocabulary as the one component built for that contract."""
    lowered = html.lower()
    for element in ("progress", "meter"):
        assert not re.search(rf"<{element}\b", lowered), f"forbidden <{element}> element found"
    role_values = re.findall(r'role\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', lowered)
    for double_quoted, single_quoted, unquoted in role_values:
        role_value = double_quoted or single_quoted or unquoted
        tokens = role_value.split()
        forbidden_tokens = [token for token in tokens if token in _FORBIDDEN_PROGRESS_ROLES]
        assert not forbidden_tokens, f"forbidden role token(s) {forbidden_tokens} found in role={role_value!r}"
    for forbidden in ("aria-valuenow", "aria-valuemin", "aria-valuemax", "aria-valuetext"):
        assert forbidden not in lowered, f"forbidden {forbidden!r} attribute found"
    assert re.search(r'aria-roledescription\s*=\s*[\'"]?\s*progress\s*bar', lowered) is None, (
        'forbidden aria-roledescription="progress bar" found'
    )


def assert_text_nodes_are_not_aria_hidden(
    html: str, *, text_classes: tuple[str, ...], expected_count: int | None = None
) -> None:
    """Assert none of the visible label/value text elements (selected by
    their own ``class="..."`` values in ``text_classes``) carry
    ``aria-hidden`` ANYWHERE IN THEIR SUBTREE, not merely on their own
    opening tag: only the decorative geometry element should, and a
    regression that nests a hidden child inside the text element
    (``<span class="bw-x__label"><span aria-hidden="true">Acme
    Corp</span></span>``) would otherwise still pass, silently removing the
    one channel COL-030 depends on while the outer tag looks clean.

    Checks EVERY matching element for each class, not just the first: a
    caller MUST render more than one matching element and pass
    ``expected_count`` to prove this, for the same reason given on
    ``assert_bar_is_aria_hidden_and_empty``. If ``expected_count`` is given,
    it is asserted once, against the total across every class in
    ``text_classes`` combined."""
    total_matches = 0
    for text_class in text_classes:
        elements = _find_text_elements(html, class_name=text_class)
        assert elements, f"no <span class={text_class!r}> element found in the rendered html"
        total_matches += len(elements)
        for element in elements:
            opening_tag = element[: element.index(">") + 1]
            assert "aria-hidden" not in opening_tag, f"{text_class!r} text element must never be aria-hidden"
            inner = element[len(opening_tag) : -len("</span>")]
            assert re.search(r'aria-hidden\s*=\s*["\']?\s*true', inner, re.IGNORECASE) is None, (
                f"{text_class!r} text element must never contain an aria-hidden descendant: {inner!r}"
            )
    if expected_count is not None:
        assert total_matches == expected_count, (
            f"expected {expected_count} text element(s) across {text_classes!r}, found {total_matches}"
        )


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

    Matches self-closing and paired forms, single or double quotes,
    attribute order, and multi-class values, via the shared
    ``_find_elements`` (so this agrees with
    ``assert_bar_is_aria_hidden_and_empty`` on which elements each helper
    can see, rather than the two helpers silently accepting different
    markup shapes).

    Scoped to the geometry element's own ``style`` attribute: an ancestor's
    unrelated ``max-width``/``min-width``/``width`` (a page layout wrapper,
    an embedded ``<style>`` block) must NOT be able to fail this assertion,
    and a property sitting on some OTHER element must not satisfy it
    either. The forbidden declaration is matched as ``width:`` preceded by
    a non-word boundary, so it specifically excludes ``max-width:``/
    ``min-width:`` on the SAME element's own style, which are legitimate
    sizing constraints distinct from the geometry riding on a literal
    ``width:`` string.

    Asserts its own precondition first: the property must actually appear at
    least once on a geometry element, or "every occurrence is unitless" is
    vacuously true of zero occurrences and proves nothing about this
    component's geometry at all.
    """
    geometry_matches = _find_elements(html, tag=tag, class_name=geometry_class)
    assert geometry_matches, f"no <{tag} class={geometry_class!r}> geometry element found in the rendered html"

    found_property = False
    for element_match in geometry_matches:
        opening_tag = element_match.group(0).split(">", 1)[0] + ">"
        style_match = re.search(r'style="([^"]*)"', opening_tag)
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
        assert re.search(r"(?<![\w-])width:", style_value) is None, (
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
