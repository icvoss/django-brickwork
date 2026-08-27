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

THE SCOPE LADDER for "this text is available to the accessibility tree"
(COL-030). Each fix so far closed one rung and left the rest untested;
enumerating the whole ladder is what this module now guards, rung by rung:

  1. the text node itself                              -- covered
  2. the text element's own attributes                  -- covered
  3. its subtree (a nested ``aria-hidden`` child)        -- covered
  4a. its immediate ancestor (the row wrapper)           -- covered
  4b. an ancestor at the fragment root (the component's
      own list element)                                 -- covered
  5. ``aria-label``/``aria-labelledby`` overriding the
      element's own text                                -- PARTIALLY covered

Rungs 1-3 are what the original nested-``aria-hidden``-child fix closed:
the element's own tag and everything strictly inside it. Rungs 4a/4b are
the SAME missing check at greater depth, closed by
``_enclosing_aria_hidden_ranges``/``_is_enclosed_by_any`` below: a
subtree walk starting at the text element can never see outward to an
ancestor, so wrapping the row (4a) or the whole ``<ol>`` (4b) in
``aria-hidden="true"`` removed every label and value from the
accessibility tree while every prior check, scoped to the element's own
tag and descendants, stayed green.

Rung 5 is only partially reachable by a regex over markup, and that
boundary is deliberate rather than an oversight: an element's own
``aria-label`` attribute IS caught by the existing text-content checks
(the label text on the element itself is part of what "text survives"
means). ``aria-labelledby`` pointing at an ID elsewhere in the document
is NOT reachable here: resolving it needs finding the referenced element
by ID anywhere in the fragment and reading ITS hidden state, which is a
second, ID-indexed lookup this module does not build, so a text element
whose accessible name is overridden by a hidden ``aria-labelledby``
target elsewhere in the document can pass every check here while its
real accessible name is empty or wrong. Neither the ranked-list template
nor any current family member uses ``aria-labelledby``, so this is a
structural limit of the regex approach, stated here rather than implied
as covered.
"""

from __future__ import annotations

import re

# --- shared element matching (self-closing/paired, quote/order-agnostic) ----

# Quote-agnostic: a single-quoted class=/style= attribute (class='bar') is
# just as real as a double-quoted one, and _find_elements/_find_text_elements
# already accept both via _class_token_regex. A double-quote-only strip
# leaves a single-quoted attribute in the "stripped" opening tag untouched,
# which either fails the "did the strip change anything" precondition on
# genuinely single-quoted markup (a false negative on this helper's own
# sanity check) or, worse, means an attribute the rest of this module can
# see was never actually stripped before the property assertion ran.
_ATTR_STRIP = re.compile(r"""\s(?:class|style)=(?:"[^"]*"|'[^']*')""")


def _attr_value(attr_name: str, opening_tag: str) -> str | None:
    """Return the value of ``attr_name`` on ``opening_tag``, single- or
    double-quoted, or ``None`` if the attribute is absent.

    A double-quote-only read is the same matched-the-wrong-thing defect as
    ``_ATTR_STRIP`` above: ``_find_elements`` deliberately accepts either
    quote style, so a caller that finds an element via ``_find_elements``
    and then reads one of its attributes with a double-quote-only regex can
    silently see NOTHING on a single-quoted element and treat "attribute
    absent" as "attribute compliant", which is a false pass, not an absent
    property. Every attribute read in this module goes through here so a
    single-quoted ``style=`` or ``class=`` is exactly as visible as a
    double-quoted one, matching what element matching itself already
    guarantees."""
    match = re.search(rf'{re.escape(attr_name)}\s*=\s*"([^"]*)"|{re.escape(attr_name)}\s*=\s*\'([^\']*)\'', opening_tag)
    if match is None:
        return None
    return match.group(1) if match.group(1) is not None else match.group(2)


def _class_token_regex(class_name: str) -> str:
    """Build a regex fragment matching ``class_name`` as one whitespace-
    delimited token inside a ``class`` attribute value, single- or
    double-quoted, so a multi-class value (``class="bw-x__bar bw-x__bar--hot"``)
    or a class listed after other attributes still matches, rather than
    demanding ``class`` be the sole, first, exact-value attribute."""
    # NOT \b around the class name: \b treats "-" as a word boundary, so
    # \bbw-x__bar\b matches inside class="bw-x__bar-label". A helper then
    # locates a SIBLING and asserts the property against it while the real
    # element goes unchecked, which is precisely the matched-the-wrong-thing
    # defect this module exists to prevent (see icvoss/django-brickwork#286).
    # The token must be delimited by whitespace or the quote itself, which is
    # what "one token of a class attribute" actually means.
    escaped = re.escape(class_name)
    boundary_open = r'(?:(?<=["\'])|(?<=\s))'
    boundary_close = r'(?=\s|["\'])'
    return rf'class\s*=\s*(["\'])(?:(?!\1).)*?{boundary_open}{escaped}{boundary_close}(?:(?!\1).)*?\1'


def _find_elements(html: str, *, tag: str, class_name: str) -> list[re.Match[str]]:
    """Find every element ``<tag ...>...</tag>`` or self-closing ``<tag .../>``
    carrying ``class_name`` as one token of its ``class`` attribute,
    regardless of attribute order or quote style. Returns the full element
    (opening tag through matching close, or the self-closing tag alone) so
    callers can inspect its complete subtree, not just the opening tag.

    A tag with no other element of the same name nested inside it is enough
    for every current family member (bars, lines, arcs are always leaves);
    this is not a general nested-tag parser."""
    # The \s before the class regex requires class= to be a real attribute:
    # without it, <span data-note="class='bar'"> matches a search for the
    # class "bar" although the element carries no class attribute at all.
    class_regex = _class_token_regex(class_name)
    element_regex = (
        rf"<{tag}\b(?:[^>]*?\s{class_regex}[^>]*?)"
        rf"(?:/>"
        rf"|>(?:(?!</?{tag}\b).)*?</{tag}>)"
    )
    return list(re.finditer(element_regex, html, re.DOTALL))


def _find_text_elements(html: str, *, class_name: str) -> list[tuple[int, str]]:
    """Find every ``<span ...>...</span>`` carrying ``class_name`` as one
    class token, returning each element's START OFFSET in ``html`` alongside
    its FULL text (opening tag through its OWN matching close), correctly
    skipping over any nested ``<span>`` rather than stopping at the first
    ``</span>`` a naive non-greedy ``(.*?)</span>`` capture would find. A
    text-bearing element that nests a hidden child span (``<span
    class="bw-x__label"><span aria-hidden="true">Acme
    Corp</span></span>``) needs its OUTER close, or the capture ends
    mid-subtree with a dangling, unclosed inner tag that no later check can
    reason about correctly.

    The start offset lets a caller ask ``_enclosing_aria_hidden_ranges``
    whether some ANCESTOR of this element (not the element itself, and not
    a sibling that already closed) is ``aria-hidden="true"``: a subtree scan
    starting from the element's own opening tag can never see outward to a
    parent, so the offset is the only way to relate this element back to
    the whole document's nesting."""
    class_regex = _class_token_regex(class_name)
    elements: list[tuple[int, str]] = []
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
        elements.append((start_match.start(), html[start_match.start() : cursor]))
    return elements


_ANY_TAG = re.compile(r"<(?P<closing>/)?(?P<name>[a-zA-Z][\w-]*)(?P<attrs>[^>]*?)(?P<selfclosing>/)?>", re.DOTALL)
# (?<![\w-]) anchors the attribute name to a real boundary, not merely
# \b: \b alone would also match inside a differently-prefixed attribute
# such as "data-aria-hidden" (that name contains "aria-hidden" as a
# substring, preceded by "-", which \b does not treat as a boundary),
# wrongly treating an unrelated attribute as the hiding one.
_ARIA_HIDDEN_TRUE = re.compile(r'(?<![\w-])aria-hidden\s*=\s*(?:"true"|\'true\'|true\b)', re.IGNORECASE)


def _enclosing_aria_hidden_ranges(html: str) -> list[tuple[int, int]]:
    """Return one ``(start, end)`` span per element, ANYWHERE in ``html``
    and of ANY tag name, whose own opening tag carries
    ``aria-hidden="true"``, spanning from that opening tag's ``<`` through
    its matching closing tag's ``>``. A caller can then test whether some
    other element's start offset falls strictly inside one of these spans,
    which is exactly "is this element a descendant of something hidden",
    the property rungs 4a/4b of the accessibility-tree ladder need: the
    existing subtree helpers only ever look at an element's own tag or
    INWARD into its own descendants, never OUTWARD at its ancestors, so
    wrapping a whole row or the component root in ``aria-hidden="true"``
    passed every prior check while removing every label and value beneath
    it from the accessibility tree.

    Built as a single forward scan over the WHOLE fragment with a tag
    stack, not a second per-element subtree walk: an ancestor can be any
    tag (``<li>``, ``<div>``, the component's own ``<ol>``), so there is no
    single tag name to anchor a depth-tracking loop on the way
    ``_find_text_elements`` anchors on ``<span>``.

    ``aria-hidden="false"`` must NOT open a hidden range: only a literal
    ``true`` (either quote style, or bare unquoted) counts, matching what
    every other helper in this module treats as "hidden". A self-closing
    tag (``<br aria-hidden="true"/>``) never opens a range: it has no body,
    so nothing can be its descendant, and pushing it on the stack would
    make the NEXT sibling's closing tag wrongly pop it instead."""
    ranges: list[tuple[int, int]] = []
    stack: list[tuple[str, int, bool]] = []  # (tag name lower, open tag start, is aria-hidden)
    for match in _ANY_TAG.finditer(html):
        name = match.group("name").lower()
        if match.group("closing"):
            # a closing tag: pop the nearest matching open element, if any.
            # Markup with a stray/mismatched close (which none of this
            # module's own templates produce) is tolerated by searching the
            # stack rather than assuming perfect nesting, since this scan
            # runs over the whole document, including markup this module
            # does not otherwise validate.
            for index in range(len(stack) - 1, -1, -1):
                if stack[index][0] == name:
                    _, open_start, is_hidden = stack.pop(index)
                    # discard anything opened after the popped element and
                    # left dangling (should not occur in well-formed markup)
                    del stack[index:]
                    if is_hidden:
                        ranges.append((open_start, match.end()))
                    break
            continue
        if match.group("selfclosing"):
            continue
        is_hidden = _ARIA_HIDDEN_TRUE.search(match.group("attrs")) is not None
        stack.append((name, match.start(), is_hidden))
    return ranges


def _is_enclosed_by_any(offset: int, ranges: list[tuple[int, int]]) -> bool:
    """True if ``offset`` falls strictly inside some ``(start, end)`` span:
    ``start < offset < end``, not ``<=``, so an element is never treated as
    its own ancestor and a SIBLING that already closed before ``offset``
    (``end <= offset``) never counts."""
    return any(start < offset < end for start, end in ranges)


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
    excluded before matching (rung 3 of the accessibility-tree ladder): that
    text is a substring of the captured content but genuinely absent from
    the accessibility tree, so it must not be able to satisfy a needle in
    its place. An element whose own ANCESTOR (its row, or the component
    root) carries ``aria-hidden="true"`` is excluded from ``text_content``
    entirely (rungs 4a/4b): wrapping a row or the whole list in
    ``aria-hidden="true"`` removes every needle beneath it from the
    accessibility tree just as completely as hiding the text node itself,
    and a needle must not be able to ride to a false pass on an
    ancestor's hidden subtree while every text element's OWN tag looks
    clean.

    Asserts its own precondition first: stripping must actually have changed
    at least one of the named elements' own opening tags, or the "survives
    stripping" property below is unproven (the check would pass identically
    against the untouched ``html``, which is not what COL-030 claims)."""
    hidden_ranges = _enclosing_aria_hidden_ranges(html)
    changed_any_element = False
    text_content: list[str] = []
    for text_class in text_classes:
        elements = _find_text_elements(html, class_name=text_class)
        assert elements, f"no <span class={text_class!r}> element found in the rendered html"
        for start_offset, element in elements:
            opening_tag = element[: element.index(">") + 1]
            inner = element[len(opening_tag) : -len("</span>")]
            if _ATTR_STRIP.sub("", opening_tag) != opening_tag:
                changed_any_element = True
            if _is_enclosed_by_any(start_offset, hidden_ranges):
                continue
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
    their own ``class="..."`` values in ``text_classes``) is hidden from the
    accessibility tree, whether ``aria-hidden`` sits on the element's OWN
    opening tag, ANYWHERE IN ITS SUBTREE (a regression that nests a hidden
    child inside the text element, ``<span class="bw-x__label"><span
    aria-hidden="true">Acme Corp</span></span>``, would otherwise still
    pass, silently removing the one channel COL-030 depends on while the
    outer tag looks clean), or on any ANCESTOR of the element (its row, or
    the component root): wrapping the whole row or list in
    ``aria-hidden="true"`` removes the text from the accessibility tree
    just as completely, while the text element's own tag and subtree stay
    entirely clean, which is exactly what the self-and-subtree checks above
    cannot see.

    Checks EVERY matching element for each class, not just the first: a
    caller MUST render more than one matching element and pass
    ``expected_count`` to prove this, for the same reason given on
    ``assert_bar_is_aria_hidden_and_empty``. If ``expected_count`` is given,
    it is asserted once, against the total across every class in
    ``text_classes`` combined."""
    hidden_ranges = _enclosing_aria_hidden_ranges(html)
    total_matches = 0
    for text_class in text_classes:
        elements = _find_text_elements(html, class_name=text_class)
        assert elements, f"no <span class={text_class!r}> element found in the rendered html"
        total_matches += len(elements)
        for start_offset, element in elements:
            opening_tag = element[: element.index(">") + 1]
            assert "aria-hidden" not in opening_tag, f"{text_class!r} text element must never be aria-hidden"
            inner = element[len(opening_tag) : -len("</span>")]
            assert re.search(r'aria-hidden\s*=\s*["\']?\s*true', inner, re.IGNORECASE) is None, (
                f"{text_class!r} text element must never contain an aria-hidden descendant: {inner!r}"
            )
            assert not _is_enclosed_by_any(start_offset, hidden_ranges), (
                f"{text_class!r} text element has an aria-hidden ancestor: it is present in the DOM but "
                "removed from the accessibility tree by a parent element, not by its own tag or subtree"
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
        # quote-agnostic, matching what _find_elements itself accepts: a
        # double-quote-only read here would find NOTHING on a single-quoted
        # style attribute and silently skip both the property-value check
        # and the width: ban below, rather than reporting the attribute as
        # absent, exactly the defect _attr_value exists to close.
        style_value = _attr_value("style", opening_tag)
        if style_value is None:
            continue
        prop_matches = re.findall(rf"{re.escape(property_name)}:\s*([^;\"']+)", style_value)
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
    not be able to satisfy this check in its place.

    Quote-agnostic, matching what ``_find_elements`` accepts elsewhere in
    this module: a single-quoted ``class='...'`` element is exactly as real
    as a double-quoted one, and a double-quote-only match here would find
    nothing on it, silently reporting "no element carrying this class"
    instead of asserting the property against it."""
    element_match = re.search(
        rf"""<(\w+)((?:\s[^>]*)?\sclass=(?:"{re.escape(list_class)}"|'{re.escape(list_class)}')[^>]*)>""", html
    )
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
