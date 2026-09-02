"""Inclusion tags for the presentational components (button, badge, alert).

These carry a little logic (variant/size validation, the ICO-008 icon-only
accessible-name enforcement), so they are tags rather than bare {% include %}.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html import unescape
from html.parser import HTMLParser

from django import template
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils.html import conditional_escape, escape, format_html
from django.utils.safestring import SafeData, SafeString, mark_safe
from django.utils.translation import gettext

register = template.Library()


@register.filter(name="list_item")
def list_item(sequence, index):
    """Return ``sequence[index]``, or ``""`` when the index is out of range.

    Django templates have no built-in "index a list by a loop counter"
    lookup (``|slice`` only takes a static ``start:stop`` literal), and
    ``_data_table.html``'s ``responsive="stack"`` mode needs exactly that: it
    walks ``columns`` to label each cell, in lockstep with ``row.cells``, by
    position (BR-BW-TPL-005, structure only, no data reshaping elsewhere).
    Silently returns "" on a bad index rather than raising, matching Django's
    own template philosophy of "fail quiet, not loud" for lookups (the same
    behaviour ``{{ dict.missing_key }}`` has).
    """
    try:
        return sequence[int(index)]
    except (IndexError, ValueError, TypeError):
        return ""


_BUTTON_VARIANTS = {"primary", "secondary", "ghost", "danger"}
_ALERT_VARIANTS = {"info", "success", "warning", "danger"}
_SIZES = {"sm", "md", "lg"}
_SKELETON_VARIANTS = {"text", "title", "row", "block"}
# ADR-060 rule 2: bw_badge was the one tag with a documented closed set and no
# enforcement, so a typo emitted a .bw-badge--<typo> class that does not exist
# and failed silently. brickworkui.com shipped variant="error" against it for
# exactly that reason.
_BADGE_VARIANTS = {"neutral", "info", "success", "warning", "danger"}
_DATA_ATTRIBUTE_NAME_RE = re.compile(r"^data-[a-z][a-z0-9_.:-]*$")


def normalise_accessible_name(value: object) -> SafeString:
    """Coerce an accessible-name argument (label/aria_label/trigger_label/...)
    to a stripped, template-safe string, without corrupting an already-safe
    value or a non-str value (icvoss/django-brickwork#329, #330).

    Two failure modes, both reproducible through ordinary template syntax,
    made a bare ``value.strip()`` wrong for this seam:

    1. **Non-str input.** A consumer passing an int, a model instance, or any
       other ``__str__``-able object (all ordinary through
       ``{% bw_toggle some_obj id="x" %}``) raised ``AttributeError`` on
       ``.strip()``, since only ``str`` has that method.
    2. **Double-escaping a SafeString.** ``str.strip()`` (and ``SafeString``
       inherits it unchanged) always returns a plain ``str``, never a
       ``SafeString``: Python's str subclass methods do not preserve the
       subclass. A caller-supplied ``mark_safe``/``format_html`` value (a
       realistic source per #329's own changelog entry: a model property, a
       ``format_html`` call) lost its ``__html__`` marker on ``.strip()``, so
       the template's own auto-escaping then escaped it a second time,
       visibly corrupting text such as ``format_html("Tom {} more", "&")``
       into a displayed ``Tom &amp; more``.

    ``conditional_escape`` is the fix for both at once: it honours
    ``__html__`` when present (a SafeString/lazy-safe value passes through
    unescaped, fixing 2) and otherwise escapes, so a plain object first
    needs coercing to ``str`` (fixing 1: ``conditional_escape`` itself is
    typed for ``str | lazy | SafeData``, not arbitrary objects, mirroring
    ``bw_data_attrs``'s own ``escape(str(value))`` above).

    The coercion guard tests ``SafeData``, not ``str``, so that a plain
    ``str`` arriving at runtime is never mistaken for vetted markup.
    ``SafeString`` subclasses ``str``, so gating on ``str`` would have
    skipped the ``str()`` coercion for every already-safe value and, worse,
    conflated the two.

    What this helper does NOT do, stated plainly because the boundary is
    easy to misread: it does not escape a quoted template literal. Django's
    parser marks every literal safe before a tag ever sees it
    (``Variable.__init__``: ``self.literal = mark_safe(...)``,
    unconditional), so ``{% bw_toggle "Tom & more" id="x" %}`` renders a raw
    ``&``, and no tag-level change can alter that. This is not the #329
    defect class: a literal is template-author text, trusted by the same
    rule as ``mark_safe``, and it is indistinguishable from ``mark_safe``
    at this boundary.

    The path that DOES carry consumer data is a context variable
    (``{% bw_toggle obj.name id="x" %}``, a DB value, a form field, a
    computed label). That arrives as a plain ``str``, takes the ``str()``
    branch, and is escaped by ``conditional_escape`` like any other
    untrusted value, so ``<script>`` reaches the DOM as text, never live.

    Stripping the *escaped* text cannot reintroduce the double-escape,
    because whitespace trimming never touches markup content, and the
    result is re-wrapped in ``mark_safe`` because ``str.strip()`` degrades
    even a ``SafeString`` input back to plain ``str`` (Python's ``str``
    subclass methods do not preserve the subclass).

    An ordinary, never-marked-safe string (the common case) is unaffected in
    substance: ``conditional_escape`` escapes it exactly as the template's
    own auto-escaping would have, so wrapping that already-escaped result in
    ``mark_safe`` and letting the auto-escaping no-op over it renders
    identically to leaving it unescaped and auto-escaped once. Only a value
    that was ALREADY safe (``SafeData``) changes behaviour, which is the
    point: that is the one case ordinary auto-escaping alone gets wrong.
    """
    return mark_safe(conditional_escape(value if isinstance(value, SafeData) else str(value)).strip())


def escape_attribute_value(value: object) -> SafeString:
    """Coerce an accessible-name argument that is rendered ONLY into an
    attribute value (``aria_label`` on ``bw_button``/``bw_dropdown``, and the
    attribute-position half of ``bw_dropdown``'s ``trigger_label``) to a
    stripped, unconditionally escaped string (icvoss/django-brickwork#349).

    This is deliberately NOT ``normalise_accessible_name``. That helper
    exists for TEXT-position values, where ``conditional_escape`` honouring
    ``__html__`` is correct: a ``mark_safe``'d value is trusted markup and
    renders as markup. An attribute value is never markup, so a ``SafeData``
    marker there is meaningless, and honouring it is exactly how #349 let a
    ``mark_safe('a" onclick="alert(1)')`` accessible name close the quote
    and land a live event handler. ``escape()``, never ``conditional_escape``,
    is the ADR-083 rule for every attribute-value seam in this module
    (``bw_data_attrs``, ``bw_chart_mount``, ``bw_icon``'s ``label``): the
    marker records THAT a value was vetted safe, never for WHICH position,
    so it cannot be trusted to mean "safe as an attribute value" here.

    ``str(value)`` first, matching ``normalise_accessible_name``, so a
    non-str argument (an int, a model instance, any ordinary ``__str__``-able
    object) does not raise, and a lazy-translated value resolves before
    escaping.

    Known, accepted cost, not a defect: a ``SafeString``/``format_html``
    accessible name is escaped like any other value here, so its entities
    render literally (e.g. an author-supplied ``&amp;`` shows as the text
    "&amp;", not "&"). The supported path for an attribute-position
    accessible name is plain text; script execution is the alternative this
    trades against, and that trade is not close.
    """
    return mark_safe(escape(str(value)).strip())


def _numeric_attribute_value(value: object) -> str:
    """Coerce ``value`` to a clamped 0-100 string for a CSS custom property
    (ADR-097 section 3): ``escape()`` is a no-op on a numeric payload with no
    quote, ``<`` or ``&`` in it, so a value interpolated into a ``style``
    attribute (``--bw-progress-value: {{ value }}``) needs a TYPE, not an
    escape. Measured: ``"50; --bw-color-accent: red; background-image:
    url(//evil.test/x)"`` survives ``escape()`` unchanged and ``float()``
    rejects it, which is the whole point of this mode.

    ``float()``, not ``Decimal``, matching the ADR-097 worked example
    exactly: this seam is for a CSS custom property display value, not a
    financial or precision-sensitive quantity (contrast ``_gauge_numeric``/
    `_validate_ranked_list_row`, which use ``Decimal`` for a different,
    amount-summing reason). A non-numeric value is a template-author error,
    not consumer data with a graceful fallback, so it raises rather than
    silently rendering 0.

    Trailing ``.0`` is stripped for a whole-number result (``50`` rather
    than ``50.0``) so a call site passing a plain int renders identically to
    the raw interpolation it replaces; a genuinely fractional clamp result
    keeps its decimal (``50.5``).
    """
    try:
        numeric_value = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TemplateSyntaxError(f"bw_attr numeric=True requires a numeric value, got {value!r}") from exc
    if not math.isfinite(numeric_value):
        raise TemplateSyntaxError(f"bw_attr numeric=True requires a finite number, got {value!r}")
    clamped = min(max(numeric_value, 0.0), 100.0)
    if clamped.is_integer():
        return str(int(clamped))
    return str(clamped)


@register.simple_tag
def bw_attr(
    name: str,
    value: object,
    *,
    allow: str = "",
    numeric: bool = False,
    prefix: str = "",
    suffix: str = "",
) -> SafeString:
    """Emit one complete, safe HTML attribute (``name="value"``) or nothing
    at all (ADR-097): the single seam for every consumer value an
    include-only template places into attribute position, callable from
    inside the template body the way ``bw_data_attrs`` already is from
    ``_data_table.html``.

    Replaces four partial mechanisms with one (ADR-097 section 1):
    ``escape_attribute_value`` (tag path only, 9 sites), the constrain
    pattern (closed-vocabulary templates only, 2 sites), ``bw_data_attrs``
    (``data-*`` mappings only, 1 site), and the ~28 include-only sites that
    had nothing. ``escape_attribute_value`` and ``bw_data_attrs`` are
    UNCHANGED by this addition (see their own docstrings); this is the one
    mechanism the other three fold into, not a fifth one alongside them.

    Three modes, selected by the VALUE's own nature, never by the
    component (ADR-097 section 3):

    - **Default**: ``escape()`` the value (the ADR-083 rule: unconditional,
      never ``conditional_escape``, because a ``SafeData`` marker records
      THAT a value was vetted safe, never for WHICH position, and an
      attribute is never a text position).
    - **``allow="a b c"``**: a closed, space-separated vocabulary. A value
      not in the list emits NOTHING, i.e. the attribute is omitted
      entirely. This never raises and never falls back to a guessed
      default: an omitted attribute is a value a reader (and any CSS/ARIA
      relying on it) can see is absent, where a silent fallback value looks
      identical to one the caller actually chose.
    - **``numeric=True``**: coerced via ``float()`` and clamped to 0-100 for
      a CSS custom property (``_numeric_attribute_value`` above). A
      non-numeric value raises ``TemplateSyntaxError``, because unlike the
      other two modes this one has no "just omit it" reading: a CSS custom
      property with no value is a template-author bug, not consumer input
      to degrade gracefully around.

    An absent value (``None``) or an empty string, in EVERY mode, emits
    nothing: there is no attribute worth emitting for "no value", and this
    matches ``bw_data_attrs``'s existing "a str means not supplied" contract
    for the same reason (an unset context variable resolves to ``""``, not
    ``None``, under Django's ``string_if_invalid`` machinery in the default
    case, and both must be treated as absence).

    ``str(value)`` first, matching ``escape_attribute_value`` exactly, so a
    non-str argument (an int, a model instance, any ordinary ``__str__``-
    able object) does not raise and a lazy-translated value resolves before
    escaping. ``numeric=True`` coerces via ``float()`` directly instead,
    since ``str()``-then-``float()`` would reject a value ``float()`` alone
    accepts (a ``Decimal`` or a numpy scalar with no clean ``str()`` form).

    Does NOT use ``format_html``: the identical trap ``bw_data_attrs``
    already documents. ``format_html`` honours ``__html__`` by documented
    contract, so a ``mark_safe``'d payload passed through it renders
    VERBATIM. Measured against a first spike of this seam:
    ``format_html('{}="{}"', name, value)`` with an unescaped ``value``
    rendered ``<div aria-label="a" onclick="alert(1)">``. This tag escapes
    the name (defence in depth: it is always a template-author literal at
    every call site the ADR names, never consumer data, but escaping it
    costs nothing and closes the case where a future call site passes a
    variable) and the value with ``escape()``, builds the attribute string
    itself with plain string interpolation, and ``mark_safe``s the result,
    so nothing downstream can re-interpret an already-escaped value as
    trusted markup.

    The attribute NAME is not validated against a closed vocabulary the way
    ``bw_data_attrs`` restricts its mapping keys to ``data-*``: this tag's
    ``name`` is always a quoted literal at the call site
    (``{% bw_attr "aria-label" label %}``), the template author's own
    choice of which attribute to protect, not consumer-supplied data the
    way a ``data`` mapping's keys are. A closed grammar here would defeat
    the seam's purpose of being usable for any attribute a template wants
    to guard.
    """
    if value is None or value == "":
        return mark_safe("")
    rendered_value: str
    if allow:
        if str(value) not in set(allow.split()):
            return mark_safe("")
        rendered_value = escape(str(value))
    elif numeric:
        rendered_value = _numeric_attribute_value(value)
    else:
        rendered_value = escape(str(value))
    # prefix/suffix are TEMPLATE-AUTHOR literals, never consumer data: they let
    # the seam own an attribute whose value is a fixed wrapper around one
    # consumer value, such as a CSS custom property
    # (style="--bw-progress-value: 42"). They are escaped like everything else
    # here, so a call site cannot smuggle markup through them either. This
    # keeps the ADR-097 rule intact rather than weakening it: the seam still
    # emits the WHOLE attribute, so there is still no quote for an author to
    # write and forget. A value that needs a wrapper built from CONSUMER data
    # is out of scope by construction, because prefix/suffix take no variable.
    return mark_safe(f'{escape(name)}="{escape(prefix)}{rendered_value}{escape(suffix)}"')


@register.simple_tag
def bw_data_attrs(attrs: object, subject: str = "data table row") -> SafeString:
    """Render consumer-owned data attributes safely.

    Structural components use this for optional ``data`` mappings. Only
    ordinary ``data-*`` names are accepted: Brickwork's own ``data-bw-*`` hooks
    remain component-owned, and attribute values are escaped.
    """
    # A str is never a valid mapping, so it means "not supplied", never
    # "supplied and wrong". That distinction is load-bearing: a consumer
    # running Django's string_if_invalid resolves a missing row.data to the
    # marker STRING, not to None, so treating a str as an error made an
    # OPTIONAL option raise a hard TemplateSyntaxError and 500 the page for
    # every consumer whose rows simply had no data key (brickwork#80, whose
    # regression suite is tests/test_string_if_invalid.py; the consumer smoke
    # leg sets string_if_invalid precisely to catch this class).
    if attrs is None or isinstance(attrs, str):
        return mark_safe("")
    if not isinstance(attrs, Mapping):
        raise TemplateSyntaxError(f"{subject} data must be a mapping of data-* attribute name -> value, got {attrs!r}")

    parts = []
    for name, value in attrs.items():
        if not isinstance(name, str) or not _DATA_ATTRIBUTE_NAME_RE.match(name) or name.startswith("data-bw-"):
            raise TemplateSyntaxError(f"{subject} data contains an invalid data-* attribute name: {name!r}")
        # escape() rather than relying on format_html's own escaping: format_html
        # does NOT escape a value that is already a SafeString, by its documented
        # contract, so a consumer value carrying mark_safe (from format_html, a
        # model property, or any helper returning pre-escaped HTML) closed the
        # quote and injected arbitrary attributes. Verified: a SafeString value
        # of '" role="progressbar' rendered role="progressbar" onto the element,
        # which is the exact outcome ADR-083 exists to prevent. The name grammar
        # cannot defend this, because the value reaches the same markup position.
        parts.append(format_html(' {}="{}"', name, escape(str(value))))
    return mark_safe("".join(parts))


_SEARCH_SCOPE_KEYS = {"label", "name", "value", "clear_href"}
# icvoss/django-brickwork#183: geometry is computed in Python against a
# closed vocabulary (ADR-060 rule 2), never left to the template to guess a
# denominator from. "max" is the leaderboard reading (the longest row is
# full-width); "total" is the share-of-whole reading (rows sum to a fraction
# of the total, so a single dominant row does not stretch to 100%).
_RANKED_LIST_BASES = {"max", "total"}


@register.inclusion_tag("brickwork/components/_button.html")
def bw_button(
    label: str = "",
    *,
    variant: str = "primary",
    size: str = "md",
    type: str = "button",
    href: str = "",
    icon: str = "",
    icon_only: bool = False,
    loading: bool = False,
    disabled: bool = False,
    aria_label: str = "",
    name: str = "",
    value: str = "",
) -> dict:
    """A button or link-button. ICO-008: an icon-only button REQUIRES an
    accessible name (aria_label), else it is a render error (WCAG 4.1.2).

    ``name``/``value`` (icvoss/django-brickwork#119) carry WHICH submit was
    pressed back to the server, which is the whole mechanism a bulk-actions bar
    runs on (_bulk_actions_bar.html's own docstring documents exactly this
    call). They apply to the ``<button>`` branch only: ``name``/``value`` on an
    ``<a>`` are meaningless, so pairing them with ``href`` is a render error
    rather than a silent drop, which is the failure mode that let #119 sit
    undetected.
    """
    if variant not in _BUTTON_VARIANTS:
        raise TemplateSyntaxError(f"bw_button variant must be one of {sorted(_BUTTON_VARIANTS)}, got {variant!r}")
    if size not in _SIZES:
        raise TemplateSyntaxError(f"bw_button size must be one of {sorted(_SIZES)}, got {size!r}")
    # Stripped before testing, not merely truthiness-tested: a whitespace-only
    # aria_label is truthy in Python and is NOT an accessible name to any
    # screen reader (the same accepted cost bw_chart_mount's own aria_label
    # documents in this file, under icvoss/django-brickwork#351).
    #
    # escape_attribute_value, not normalise_accessible_name: aria_label is
    # rendered ONLY into an aria-label ATTRIBUTE by _button.html (three
    # sites), never into text position, so it must be unconditionally
    # escaped rather than conditionally escaped. normalise_accessible_name's
    # conditional_escape honours a SafeString's __html__ marker, which is
    # correct for text position and is exactly how a mark_safe'd aria_label
    # closed the attribute and landed a live event handler
    # (icvoss/django-brickwork#349).
    aria_label = escape_attribute_value(aria_label)
    if icon_only and not aria_label:
        raise TemplateSyntaxError(
            "bw_button icon_only=True requires aria_label= (an icon-only button "
            "with no accessible name is a WCAG 4.1.2 failure, ICO-008)."
        )
    if href and (name or value):
        raise TemplateSyntaxError(
            "bw_button name=/value= apply to the <button> branch only, but href= "
            "was given, which renders an <a>. A link carries its data in the URL, "
            "so drop name/value or drop href."
        )
    if value and not name:
        raise TemplateSyntaxError(
            "bw_button value= requires name= (a submit value with no name is "
            "never sent by the browser, so the server would see nothing)."
        )
    return {
        "label": label,
        "variant": variant,
        "size": size,
        "type": type,
        "href": href,
        "icon": icon,
        "icon_only": icon_only,
        "loading": loading,
        "disabled": disabled,
        "aria_label": aria_label,
        "name": name,
        "value": value,
    }


@register.inclusion_tag("brickwork/components/_badge.html")
def bw_badge(label: str, *, variant: str = "neutral", icon: str = "", dismissible: bool = False) -> dict:
    """A small status/label badge. Reserved for neutral information, never error
    communication (errors use bw_alert in banner form, STA-008). dismissible=True
    (04-interfaces 4b Dismissible section, CMP-012) adds the bwDismissible wiring
    and a hidden-until-init close control; False renders byte-identical to the
    pre-0.9.0 output."""
    if variant not in _BADGE_VARIANTS:
        raise TemplateSyntaxError(f"bw_badge variant must be one of {sorted(_BADGE_VARIANTS)}, got {variant!r}")
    return {"label": label, "variant": variant, "icon": icon, "dismissible": bool(dismissible)}


@register.inclusion_tag("brickwork/components/_alert.html")
def bw_alert(message: str = "", *, variant: str = "info", title: str = "", dismissible: bool = False) -> dict:
    """A full-width banner alert (role=alert), the loud-surface for errors and
    other page-level status (STA-008/009). dismissible=True (04-interfaces 4b
    Dismissible section, CMP-010) adds the bwDismissible wiring and a
    hidden-until-init close control; False renders byte-identical to the
    pre-0.9.0 output."""
    if variant not in _ALERT_VARIANTS:
        raise TemplateSyntaxError(f"bw_alert variant must be one of {sorted(_ALERT_VARIANTS)}, got {variant!r}")
    icon = {"info": "info", "success": "success", "warning": "alert-triangle", "danger": "alert-circle"}[variant]
    return {"message": message, "variant": variant, "title": title, "icon": icon, "dismissible": bool(dismissible)}


@register.inclusion_tag("brickwork/components/_search.html")
def bw_search(
    action: str,
    *,
    name: str = "q",
    placeholder: str = "",
    value: str = "",
    scope: Mapping[str, str] | None = None,
) -> dict:
    """A topbar search form with a real GET no-JS floor.

    ``action`` is the consumer-owned search URL. ``name`` (default ``"q"``),
    ``placeholder``, and ``value`` configure the native search input. An
    optional ``scope`` mapping makes a search pre-scoped and must contain
    ``label``, ``name``, ``value``, and ``clear_href``. It renders both the
    hidden submitted input and a native clear link, so widening the search
    scope also works without JavaScript. ``clear_label`` may override the
    clear link's accessible name.

    Brickwork renders the form and its query fields only. The consumer owns
    the endpoint, search behaviour, and construction of ``clear_href`` so it
    preserves whichever query parameters matter to that application.
    """
    if not action:
        raise TemplateSyntaxError("bw_search requires action= (the consumer-owned search URL).")
    if not name:
        raise TemplateSyntaxError("bw_search requires a non-empty name= for the submitted query.")

    scope_context = None
    if scope is not None:
        if not isinstance(scope, Mapping):
            raise TemplateSyntaxError("bw_search scope= must be a mapping with label, name, value, and clear_href.")
        missing = _SEARCH_SCOPE_KEYS.difference(scope)
        if missing:
            raise TemplateSyntaxError(f"bw_search scope= is missing required keys: {sorted(missing)}.")
        scope_context = {
            "label": scope["label"],
            "name": scope["name"],
            "value": scope["value"],
            "clear_href": scope["clear_href"],
            "clear_label": scope.get("clear_label")
            or gettext("Remove %(label)s search scope") % {"label": scope["label"]},
        }

    return {
        "action": action,
        "name": name,
        "placeholder": placeholder or gettext("Search"),
        "value": value,
        "scope": scope_context,
        "search_label": gettext("Search"),
    }


@register.inclusion_tag("brickwork/components/_toggle.html")
def bw_toggle(
    label: str,
    *,
    id: str,
    name: str = "",
    value: str = "on",
    checked: bool = False,
    disabled: bool = False,
) -> dict:
    """A standalone labelled toggle switch, not bound to a Django form field
    (BR-BW-INPUT-001). ``label`` is required and non-empty (a switch with no
    accessible name is a WCAG 4.1.2 failure, the ICO-008 defect class); ``id``
    is required so the wrapping <label> pairs correctly. ``name`` defaults to
    ``id`` when omitted, matching how most single-control POST/hx-post payloads
    key their field. For a form-bound checkbox use bw_field_widget's own
    BR-BW-INPUT-001 opt-in (forms.CheckboxInput(attrs={"class": "bw-toggle"}))
    instead of this tag."""
    # Stripped before testing, not merely truthiness-tested: a whitespace-only
    # label is truthy in Python and is NOT an accessible name to any screen
    # reader (the bw_chart_mount aria_label precedent, brickwork_components.py:517),
    # so the "requires a non-empty label" claim below is only true once this runs.
    # normalise_accessible_name (not a bare .strip()) also coerces a non-str
    # value and preserves an already-safe one without double-escaping it
    # (icvoss/django-brickwork#330).
    label = normalise_accessible_name(label)
    if not label:
        raise TemplateSyntaxError(
            "bw_toggle requires a non-empty label (a switch with no accessible name is a WCAG 4.1.2 failure)."
        )
    if not id:
        raise TemplateSyntaxError("bw_toggle requires id= (the wrapping label pairs with it).")
    return {
        "label": label,
        "id": id,
        "name": name or id,
        "value": value,
        "checked": bool(checked),
        "disabled": bool(disabled),
    }


@register.inclusion_tag("brickwork/components/_skeleton.html")
def bw_skeleton(
    *,
    variant: str = "text",
    count: int = 1,
    width: str = "",
    height: str = "",
) -> dict:
    """A loading placeholder (STA-004). Repeats ``count`` copies of the shape
    named by ``variant`` ("text" | "title" | "row" | "block"). A plain
    {% include %} cannot loop a variable count, so this is a tag: it
    validates ``variant`` and turns ``count`` into a range() the template
    iterates. ``width``/``height`` (CSS lengths, e.g. "12rem") override the
    variant's default box via the --bw-skeleton-w/-h custom properties;
    omitted keeps the variant's own default sizing."""
    if variant not in _SKELETON_VARIANTS:
        raise TemplateSyntaxError(f"bw_skeleton variant must be one of {sorted(_SKELETON_VARIANTS)}, got {variant!r}")
    if not isinstance(count, int) or count < 1:
        raise TemplateSyntaxError(f"bw_skeleton count must be a positive int, got {count!r}")
    style_parts = []
    if width:
        style_parts.append(f"--bw-skeleton-w: {width}")
    if height:
        style_parts.append(f"--bw-skeleton-h: {height}")
    return {
        "variant": variant,
        "count": range(count),
        # Plain (unescaped) string: the template renders it inside a
        # style="..." attribute, where Django's normal autoescaping of the
        # attribute value is exactly the protection needed (width/height are
        # caller-supplied CSS lengths, never markup).
        "style_attr": "; ".join(style_parts),
    }


@dataclass(frozen=True)
class RankedListRow:
    """One ranked-list row prepared for template rendering: label/value
    resolved to display strings, the bar's 0-100 geometry computed here (the
    template only ever consumes the finished number), href/data pre-shaped."""

    label: str
    value: str
    percent: int
    href: str
    attrs_html: SafeString  # "" or a leading-space run of escaped data-* attributes


def _ranked_list_denominator(amounts: list[Decimal], basis: str) -> Decimal:
    # amounts is never empty here: _validate_ranked_list_row runs (and would
    # already have raised on a missing/non-numeric amount) for every row
    # before this is called. start=Decimal(0), not the sum() builtin's
    # default int 0, so mypy sees the return type as Decimal in both
    # branches rather than "Decimal | int" (sum() never actually returns the
    # int seed here, since amounts is never empty, but its static type does).
    return max(amounts) if basis == "max" else sum(amounts, start=Decimal(0))


def _validate_ranked_list_row(raw: object, *, basis: str) -> Decimal:
    """Raise the friendly, specific error for a malformed row, and return its
    amount as a ``Decimal``. Split from `_shape_ranked_list_row` so every
    row's shape is checked, and every amount collected, BEFORE the
    denominator is computed: `max()`/`sum()` over zero collected amounts
    (every row malformed) would otherwise raise a bare ValueError instead of
    this function's own TemplateSyntaxError.

    Every amount is normalised to ``Decimal`` here, not ``float``, so the
    geometry maths downstream never round-trips through float and cannot
    silently under/overflow a caller's ``Decimal`` (icvoss/django-brickwork
    adversarial review: ``Decimal("1e-1000")`` underflowed to 0.0 through
    ``float()``, and ``Decimal("1e10000")`` overflowed to inf and crashed
    `round()`). ``Decimal(str(x))`` is exact for int and bool, and matches
    float's own repr for float, so this changes nothing for the existing
    int/float callers.
    """
    if not isinstance(raw, Mapping):
        raise TemplateSyntaxError(f"bw_ranked_list rows must be mappings, got {raw!r}")
    label = raw.get("label")
    amount = raw.get("amount")
    if not label or amount is None:
        raise TemplateSyntaxError(f'bw_ranked_list rows require "label" and "amount", got {dict(raw)!r}')
    try:
        if isinstance(amount, Decimal):
            decimal_amount = amount
        elif isinstance(amount, bool):
            # bool is an int subclass in Python, and str(True) == "True" is not
            # a numeric string Decimal() accepts, so it needs its own branch.
            # Unchanged, pre-existing behaviour (amount=True already rendered
            # as 1 before this fix): not something this defect pass changes.
            decimal_amount = Decimal(int(amount))
        else:
            decimal_amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise TemplateSyntaxError(f"bw_ranked_list row amount must be numeric, got {amount!r}") from exc
    # NaN and +/-Infinity pass isinstance/Decimal conversion but are not a
    # position on the number line, so a share-of-something computed against
    # one is meaningless; reject rather than let round() crash on it later
    # (bare "cannot convert float NaN to integer") or render a corrupted bar.
    if not decimal_amount.is_finite():
        raise TemplateSyntaxError(
            f"bw_ranked_list row amount must be a finite number, got {dict(raw)!r} (amount={amount!r})"
        )
    if basis == "total" and decimal_amount < 0:
        # "share of total" is undefined once amounts have mixed signs: the
        # denominator (sum of all amounts) can land at or below zero even
        # though some individual rows are genuinely positive, which the old
        # code rendered as every row (including the positive ones) at a
        # zero-width bar (icvoss/django-brickwork adversarial review). A
        # negative row is meaningful under basis="max" (it degrades to a
        # zero-width bar, which the existing geometry contract already
        # covers), so the rejection is scoped to basis="total" only.
        raise TemplateSyntaxError(
            f'bw_ranked_list basis="total" requires every row amount to be non-negative (share of a total is '
            f"undefined with mixed signs), got {dict(raw)!r}"
        )
    return decimal_amount


def _shape_ranked_list_row(raw: Mapping, *, amount: Decimal, denominator: Decimal) -> RankedListRow:
    """Build the finished row. ``raw`` has already passed
    `_validate_ranked_list_row` (a mapping, with "label" and a finite,
    numeric "amount"), and ``amount`` is that same amount as a ``Decimal``,
    so this function does no further validation of its own."""
    # A zero or negative denominator (every amount non-positive, or basis="max"
    # against an all-zero set) degrades to a zero-width bar rather than a
    # ZeroDivisionError or a negative/over-100 width: the label/value text
    # still renders, only the decorative bar goes empty.
    percent = 0 if denominator <= 0 or amount <= 0 else round(min(amount / denominator, Decimal(1)) * 100)
    value = raw.get("value")
    if value is None:
        # VIZ-020: the package never formats numbers (locale, currency and
        # precision are consumer decisions); the unformatted RAW amount
        # (never the coerced float) is the only honest default, matching how
        # bw_data_table leaves cell text entirely to the caller.
        value = str(raw["amount"])
    return RankedListRow(
        label=str(raw["label"]),
        value=str(value),
        percent=int(percent),
        href=str(raw.get("href", "") or ""),
        attrs_html=bw_data_attrs(raw.get("data"), "ranked list row"),
    )


# icvoss/django-brickwork VIZ-007 to VIZ-010: a gauge reads one quantity
# against a fixed min/max, not an N-way comparison (bw_ranked_list's own
# family boundary), so it deliberately keeps the SVG geometry fixed at a
# 0-100 viewBox and expresses only the arc's dash geometry per instance.
# threshold_bands resolves to one of these four names, never a caller-chosen
# colour string: each is an ALREADY-SHIPPED semantic token (danger/warning/
# success carry their own status meaning; accent is the shared ink used for
# every other determinate-progress fill in the package, .bw-progress__fill
# and .bw-ranked-list__bar__before both key off --bw-color-accent), so this
# component ships no new colour token at all (colour tokens are semantic-tier
# and per-theme-authored; this closed set already exists in both themes).
_GAUGE_SIZES = _SIZES
_GAUGE_THRESHOLD_TOKENS = {"accent", "success", "warning", "danger"}
# A full circle's centre-to-edge angle in a 0-100 viewBox: r=40 leaves enough
# margin inside a 100x100 box for the stroke width without clipping (VIZ-010
# sizes only change the box's rendered diameter via CSS, never this radius,
# so the geometry maths below is the same for every size).
_GAUGE_VIEWBOX_RADIUS = 40.0
_GAUGE_CIRCUMFERENCE = 2 * 3.141592653589793 * _GAUGE_VIEWBOX_RADIUS


def _gauge_numeric(raw: object, *, name: str) -> Decimal:
    """Coerce a gauge numeric argument (value/min/max) to ``Decimal``, the
    same conversion `_validate_ranked_list_row` uses and for the same reason:
    ``Decimal(str(x))`` never round-trips through float, so it cannot
    silently under/overflow the way a caller-supplied `Decimal("1e10000")`
    already has for `_ranked_list.html` (icvoss/django-brickwork adversarial
    review, see `_validate_ranked_list_row`'s own docstring)."""
    try:
        if isinstance(raw, Decimal):
            decimal_value = raw
        elif isinstance(raw, bool):
            decimal_value = Decimal(int(raw))
        else:
            decimal_value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise TemplateSyntaxError(f"bw_gauge {name} must be numeric, got {raw!r}") from exc
    if not decimal_value.is_finite():
        raise TemplateSyntaxError(f"bw_gauge {name} must be a finite number, got {raw!r}")
    return decimal_value


def _gauge_threshold_token(percent: Decimal, threshold_bands: object) -> str:
    """Resolve the arc's colour token from ``threshold_bands`` (VIZ-009): a
    list of ``{"max": <numeric>, "token": <one of _GAUGE_THRESHOLD_TOKENS>}``
    mappings, sorted here by ``max`` ascending, the first band whose ``max``
    is greater than or equal to the current percent. ``threshold_bands=None``
    (the default) or an empty list resolves to "accent" unconditionally,
    which is the same colour a bare `_progress.html` fill already uses, so an
    ungated gauge call reads exactly like the plain determinate case rather
    than an unstyled or missing arc.

    COL-030 is enforced structurally, not by this function: the resolved
    token only ever selects a CSS class modifier on the decorative,
    aria-hidden arc (never inline colour), and the template ALWAYS renders
    either the caller's own visible-text label or, when the label carries no
    visible text (empty, whitespace-only, or markup with no text content;
    see ``_gauge_label_has_visible_text``), the numeric percentage as visible
    text instead, regardless of which band, or whether any band, resolved. A
    caller cannot construct a threshold-banded gauge whose value is not also
    paired with visible text, because the template does not expose a way to
    omit that text node."""
    if threshold_bands is None:
        return "accent"
    if not isinstance(threshold_bands, list | tuple):
        raise TemplateSyntaxError(f"bw_gauge threshold_bands must be a list/tuple of mappings, got {threshold_bands!r}")
    if not threshold_bands:
        return "accent"
    parsed: list[tuple[Decimal, str]] = []
    for raw_band in threshold_bands:
        if not isinstance(raw_band, Mapping):
            raise TemplateSyntaxError(f"bw_gauge threshold_bands entries must be mappings, got {raw_band!r}")
        band_max = _gauge_numeric(raw_band.get("max"), name="threshold_bands max")
        token = raw_band.get("token")
        if token not in _GAUGE_THRESHOLD_TOKENS:
            raise TemplateSyntaxError(
                f"bw_gauge threshold_bands token must be one of {sorted(_GAUGE_THRESHOLD_TOKENS)}, got {token!r}"
            )
        parsed.append((band_max, token))
    parsed.sort(key=lambda band: band[0])
    for band_max, token in parsed:
        if percent <= band_max:
            return token
    # every band's max is below the current percent: the highest band wins,
    # matching a "90+ is success" band still applying at exactly 100.
    return parsed[-1][1]


# Tags whose own text content is never rendered on screen, only exposed to
# assistive technology (title/desc) or not rendered as text at all
# (script/style): a plain strip-the-tags-keep-the-text approach (this
# function's own first version, django.utils.html.strip_tags) cannot
# distinguish "this text is on screen" from "this text is somewhere in the
# subtree", so mark_safe("<svg><title>73%</title></svg>") read as visible
# text when it is, by definition, an accessible name a sighted user never
# sees (found by adversarial review after the first COL-030 fix landed,
# icvoss/django-brickwork COL-030). <img alt="..."> also carries text that
# is never a text NODE (it lives in an attribute), which strip_tags happened
# to discard for the unrelated reason that it discards all attributes.
#
# <template> and <noscript> were added after a further adversarial pass
# found both render with an empty innerText and zero height in a real
# browser (Chromium, verified directly rather than reasoned from the spec
# alone). <template> content is the HTML5 "template contents", an inert
# DocumentFragment that is never inserted into the rendered document by
# parsing alone; nothing under it is ever on screen unless a caller's own
# script clones and appends it, which this function cannot assume happened.
# <noscript> is the mirror case: the HTML5 parsing spec places its content
# in the "in head noscript"/"in body" insertion modes as literal, inert TEXT
# when the "scripting flag" is enabled, which is the ordinary case for any
# real browser with JavaScript on; only a scripting-disabled context (fixed
# by the same spec) exposes and renders it. This package's own audience is a
# sighted user in an ordinary browser with scripting enabled, so treating
# <noscript> content as non-visible matches that browser's actual DEFAULT
# rendering, not an unusual configuration.
_GAUGE_LABEL_NON_VISIBLE_TEXT_TAGS = frozenset({"title", "desc", "script", "style", "template", "noscript"})

# The HTML5 VOID elements: by spec they can never have content (no closing
# tag, nothing nested inside), so they can never themselves wrap visible
# text and correctly never push a hiding state that would need popping.
# Hand-enumerated, deliberately, rather than reached for a stdlib constant:
# xml.etree.ElementTree.HTML_EMPTY exists but is an undocumented internal
# detail of that module's own (deprecated) legacy HTML serialiser, not a
# published "void elements" API, and its contents differ from the current
# HTML5 spec (it also carries basefont/frame/isindex/param, obsolete HTML4
# elements the current spec does not call void). Unlike the Unicode Cf
# category used elsewhere in this function, where new characters are
# assigned over time and a hand-enumerated set goes stale, the HTML5 void
# element set is fixed by spec (WHATWG "void elements"): this list is not
# expected to grow.
_GAUGE_LABEL_VOID_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
)


class _GaugeLabelVisibleTextExtractor(HTMLParser):
    """Collect only the text a sighted user would actually see when
    ``gauge_label`` is rendered: text inside ``_GAUGE_LABEL_NON_VISIBLE_TEXT_TAGS``
    (accessible-name-only or non-text elements) and text inside any element
    carrying ``aria-hidden="true"`` or the boolean ``hidden`` attribute is
    excluded, everything else is kept, mirroring the same "own tag or any
    ancestor" hiding shape ``tests/_encoding_contract.py`` already checks for
    on the RENDERED side of this same component family.

    Depth-tracked with a stack rather than a bare counter so a hidden
    element's CLOSE only clears its own contribution: a counter that merely
    incremented and decremented on tag name would also un-hide text that
    follows a hidden sibling once a same-named tag anywhere closed.

    VOID elements (``<br>``, ``<img>``, and the rest of
    ``_GAUGE_LABEL_VOID_TAGS``) never push onto the hidden stack at all,
    whether or not they carry ``aria-hidden``/``hidden``: ``HTMLParser``
    never calls ``handle_endtag`` for a void element written without a
    trailing slash (``<br aria-hidden="true">``, the ordinary spelling), so
    pushing there and relying on a later pop left the stack permanently one
    entry too deep, treating every sibling AFTER the void element as hidden
    for the rest of the document (found by a further adversarial pass,
    icvoss/django-brickwork COL-030). A void element can never have content
    by the HTML5 spec (no closing tag, nothing nested inside it), so its own
    hiding attributes are correctly irrelevant here regardless: there is no
    text inside it that could need hiding, so not pushing for it loses
    nothing. ``handle_startendtag`` (an explicit self-closing spelling,
    ``<br aria-hidden="true"/>``, or a non-void tag mistakenly self-closed,
    ``<span aria-hidden="true"/>``) is NOT overridden separately: the base
    class's own default implementation calls ``handle_starttag`` then
    ``handle_endtag`` in sequence for it, which is already exactly correct
    once ``handle_starttag``/``handle_endtag`` are themselves correct, since
    a self-closed element has no body either.

    This failure mode is checked and confirmed to run in the SAFE direction
    for every case exercised: unbalanced or void-heavy markup either loses a
    caller's own label text (falls back to the number early) or leaves it
    intact, but never the reverse (suppressing the number while the arc
    keeps its threshold colour, which is the actual COL-030 violation this
    whole function exists to prevent). A parser that pushed but never popped
    correctly, as this one did before this fix, still failed on the SAFE
    side of that line: it over-hid text, which forces MORE fallbacks to the
    number, not fewer.

    ``convert_charrefs=True`` (the parser's own default from Python 3.5) also
    replaces the earlier separate ``html.unescape`` call: entities are
    decoded once, during parsing, rather than as a second pass afterwards."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self._non_visible_depth = 0
        self._hidden_stack: list[bool] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _GAUGE_LABEL_VOID_TAGS:
            # no handle_endtag will ever arrive for this tag (no slash), and
            # it can carry no content anyway: contribute nothing to either
            # stack rather than push an entry that would never be popped.
            return
        attrs_dict = dict(attrs)
        if tag in _GAUGE_LABEL_NON_VISIBLE_TEXT_TAGS:
            self._non_visible_depth += 1
        is_hidden = attrs_dict.get("aria-hidden") == "true" or "hidden" in attrs_dict
        self._hidden_stack.append(is_hidden)

    def handle_endtag(self, tag: str) -> None:
        if tag in _GAUGE_LABEL_VOID_TAGS:
            # nothing was pushed for this tag in handle_starttag; nothing to
            # pop. A real browser's parser does not treat a stray closing
            # tag for a void element (malformed input) as balancing some
            # OTHER element's opening tag either, so doing nothing here is
            # the correct, conservative response, not merely a no-op default.
            return
        if tag in _GAUGE_LABEL_NON_VISIBLE_TEXT_TAGS and self._non_visible_depth > 0:
            self._non_visible_depth -= 1
        if self._hidden_stack:
            self._hidden_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._non_visible_depth == 0 and not any(self._hidden_stack):
            self.chunks.append(data)


def _gauge_label_has_visible_text(gauge_label: object) -> bool:
    """Whether ``gauge_label`` carries text this function can identify as
    visible under HTML's DEFAULT rendering, absent any CSS the caller applies.

    That wording is the honest scope, not hedging. "Is this text visible" is a
    LAYOUT question and this is a PARSE-TREE instrument, so the two can never
    fully meet: no markup-only check can see a stylesheet rule, a zero-size
    ancestor, ``text-indent: -9999px``, ``visibility: collapse``, or a clip
    path. Seven rounds of this guarantee leaking were each a case where the
    true answer needed rendering, and each fix narrowed the approximation
    without closing it, because the target property is not decidable from
    markup alone.

    So ``_GAUGE_LABEL_NON_VISIBLE_TEXT_TAGS`` is EMPIRICAL and dated, not a
    spec table transcribed. It happens to converge with three separate spec
    mechanisms rather than one: HTML's default UA stylesheet ``display: none``
    set, ``<noscript>``'s parsing-mode rule (its content is inert text
    whenever scripting is enabled, the ordinary case), and SVG's own
    accessible-name elements, which the HTML UA stylesheet does not cover at
    all. Deriving the list from any one of those would swap a hand-built list
    for a differently-sourced one, still finite, still missing the others.

    What makes this safe despite being incomplete is the FAILURE DIRECTION,
    which is asserted and tested rather than hoped for: a case this cannot
    detect degrades to discarding the caller's label in favour of the number.
    That is a correctness annoyance, never the COL-030 violation the guarantee
    exists to prevent. Over-hiding forces MORE fallbacks, never fewer.

    The rest of the reasoning, "stripped, not merely truthy", is the same ``bw_chart_mount`` applies to ``aria_label``
    (see that tag's own comment): a whitespace-only string is truthy in
    Python and is not visible text, so testing truthiness alone would let
    ``{% if gauge_label %}`` render an empty-looking label with no numeric
    fallback, which is exactly the COL-030 defect this function exists to
    close (icvoss/django-brickwork COL-030).

    A defect HERE has two distinct failure directions, and only one of them
    is the COL-030 violation: returning ``True`` for a label with no real
    visible text (the number gets suppressed while the arc keeps its
    threshold colour, meaning riding on colour alone) versus returning
    ``False`` for a label that DOES carry visible text (a legitimate label
    gets discarded in favour of the number, which is a correctness bug, not
    an accessibility one, since the user still sees a number either way).
    See ``_gauge.html``'s own Accessibility comment for the full statement
    of this distinction and how to apply it when triaging a report against
    this function.

    Unlike ``aria_label``, ``gauge_label`` is a TRUSTED MARKUP slot (VIZ-008):
    a caller may legitimately pass ``mark_safe("<strong>73%</strong>")``, so
    this cannot strip or reject markup the way ``bw_chart_mount`` does.
    Instead it tests for text CONTENT actually rendered on screen, via
    ``_GaugeLabelVisibleTextExtractor`` above, while the caller (``bw_gauge``)
    keeps passing the ORIGINAL value, safe marker intact, to the template.
    This function only answers the yes/no question; it never mutates or
    returns the label itself.

    ``force_str(gauge_label)`` resolves LAZINESS first, before anything else
    runs, because the branch below must see exactly what the template will
    see. A lazily-wrapped safe string (``lazy(lambda: mark_safe(...), str)()``,
    the shape ``gettext_lazy`` and similar produce) is an ordinary object of
    that lazy library's own ``__proxy__`` type: it is not a ``str`` subclass
    and carries no ``__html__`` attribute of its own, so a naive
    ``isinstance(gauge_label, SafeString)`` check reads it as "plain", and a
    naive plain-string branch that never parses markup would then read
    ``<svg><title>73%</title></svg>`` as literal, ordinary characters and
    conclude there is visible text (found by a further adversarial pass,
    icvoss/django-brickwork COL-030). Django's own template variable
    rendering (``django.template.base.render_value_in_context``) resolves
    exactly this shape by calling ``str(value)`` on anything that is not
    already a ``str`` subclass, which is what actually makes the lazy
    wrapper's own ``__html__``-carrying result reach the template's
    ``conditional_escape`` unescaped in the first place; ``force_str`` is the
    named, public Django utility for that same "resolve to what will
    actually be rendered" operation, so using it here rather than a bespoke
    resolution keeps this function's decision aligned with the template's
    own, rather than a second, independently-arrived-at opinion that could
    drift from it.

    Resolving via ``force_str`` does NOT itself repeat the ``.strip()``
    failure mode this function documents below (a genuine string operation
    that builds a fresh, unmarked ``str`` even when its input was safe):
    ``force_str`` returns its argument UNCHANGED, by identity, when it is
    already a ``str`` subclass (``issubclass(type(s), str): return s``), and
    only falls through to a real ``str(s)`` call for a non-``str``-subclass
    input. For the lazy case that matters here, ``str()`` on a
    ``str``-resultclass lazy proxy invokes the wrapped callable and then
    ``str()``s ITS result: if that result is already a ``SafeString`` (a
    ``str`` subclass), THAT ``str()`` call is also an identity return by the
    same rule, so the ``SafeString`` marker survives the whole resolution
    intact, verified directly (``force_str(lazy(lambda: mark_safe(...), str)())``
    returns a ``SafeString``, not a downgraded plain ``str``) rather than
    assumed from reading the source alone.

    Unlike ``aria_label``, ``gauge_label`` is a TRUSTED MARKUP slot (VIZ-008):
    a caller may legitimately pass ``mark_safe("<strong>73%</strong>")``, so
    this cannot strip or reject markup. The parser runs ONLY when the
    RESOLVED value is a ``SafeString``: that is exactly the condition under
    which the template will render it as real markup rather than
    auto-escaped text (``_gauge.html``'s own ``{{ gauge_label }}`` still
    auto-escapes an ordinary ``str``, matching every other Django template
    variable). A plain ``str`` gets the simpler "unescape entities, strip,
    test for a Cf-only remainder" check below with no HTML-structural
    interpretation at all, because Django is going to render its literal
    characters as escaped text, not as tags: parsing an UNTRUSTED plain
    string as if it were markup is its own defect, not a safety margin, and
    shipped as one. A caller-typed ``gauge_label="<script>steal()</script>"``
    (no ``mark_safe``, ordinary text that merely contains angle brackets) is
    real, VISIBLE text once escaped to ``&lt;script&gt;...``; running it
    through the tag-aware extractor instead read the literal word "script"
    as a real ``<script>`` element, discarded its text content by the same
    rule that correctly discards a genuine trusted ``<script>``, and wrongly
    forced the numeric fallback over the caller's own escaped text. Found by
    rerunning this fix's own pre-existing test suite before reporting it as
    done, which is exactly the "verify your own report" habit that catches a
    defect a per-case teeth-check on the intended cases alone would not:
    none of the round-two defect cases are a plain string, so a teeth-check
    limited to them would not have exercised this branch at all.

    An object defining only ``__html__`` (no ``mark_safe``, no ``SafeString``
    subclass, e.g. a hand-written class with an ``__html__`` method and no
    ``__str__``) is deliberately NOT treated as markup here, and this is
    correct rather than a gap: Django's own ``render_value_in_context``
    converts such an object with a bare ``str(value)`` BEFORE
    ``conditional_escape`` ever runs (since it is not a ``str`` subclass),
    which discards access to ``__html__`` entirely, so the template renders
    it as escaped plain text too. Verified by rendering ``{{ v }}`` directly
    for such an object rather than reasoned about from
    ``conditional_escape``'s own logic in isolation: ``conditional_escape``
    alone WOULD honour ``__html__`` on any object carrying it, which is a
    different and wider rule than what the template's variable-output path
    actually applies, and trusting that wider rule here would have "fixed" a
    case that was never broken.

    A real HTML parser (the stdlib's ``html.parser.HTMLParser``, no new
    dependency), not ``django.utils.html.strip_tags`` plus a text scrape, for
    the SafeString branch: the first version of this function used exactly
    that combination and passed every case in the original defect report,
    but a later adversarial pass found ``strip_tags`` keeps the TEXT CONTENT
    of elements it cannot render visibly, only discarding the tags
    themselves, so ``mark_safe("<svg><title>73%</title></svg>")`` read as
    visible text when a sighted user never sees it (an SVG ``<title>`` is an
    accessible name only). A regex-based fix for that one shape would have
    been the same "enumerate what I've seen so far" defect the
    ``&nbsp;``/format-character fix below already rejects; a real parser
    tracking element nesting is the proportionate tool once the property
    being tested depends on WHERE in the tree a character sits, not merely
    which characters they are.

    Deliberately NOT a general accessibility-tree resolver: the SafeString
    branch only answers "does this trusted markup contain any visible text",
    via the four named non-visible-text tags and the
    ``aria-hidden``/``hidden`` attributes, the same named, closed set
    ``tests/_encoding_contract.py`` already documents as this codebase's
    honest boundary for a markup-level check (its own module docstring: five
    named hiding mechanisms, not "every way an element can be hidden"). A
    CSS rule hiding the label via an external stylesheet selector
    (``<style>.bw-gauge__label{display:none}</style>``) is genuinely outside
    what parsing markup can resolve, since that needs a real CSS cascade,
    and is not attempted here (see the encoding-contract test coverage table
    in the test suite for what closes that gap instead).

    After extracting the visible text (the SafeString branch) or unescaping
    entities (the plain-string branch), a string is still treated as empty
    when every remaining character is Unicode general category ``Cf``
    ("format"): zero-width space, zero-width non-joiner, the BOM and the
    word joiner are all ``Cf`` and render as literally nothing on screen, the
    same invisible-to-a-sighted-user argument the ``&nbsp;`` handling already
    makes one category over (``Zs``, "space separator", which ``.strip()``
    already removes on its own). Checked via
    ``unicodedata.category(ch) == "Cf"`` per character, deliberately not a
    hand-enumerated set of the four characters named above: ``Cf`` is a
    stable Unicode property covering every current and future format
    character, and an enumeration goes stale the moment a fifth one is used.

    ``None`` is guarded explicitly first: an unguarded ``str(None)`` would
    be fed onward as the literal four-character text ``"None"``, which would
    wrongly test as visible text."""
    if not gauge_label:
        return False
    # Resolve laziness BEFORE the isinstance check, not after: the branch
    # below must see what the template will see, and force_str is a no-op
    # (returns the same object) for anything already a str subclass, so this
    # costs nothing for the ordinary str/SafeString cases the rest of this
    # function was already written for.
    resolved_label = force_str(gauge_label)
    if isinstance(resolved_label, SafeString):
        extractor = _GaugeLabelVisibleTextExtractor()
        extractor.feed(str(resolved_label))
        visible_text = "".join(extractor.chunks).strip()
    else:
        # A plain str is never parsed as markup: the template auto-escapes
        # it verbatim, so this only needs entity-decoding (the "&nbsp;"
        # shape, unlikely but not impossible in caller-typed plain text) and
        # a strip, exactly as bw_chart_mount's own aria_label.strip() does.
        visible_text = unescape(resolved_label).strip()
    return any(unicodedata.category(ch) != "Cf" for ch in visible_text)


@register.inclusion_tag("brickwork/components/_gauge.html")
def bw_gauge(
    *,
    value: object,
    min: object = 0,  # shadows the builtin `min`, deliberately: VIZ-007 names the public kwarg min/max/value
    max: object = 100,  # shadows the builtin `max`, deliberately: see `min` above
    label: str = "",
    size: str = "md",
    threshold_bands: object = None,
    gauge_label: str | SafeString = "",
    data: object = None,
) -> dict:
    """A circular progress ring (VIZ-007 to VIZ-010): one quantity read
    against a fixed ``min``/``max``, rendered as an SVG ``<circle>`` whose
    ``stroke-dasharray``/``stroke-dashoffset`` encode the percentage. No JS
    or canvas: the arc is pure CSS-driven SVG, geometry computed HERE in
    Python (mirroring ``bw_ranked_list``'s own promotion from a plain
    include), never left to the template to build a dash string. A TAG,
    not an ``{% include %}``, for the same reason ``bw_ranked_list`` is one:
    ``min``/``max``/``threshold_bands`` need real validation against a
    render-time TemplateSyntaxError, which an include has no seam for
    (ADR-060 rule 2).

    Required context:
      value: the reading, numeric (int/float/Decimal/numeric string).
    Optional:
      min (default 0), max (default 100): the fixed range ``value`` reads
          against. ``max`` must be strictly greater than ``min``, or this is
          a render-time TemplateSyntaxError (a zero or negative range has no
          meaningful percentage). ``value`` is clamped into ``[min, max]``
          before the percentage is computed, so an out-of-range reading
          renders a full or empty ring rather than an invalid dash length.
      label: the accessible name (``aria-label``, ``role="img"`` on the SVG
          root, mirroring ``bw_chart_mount``'s CHT-012 contract for a static
          one-shot visual summary rather than a live task-progress control).
          Omitted renders no ``aria-label``: give one when the gauge's
          meaning is not already carried by an adjacent, associated heading.
      size ("sm" | "md" | "lg", default "md", VIZ-010): the ring's rendered
          diameter, via the ``--bw-component-gauge-diameter-*`` component
          token. Any other value is a render-time TemplateSyntaxError
          (ADR-060 rule 2).
      threshold_bands (VIZ-009): a list of ``{"max": <numeric>,
          "token": "accent" | "success" | "warning" | "danger"}`` mappings.
          The arc's colour resolves to the first band (sorted by ``max``
          ascending, computed here) whose ``max`` is at or above the current
          percentage, falling back to the highest band past its max, or
          plain "accent" when omitted, empty, or no percentage-basis
          reading applies. Every token is an EXISTING semantic status
          colour (no new token is authored for this: --bw-color-danger/
          -warning/-success already carry their own meaning, and --bw-
          color-accent is the same ink _progress.html's own determinate
          fill already uses). COL-030 is structural here, not merely
          documented: the resolved token only ever selects a class modifier
          on the decorative, aria-hidden arc, and the numeric percentage
          always renders as visible text regardless of which band (or
          none) resolved, so a threshold colour can never ship without its
          paired visible number.
      gauge_label (VIZ-008, a pre-rendered safe string): overrides the text
          rendered inside the ring. Mirrors ``_stat.html``'s own
          ``sparkline`` seam (a caller-supplied SafeString, brickwork never
          sanitises it, never pass unescaped user input here) rather than a
          named block: this is an inclusion tag, and a plain
          ``{% include %}``/inclusion-tag context has no block-filling seam
          the way ``{% extends %}`` does. Omitted (the default), empty, or
          carrying no visible text (whitespace-only, or markup with no text
          content, e.g. ``mark_safe("<span></span>")``) all render the
          computed percentage as ordinary escaped text instead, e.g. "73%"
          (COL-030): the fallback is decided by visible TEXT CONTENT, never
          by truthiness, so a caller cannot accidentally satisfy this seam
          with something that looks empty. A label WITH visible text (plain
          string or markup) always renders the caller's own value verbatim,
          never falls back.
      data: a mapping of consumer-owned ``data-*`` attributes for the gauge
          root (component-level test hooks, mirroring ``_stat.html``'s and
          ``bw_ranked_list``'s own root data seam).

    States: a single populated state (no loading/empty variant: a gauge
      always has a value once rendered, matching ``_progress.html``'s own
      determinate case); the threshold band (if any) changes only the arc's
      colour class, never its markup shape.
    Accessibility: ``role="img"`` with ``aria-label`` from ``label`` when
      given (CHT-012's own reasoning: a bare SVG root maps to no accessible-
      name-bearing role without one). The percentage is ALWAYS rendered as
      visible text inside the ring (COL-030), and the decorative arc/track
      circles are ``aria-hidden="true"`` and carry no text of their own
      (VIZ-015: deliberately no ``role="progressbar"``/``aria-valuenow``,
      since a static, already-resolved reading is not the "toward a live
      target" contract that role implies; that vocabulary belongs to
      ``_progress.html`` alone). Covered by the encoding-contract helpers in
      ``tests/_encoding_contract.py`` (ADR-081), the same machinery
      ``bw_ranked_list`` is proven against, and by axe.spec.mjs against
      gauge-*.html, both themes.
    Responsive: no breakpoint switch; ``size`` is the fixed sm/md/lg token
      scale (VIZ-010), never viewport-driven. Geometry (the SVG viewBox and
      dash maths) is fixed at every size: only the rendered diameter, via
      CSS, changes.
    """
    if size not in _GAUGE_SIZES:
        raise TemplateSyntaxError(f"bw_gauge size must be one of {sorted(_GAUGE_SIZES)}, got {size!r}")
    min_value = _gauge_numeric(min, name="min")
    max_value = _gauge_numeric(max, name="max")
    if max_value <= min_value:
        raise TemplateSyntaxError(f"bw_gauge max ({max_value}) must be strictly greater than min ({min_value})")
    raw_value = _gauge_numeric(value, name="value")
    # The `min`/`max` PARAMETERS above shadow the builtins for the rest of
    # this function body, which is exactly why the clamp below is written as
    # explicit comparisons rather than calling min()/max(): a bare min(...)
    # here would call this function's own `min` argument (a Decimal), not
    # the builtin, and raise TypeError immediately.
    clamped_value = raw_value
    if clamped_value < min_value:
        clamped_value = min_value
    elif clamped_value > max_value:
        clamped_value = max_value
    percent = ((clamped_value - min_value) / (max_value - min_value)) * 100
    if percent < 0:
        percent = Decimal(0)
    elif percent > 100:
        percent = Decimal(100)
    threshold_token = _gauge_threshold_token(percent, threshold_bands)

    # Geometry as floats formatted to a fixed 2-decimal-place pattern (never
    # a Decimal or a caller-influenced string): a value built this way cannot
    # carry a quote character into the style="..." attribute it lands in, so
    # there is nothing here for an escaping step to defend, which is the
    # safe-by-construction property this component is built to (see the
    # module's own worked defect history on _validate_ranked_list_row).
    percent_float = float(percent)
    dash_offset = _GAUGE_CIRCUMFERENCE * (1 - percent_float / 100)

    # ATTRIBUTE position (icvoss/django-brickwork#339): _gauge.html renders
    # this INSIDE the quotes, as aria-label="{{ label }}", with no template
    # filter, so a mark_safe'd label reached that attribute unescaped and
    # closed the quote (the #349 defect class this file's escape_attribute_
    # value already exists for). This is computed from the RAW label
    # parameter, never from a conditional_escape/normalise_accessible_name
    # result, because feeding an already-escaped SafeString into a second
    # unconditional escape() would double-escape it. escape_attribute_value,
    # not normalise_accessible_name: that helper's conditional_escape
    # honours a SafeString's __html__ marker, which is correct for TEXT
    # position (_toggle.html's own `{{ label }}`) but is exactly how a
    # mark_safe'd label closed this attribute in the first place. Stripped,
    # not merely truthy, so a whitespace-only label renders no aria-label at
    # all, matching bw_chart_mount's own aria_label precedent.
    label = escape_attribute_value(label)

    return {
        "label": label,
        "size": size,
        "threshold_token": threshold_token,
        "circumference": f"{_GAUGE_CIRCUMFERENCE:.2f}",
        "dash_offset": f"{dash_offset:.2f}",
        "radius": f"{_GAUGE_VIEWBOX_RADIUS:.2f}",
        "percent_display": str(int(percent.to_integral_value())),
        # The DECISION (has visible text) is computed here, not left to the
        # template's own truthiness test (COL-030 fix): the template branches
        # on this boolean, never on `gauge_label` itself. `gauge_label` below
        # is still the caller's ORIGINAL value, safe marker intact, so a
        # `mark_safe(...)` label renders its markup verbatim rather than
        # escaped; only the boolean decision is derived from a stripped copy.
        "gauge_label_has_text": _gauge_label_has_visible_text(gauge_label),
        "gauge_label": gauge_label,
        "attrs_html": bw_data_attrs(data, "gauge"),
    }


@register.simple_tag
def bw_chart_mount(
    *,
    aria_label: str = "",
    aria_describedby: str = "",
    decorative: bool = False,
    min_height: str = "",
    aspect_ratio: str = "",
    css_class: str = "",
) -> SafeString:
    """The mount point a consumer's own charting engine paints into (CHT-001,
    CHT-011: brickwork never bundles or auto-inits an engine). A TAG, not an
    {% include %}, for exactly one reason: CHT-012's accessible name is
    MANDATORY, and an include-only component cannot make anything required
    (an unfilled context variable renders empty with no error, ADR-083
    section 4). Emits a single ``<div data-bw-chart-mount>`` the consumer's
    own JS selects and mounts a canvas/SVG engine into; brickwork ships no
    chart renderer of its own (matching _stat.html's sparkline seam and
    _data_table.html's no-virtualisation doctrine).

    Accessibility (CHT-012, enforced, modelled exactly on bw_icon's ICO-007
    pairing): the mount is EITHER meaningful (aria_label= or
    aria_describedby=, an accessible summary of the chart, supplied by the
    consumer since only the consumer knows what the chart shows, emitted with
    ``role="img"``) OR decorative (decorative=True -> aria-hidden="true", no
    role).

    ``role="img"`` is load-bearing, not decoration, and removing it silently
    undoes the whole contract: a bare ``<div>`` maps to ARIA's generic role,
    which does not support an accessible name, so ``aria-label`` and
    ``aria-describedby`` on one are ignored by most assistive technology. A
    named mount without a role therefore renders valid markup, passes axe
    (which does not flag a name that is merely ignored), and reaches nobody,
    which is precisely the failure CHT-012 exists to prevent. It shipped that
    way in this tag's first draft and was caught by reading bw_icon's
    contract rather than by any gate.

    The role carries a BOUNDARY worth knowing before you reach for it: it
    makes the mount's descendants presentational, so anything focusable the
    engine paints inside (a keyboard-navigable data point, a drill-down
    control) stays reachable by keyboard while being hidden from assistive
    technology, which is a worse state than either a plain image or a plain
    interactive region. The role is right for the case this contract targets
    and CHT-012 describes: a canvas or SVG that is ONE graphical object to a
    screen reader, whose detail is carried by the chart_data_table fallback
    rather than by traversable children. An interactive chart is a different
    contract that this tag does not yet serve, and it wants its own role and
    its own keyboard story rather than a widened meaning for this one.

    Supplying neither is
    a render-time error: a canvas or SVG the engine paints into has no
    accessible name of its own, so silence here is exactly the WCAG 1.1.1
    defect this tag exists to close. Supplying both is also an error
    (contradictory: a hidden element does not also carry an accessible
    name). The decorative case is legitimate, not a loophole: CHT-012 also
    specifies a chart_data_table fallback rendering the same series as an
    accessible table, so a chart whose data is fully duplicated there is
    genuinely decorative to a screen reader, which never needs the visual
    plot at all once the table exists. Supplying both aria_label and
    aria_describedby (rather than either against decorative) is not an
    error, since the two are not mutually exclusive in HTML: aria_label
    wins and aria_describedby is silently dropped, mirroring how
    _alert.html's icon resolution takes the first of several possible
    sources rather than rendering both.

    Reservation (CHT-024, read d3fa3db before changing this): min_height
    and/or aspect_ratio reserve the mount's box BEFORE the engine's JS
    paints, so first render already occupies its final size and the engine
    mounting in later causes no layout shift. Both are plain CSS length/
    ratio strings (e.g. min_height="20rem", aspect_ratio="16 / 9"), emitted
    as the --bw-chart-mount-min-height / --bw-chart-mount-aspect-ratio
    inline custom properties (matching bw_skeleton's own width/height
    override seam): a caller-supplied CSS length is not markup, so Django's
    ordinary attribute-value escaping inside the style="..." attribute is
    the correct and sufficient protection, same reasoning bw_skeleton's own
    style_attr documents. Neither is required: a component or card that
    already constrains its own box (a fixed-height dashboard tile, say)
    may need neither, and the CSS ships no default of its own to reserve
    (there is no one right chart height), so omitting both renders a mount
    with no inline reservation and whatever height its container gives it.

    css_class: extra CSS classes appended after the base bw-chart-mount
        class, for a caller that needs to compose this with its own layout
        (mirrors bw_icon's own css_class seam).

    Does NOT carry a data=/attrs= passthrough seam (blocked on #308, out of
    scope per ADR-083): the only attributes this tag emits are the ones
    named above, never arbitrary consumer-supplied attributes.
    """
    # Coerced to str before anything else, deliberately with no SafeData gate
    # (unlike normalise_accessible_name's conditional_escape route): str() on
    # an already-str/SafeString value is a no-op (returns the same object,
    # marker and all) and on a non-str value (int, model instance, lazy
    # gettext proxy) resolves it the same way an f-string would
    # (icvoss/django-brickwork#351): a consumer passing aria_label=some_count
    # no longer raises AttributeError from a bare .strip(), which only str
    # has. That is the real defect this coercion fixes.
    #
    # It does NOT, and must not, attempt to preserve a SafeString's marker
    # through to the escape() call below. The .strip() immediately after
    # this str() call already destroys the marker on its own (str.strip()
    # never preserves a str subclass), purely as a side effect of stripping
    # for the whitespace contract two lines down, not as a deliberate
    # security measure: do not treat that marker loss as a defence to rely
    # on, because a future change to how the value is trimmed could stop
    # destroying it without anyone noticing. escape() a few lines down is
    # the deliberate, primary defence regardless of what .strip() does to
    # the marker, and it runs unconditionally: a caller-supplied SafeString
    # is escaped a second time as a result, which has a real, measured cost
    # (a screen reader announces the literal entity text rather than the
    # intended character, see the noqa comment below for the full
    # two-guard picture), accepted against the alternative of trusting the
    # marker, which lets the same mechanism break out of the attribute and
    # execute script. aria_label=/aria_describedby= are accessible names,
    # not markup, and a SafeString is not a supported input for either: pass
    # plain text (e.g. aria_label="Tom & more") and it escapes exactly once.
    #
    # Stripped before testing, not merely truthiness-tested: a whitespace-only
    # aria_label is truthy in Python and is NOT an accessible name to any
    # screen reader, so testing truthiness alone would let a consumer satisfy
    # a hard-required check by supplying nothing. A requirement that can be
    # met with " " is not a requirement, and this one exists precisely because
    # an unnamed chart is invisible.
    aria_label = str(aria_label).strip()
    aria_describedby = str(aria_describedby).strip()

    if decorative and (aria_label or aria_describedby):
        raise TemplateSyntaxError(
            "bw_chart_mount: pass either decorative=True or aria_label=/aria_describedby=, not both "
            "(a hidden mount does not also carry an accessible name)."
        )
    if not decorative and not aria_label and not aria_describedby:
        raise TemplateSyntaxError(
            "bw_chart_mount requires either aria_label=/aria_describedby= (an accessible summary of "
            "the chart) or decorative=True (only when a chart_data_table fallback carries the same "
            "data). A canvas or SVG with no accessible name is invisible to assistive technology "
            "(WCAG 1.1.1, CHT-012)."
        )

    classes = "bw-chart-mount"
    if css_class:
        classes += " " + escape(css_class)

    style_parts = []
    if min_height:
        style_parts.append(f"--bw-chart-mount-min-height: {min_height}")
    if aspect_ratio:
        style_parts.append(f"--bw-chart-mount-aspect-ratio: {aspect_ratio}")
    style_attr = f' style="{escape("; ".join(style_parts))}"' if style_parts else ""

    # role="img" accompanies BOTH naming paths, matching bw_icon's contract
    # (brickwork_icons.py:19). A bare <div> maps to ARIA's generic role, which
    # does not support an accessible name: aria-label and aria-describedby on
    # a generic element are ignored by most assistive technology, so a mount
    # named without a role is exactly the invisible-chart failure CHT-012
    # exists to prevent, in the code enforcing CHT-012. role="img" is correct
    # for the mounted render specifically: a canvas or SVG chart is a single
    # graphical object to a screen reader, and its detail is carried by the
    # chart_data_table fallback rather than by traversable children.
    #
    # The decorative branch takes no role: aria-hidden="true" removes the
    # element from the accessibility tree entirely, so a role on it would
    # describe something nothing can reach.
    if decorative:
        a11y = 'aria-hidden="true"'
    elif aria_label:
        a11y = f'role="img" aria-label="{escape(aria_label)}"'
    else:
        a11y = f'role="img" aria-describedby="{escape(aria_describedby)}"'

    div = f'<div class="{classes}" data-bw-chart-mount{style_attr} {a11y}></div>'
    # noqa justification (S308): every interpolated value above is either a fixed
    # literal (the base class, data-bw-chart-mount, the a11y attribute names) or
    # escape()d caller input (css_class, min_height/aspect_ratio inside
    # style_attr, aria_label/aria_describedby). No untrusted string reaches this
    # SafeString unescaped.
    #
    # escape(), never conditional_escape(): every value here is an ATTRIBUTE
    # VALUE, never markup, and conditional_escape honours __html__, so a
    # SafeString passes through verbatim. That is a real break-out, not a
    # theoretical one: css_class=mark_safe('a" onmouseover="alert(1)') closed
    # the class attribute and landed a handler on the element (this file's
    # bw_data_attrs, above, records the same exploit independently: a
    # SafeString value of '" role="progressbar' rendered a real
    # role="progressbar" onto the element it escapes, "because the value
    # reaches the same markup position"), and
    # aria_label=mark_safe('a" onmouseover="alert(1)') does exactly the same
    # thing to the a11y attribute (icvoss/django-brickwork#351).
    #
    # This is unconditional, and it has a real, measured cost: a
    # caller-supplied SafeString (e.g. aria_label=format_html("Tom {} more",
    # "&")) IS escaped a second time here, rendering aria-label="Tom &amp;amp;
    # more" rather than "Tom &amp; more" (see
    # test_safestring_is_escaped_again_because_an_attribute_is_not_markup).
    # An attribute value is decoded by the browser before assistive
    # technology reads it, so this is not cosmetic: a screen reader announces
    # the literal characters "&amp;" instead of "&", corrupting the
    # accessible name it exists to carry. That cost is accepted against the
    # alternative: there is no way to distinguish, from the SafeString alone,
    # "pre-escaped entities from a trusted helper" from "attacker-supplied
    # attribute-breaking characters wrapped in mark_safe", so honouring the
    # marker to avoid the corruption would also honour it for
    # mark_safe('a" onmouseover="alert(1)'), which breaks out of the
    # attribute and executes script. A corrupted announcement is accepted
    # over arbitrary script execution.
    #
    # The consequence for a caller: a SafeString is not a supported input for
    # aria_label=/aria_describedby=, because an accessible name is not
    # markup. Pass plain text (e.g. aria_label="Tom & more"), which escapes
    # exactly once and announces correctly.
    #
    # escape() here is the deliberate, PRIMARY defence, and it is the one to
    # preserve. Do not replace it with conditional_escape() and do not remove
    # it on the grounds that something upstream appears to make it redundant.
    #
    # It currently LOOKS redundant, which is the trap this note exists to
    # close. str(value).strip() above degrades a SafeString to a plain str
    # (str.strip() never preserves a str subclass), so by the time this line
    # runs the marker is already gone, and escape() and conditional_escape()
    # would behave identically on the result: forcing conditional_escape()
    # here still blocks the break-out, because the strip removed the marker,
    # NOT because conditional_escape() is safe in this position.
    #
    # That redundancy is a coincidence of today's strip() call, not a
    # designed-in second defence. The marker loss is incidental to an
    # unrelated purpose (the whitespace contract a few lines up, which needs
    # .strip() for reasons that have nothing to do with HTML safety), so a
    # future edit changing HOW the value is stripped, trimmed or normalised
    # could stop destroying the marker without anyone noticing, at which
    # point escape() is the only thing between a SafeString and a live
    # break-out. Lean on the coincidence and the seam fails silently and
    # much later.
    #
    # Because the marker is already gone, no black-box test can tell escape()
    # from conditional_escape() here, so the requirement is pinned by
    # test_interpolation_uses_escape_not_conditional_escape instead.
    return mark_safe(div)  # noqa: S308


# CHT-013's mode vocabulary, CLOSED and enforced (ADR-060 rule 2). Adjacent to
# bw_chart_data_table below, matching where _TRIGGER_MODES/_TRIGGER_VARIANTS sit
# relative to their own tags in brickwork_interactions.py.
#
# A closed vocabulary is currently doing invisible escaping duty at several
# sites across this package (ADR-084 section 6): because a value is validated
# against a fixed set before it is ever interpolated, it cannot carry consumer
# markup, so the site "happens to be safe" without any escaping seam being
# visible in the code. That is a real property here too, since a
# data_table_mode reaching the template is guaranteed to be one of exactly
# three literals. It is deliberately NOT relied on: the value is routed
# through the ordinary template seam like every other context value, so the
# safety of this site is stated by the seam rather than inferred from a
# validation several lines away. Reasoning about safety by tracing which
# earlier check makes an interpolation harmless is exactly the analysis that
# fails silently when someone later widens the set, moves the check, or copies
# the interpolation to a site with no check at all.
_CHART_DATA_TABLE_MODES = frozenset({"hidden", "toggle", "visible"})


@register.simple_tag
def bw_chart_data_table(
    *,
    caption: str = "",
    columns: object = (),
    rows: object = (),
    data_table_mode: str = "hidden",
    toggle_label: str = "",
) -> SafeString:
    """CHT-012's data-table fallback: the same series a chart plots, rendered
    as a plain semantic table so a screen reader reaches the DATA a canvas or
    SVG cannot expose, with CHT-013's ``data_table_mode`` choosing how it is
    presented visually.

    THE SIBLING RULE, the load-bearing design decision
    (icvoss/django-brickwork#326). The table this tag renders is a SIBLING of
    the chart mount, never a descendant of it, and ``_chart_card.html`` places
    it that way. The reason is ARIA, not layout: ``bw_chart_mount`` emits
    ``role="img"``, and ``role="img"`` makes every descendant of the mount
    PRESENTATIONAL, so a ``<table>`` rendered inside the mount is unreachable
    to assistive technology no matter how well formed it is. That is not a
    reason CHT-012 cannot be implemented; it is precisely the reason the
    fallback must sit OUTSIDE the mount.

    Read the other way round, the rule is self-evident: the mount is opaque
    BECAUSE it is one graphical object, and this table exists to carry exactly
    what an opaque object cannot. Placing the table inside the thing whose
    opacity it compensates for would be self-defeating.

    #326 is therefore NOT a blocker for CHT-012, and this tag does NOT resolve
    #326 and must not be read as resolving it. #326 is a DIFFERENT unserved
    case: an interactive chart whose engine paints focusable, traversable
    children, which wants its own role and its own keyboard story rather than
    a widened meaning for ``role="img"``. The sibling placement is exactly
    what lets CHT-012 ship correctly while #326 stays open, and it widens
    nothing: ``role="img"`` keeps meaning "one graphical object", and the
    table beside it keeps meaning "the data".

    A TAG rather than an ``{% include %}``, for the same reason
    ``bw_chart_mount`` is one: ``data_table_mode`` is a closed vocabulary and
    an include-only component cannot validate anything (an unrecognised value
    reaches the template verbatim, silently selects no branch and renders the
    wrong thing, ADR-060 rule 2, the failure ``_chart_card.html``'s own
    ``legend_position`` documents as its accepted cost).

    A ``simple_tag`` rather than an ``inclusion_tag``, following
    ``bw_sparkline``'s own precedent in this module and for the same reason:
    the output is composed by the caller rather than placed by it. A caller
    writes ``{% bw_chart_data_table ... as table %}`` and hands the result to
    ``_chart_card.html``'s ``data_table`` context variable, and Django's
    ``inclusion_tag`` cannot do ``as var`` at all (its parser reads ``as`` as
    a positional argument after keywords and raises), so registering it that
    way would make the documented call unwritable.

    caption: the table's accessible name, rendered as a real ``<caption>``.
        Required in substance: a table with no caption is announced as an
        anonymous grid of numbers, which is the same WCAG 1.1.1 failure the
        unnamed mount is. Whitespace-only is treated as absent, matching
        ``bw_chart_mount``'s own aria_label contract: a requirement that can
        be met with " " is not a requirement.
    columns: the column header labels, in order, as a list/tuple. The FIRST
        entry labels the row-header column (the category axis, e.g. "Month");
        the rest label the series columns.
    rows: a list/tuple of row sequences. Each row's first cell is that row's
        header (``<th scope="row">``), the remaining cells are data
        (``<td>``). Column and row headers together are what make each cell
        announce with both of its coordinates instead of as a bare number.
        The list/tuple shape is checked and raises, rather than being
        rendered as given, because the wrong shape fails SILENTLY otherwise: a
        flat list of values passed as ``rows`` makes the template iterate each
        value's characters, rendering a table of single letters that raises
        nowhere and looks like a data bug rather than a call-site one.
    data_table_mode ("hidden" default | "toggle" | "visible", CHT-013):
        "hidden" renders the table visually hidden but present in the
        accessibility tree (the ``bw-visually-hidden`` clip-path pattern,
        never ``display: none``, which would remove it from that tree and
        defeat the whole contract); "visible" renders it plainly, as the
        base state with no wrapper; "toggle" composes ``_disclosure.html``'s
        native ``<details>``, whose no-JS floor holds by construction
        (BR-BW-HTMX-001: that component ships no JavaScript at all).
    toggle_label: the ``<summary>`` text, used in "toggle" mode only and
        ignored in the other two. Blank in toggle mode falls back to a
        translated default rather than rendering an unlabelled disclosure
        control.

    Escaping (ADR-084). Every consumer value this tag takes lands in TEXT
    position, never in an attribute, and every one of them is escaped by
    ``_chart_data_table.html``'s own auto-escaping at the point it is
    interpolated. This tag therefore passes ``caption``, ``columns``, ``rows``
    and ``toggle_label`` through RAW: pre-escaping them here and then letting
    the template escape the result again is the documented double-escape trap,
    and it is the trap this direction of the seam falls into
    (``normalise_accessible_name``'s own docstring records it from the
    opposite direction). ``escape_attribute_value`` has no site in this tag at
    all, because no value here reaches an attribute value; a future change
    that puts one there (a caller-supplied id, say) must derive a SECOND value
    from the RAW input for that position rather than reusing one of these.

    One consequence, stated because it is the thing a reader will want to
    check: a ``mark_safe``/``format_html`` value passed as a caption, a column
    header, a cell or a toggle label renders as MARKUP, because text position
    is exactly where a safe marker means something. That is the ordinary
    text-position rule every other slot in this package follows, not a hole,
    and it is the deliberate opposite of ``bw_chart_mount``'s ``aria_label``,
    which is an attribute value where the marker is meaningless and
    ``escape()`` runs unconditionally. An ordinary consumer string (a DB
    value, a form field, a computed label) is never ``SafeData`` and is
    escaped normally. The blankness checks below therefore test a stripped
    COPY and render the ORIGINAL, so this rule holds uniformly across all four
    arguments rather than varying with which of them happens to be stripped.
    """
    if data_table_mode not in _CHART_DATA_TABLE_MODES:
        raise TemplateSyntaxError(
            f"bw_chart_data_table data_table_mode must be one of {sorted(_CHART_DATA_TABLE_MODES)}, "
            f"got {data_table_mode!r}"
        )

    # The blankness DECISION is computed from a stripped copy; the value
    # actually rendered stays the caller's ORIGINAL. This split is deliberate
    # and it is the _gauge.html gauge_label precedent in this module
    # (`gauge_label_has_text`), applied for the same reason.
    #
    # Why a stripped copy for the decision: a whitespace-only caption is truthy
    # in Python and is not an accessible name to any screen reader, so a bare
    # truthiness test would let a consumer satisfy a hard requirement by
    # supplying nothing (bw_chart_mount's own aria_label contract, above). str()
    # first, so a non-str value (an int, a lazy gettext proxy, a model instance)
    # resolves rather than raising AttributeError from a bare .strip(), which
    # only str has (icvoss/django-brickwork#351).
    #
    # Why the ORIGINAL is what gets rendered, rather than the stripped copy: a
    # caption lands in TEXT position, where a SafeString means "trusted markup"
    # and the template's auto-escaping honours it. str().strip() silently
    # DEGRADES a SafeString to a plain str (str.strip() never preserves a str
    # subclass), so rendering the stripped copy would escape a mark_safe caption
    # while leaving a mark_safe column header or cell (neither of which is
    # stripped) rendering as markup. That divergence would be invisible at the
    # call site and decided by which argument a value happened to land in,
    # rather than by its position in the output, which is the property that is
    # actually supposed to govern escaping in this package.
    #
    # Deliberately NOT normalise_accessible_name, for either purpose: that
    # helper conditionally escapes and re-wraps in mark_safe, which is right for
    # a value the CALLER interpolates itself. Here the value is handed to a
    # template that escapes it in text position, so pre-escaping it would
    # double-escape it (the trap that helper's own docstring records, hit from
    # this direction).
    if not str(caption).strip():
        raise TemplateSyntaxError(
            "bw_chart_data_table requires caption=, the table's accessible name. A fallback table with "
            "no caption is announced as an anonymous grid of numbers, which is the same WCAG 1.1.1 "
            "failure an unnamed chart is (CHT-012)."
        )

    # Shape-checked before use, and raising rather than rendering a wrong-shaped
    # table, matching bw_ranked_list's own rows= check in this module. The
    # failure this prevents is specific: a caller passing a flat list of values
    # instead of a list OF ROWS gets each value iterated character by character
    # by the template's {% for cell in row %}, producing a table of single
    # letters that renders cleanly and errors nowhere. A str is the exact shape
    # that does this, which is why the row check is an isinstance test rather
    # than a bare "is it iterable".
    if not isinstance(columns, list | tuple):
        raise TemplateSyntaxError(f"bw_chart_data_table columns must be a list/tuple of labels, got {columns!r}")
    if not isinstance(rows, list | tuple):
        raise TemplateSyntaxError(f"bw_chart_data_table rows must be a list/tuple of row sequences, got {rows!r}")
    for index, row in enumerate(rows):
        if not isinstance(row, list | tuple):
            raise TemplateSyntaxError(
                f"bw_chart_data_table rows[{index}] must be a list/tuple of cells, got {row!r}. A flat list "
                "of values renders each one character by character, which produces a table of single "
                "letters and raises nowhere."
            )

    # Materialised into lists so a one-shot iterator (a queryset's own lazy
    # sequence, say) is not silently exhausted by the first of the two renders
    # below. The table partial is rendered once, but "rendered once" is a
    # property of today's control flow rather than of the argument.
    columns = list(columns)
    rows = [list(row) for row in rows]

    if data_table_mode == "toggle":
        # A blank toggle_label in toggle mode would render an unlabelled
        # <summary>, i.e. a focusable control with no accessible name (WCAG
        # 4.1.2), so it falls back rather than rendering empty. gettext, not
        # gettext_lazy: the value is used immediately, in this call, and the
        # module already imports the eager form for the same reason
        # (_data_table.html's own "Select all rows" is the template-side
        # {% translate %} equivalent of this).
        #
        # The blankness decision is computed from a stripped copy while the
        # ORIGINAL is what gets rendered, exactly as caption above, and for the
        # same reason: str().strip() would degrade a SafeString and escape a
        # value that the identically-positioned column headers and cells render
        # as markup. Only the fallback branch substitutes a new value, and that
        # one is package-authored text, never consumer data.
        toggle_label = toggle_label if str(toggle_label).strip() else gettext("View as table")

    # The table markup is built by the TEMPLATE, never assembled here as an
    # f-string, which is the whole reason this tag needs no noqa: S308
    # justification of its own the way bw_chart_mount's hand-built <div> does.
    # Two renders of one file: the `table` partial produces the <table> on its
    # own, because _disclosure.html's `content` contract takes PRE-RENDERED
    # HTML, and the outer render then wraps that SafeString per mode.
    #
    # The value handed between them is markup by construction, not a trusted
    # consumer value: every caption, header and cell inside it was escaped
    # exactly once, in text position, by the partial's own auto-escaping. The
    # outer render only wraps it, so no value is escaped twice anywhere in
    # this composition.
    #
    # No mark_safe() around table_html, deliberately: render_to_string already
    # returns a SafeString (its return value is a rendered template, which is
    # markup by definition), so re-marking it would be a no-op that reads like
    # a security decision and invites the next reader to look for the untrusted
    # value it is supposed to be vouching for. The safe marker matters here:
    # without it {{ table_html }} in the wrapper template would escape the
    # whole table into visible <table> text, which is the failure mode to
    # watch for if this ever stops being a template render.
    table_html = render_to_string(
        "brickwork/components/_chart_data_table.html#table",
        {"caption": caption, "columns": columns, "rows": rows},
    )
    return render_to_string(
        "brickwork/components/_chart_data_table.html",
        {"mode": data_table_mode, "table_html": table_html, "toggle_label": toggle_label},
    )


@register.inclusion_tag("brickwork/components/_ranked_list.html")
def bw_ranked_list(
    rows: object,
    *,
    basis: str = "max",
    label: str = "",
    loading: bool = False,
    empty_heading: str = "",
    empty_body: str = "",
    empty_action_href: str = "",
    empty_action_label: str = "",
    data: object = None,
) -> dict:
    """A ranked bar list (icvoss/django-brickwork#183): an ordered ``<ol>`` of
    label/value rows, each paired with a proportional decorative bar. The
    rank order IS the meaning (a leaderboard, a top-N breakdown), which is
    why the semantic root is an ordered list rather than a plain list or a
    set of per-row progressbars (see Accessibility below).

    Required context:
      rows: a non-empty list of mappings (ignored while loading=True or when
          empty, see below). Each row requires "label" (str) and "amount"
          (numeric, drives the bar's geometry). Optional per row:
            value: a pre-formatted display string. The package never formats
                numbers (VIZ-020: locale, currency and precision are consumer
                decisions); omitted renders the raw amount as text.
            href: the row becomes an anchor (VIZ-024). Omitted renders a
                plain, never clickable-looking, row.
            data: a mapping of consumer-owned data-* attributes for the row
                (test/lightweight-JS hooks), via the same bw_data_attrs seam
                _stat.html and _data_table.html use; a str value (an unset
                context variable under string_if_invalid) is treated as
                "not supplied", never an error (brickwork#80).
    Optional:
      basis ("max" default | "total"): the closed vocabulary the bar geometry
          is computed against. "max" reads as a leaderboard (the largest row
          fills the bar track); "total" reads as a share of the whole (rows
          sum toward 100%). Any other value is a render-time
          TemplateSyntaxError (ADR-060 rule 2: a typo here must not ship a
          silently wrong bar). Geometry is computed in PYTHON, never left to
          the template to build a percentage string; a zero or negative
          denominator (every amount non-positive, under basis="max") degrades
          every bar to zero-width rather than raising or emitting a malformed
          calc(). basis="total" additionally requires every amount to be
          non-negative: share-of-total is undefined with mixed signs (a
          negative row can otherwise push the sum to zero or below while
          individual rows are still genuinely positive), so a negative
          amount with basis="total" is a render-time TemplateSyntaxError. A
          negative amount is fine under basis="max": it degrades to a
          zero-width bar and every positive row still renders proportionally
          against the largest amount, since a negative value is never the
          max unless every amount is non-positive.
      label: the accessible name for the list (aria-label on the <ol>).
          Omitted renders no aria-label; give one when the list's heading is
          not already an adjacent, associated heading.
      loading (bool, default False): renders a skeleton row set (STA-004)
          instead of rows; rows is ignored while loading. basis is validated
          regardless of loading (a contract violation, such as a typo'd
          basis, does not become acceptable just because rows are not being
          rendered this call).
      empty_heading, empty_body, empty_action_href, empty_action_label:
          passthrough to _empty_state.html (size="sm", VIZ-021) when rows is
          empty and loading is False. empty_body should always be supplied
          (STA-003); empty_heading is optional at size="sm". The action pair
          renders only when BOTH href and label are given, matching
          _empty_state.html's own action contract.
      data: a mapping of consumer-owned data-* attributes for the list root
          (component-level test hooks, mirroring _stat.html's own root data
          seam).

    States: loading (a skeleton row set stands in for the whole list) and
      empty (zero rows composes _empty_state.html at size="sm", VIZ-021,
      with the empty_* passthrough); otherwise the populated list, each row's
      bar width driven by its computed percent.
    Accessibility: an <ol> (rank order is meaning: VoiceOver/NVDA announce
      "1 of 5", "2 of 5", which a plain <ul> or a div soup never gives for
      free), each row rendering its label and value as VISIBLE text (COL-030:
      the numeric meaning never rides on bar length or colour alone) with the
      bar itself aria-hidden="true" (decorative). Deliberately NOT a
      role="progressbar" per row (VIZ-015): progressbar's accessibility
      contract is for a SINGLE quantity's progress toward a known target
      (aria-valuenow/-valuemin/-valuemax against one goal, exactly
      _progress.html's own case), not an N-way comparison across independent
      rows with no shared "complete" semantics; stamping progressbar role on
      every row would announce a false "toward completion" framing a ranked
      comparison does not have, and COL-030 is already satisfied without it
      by the visible label/value text. Covered by axe.spec.mjs against
      ranked-list-*.html (populated, empty and loading variants), both
      themes.
    Responsive: no breakpoint switch; no width-dependent CSS on any
      .bw-ranked-list* selector. The bar geometry is computed once in Python
      as a fixed 0-100 number and never recomputed client-side, so there is
      no post-load reveal or JS-dependent resize: the list renders its final
      geometry server-side and occupies its full row height and bar width on
      first paint, with zero layout shift.
    """
    if basis not in _RANKED_LIST_BASES:
        raise TemplateSyntaxError(f"bw_ranked_list basis must be one of {sorted(_RANKED_LIST_BASES)}, got {basis!r}")
    if not loading and rows is not None and not isinstance(rows, list | tuple):
        # Checked before the emptiness test below, and regardless of
        # truthiness: rows={} is a falsey non-list/tuple, and without this
        # ordering it silently fell through to the empty-state branch
        # instead of raising, while a non-empty mapping correctly raised
        # (icvoss/django-brickwork adversarial review). rows=None still
        # renders the empty state (see the emptiness test below); only a
        # value that is neither None nor a list/tuple is a contract
        # violation.
        raise TemplateSyntaxError(f"bw_ranked_list rows must be a list/tuple of mappings, got {rows!r}")
    rendered_rows: list[RankedListRow] = []
    if not loading and rows:
        # The isinstance check above already narrowed the only two shapes
        # that can reach here (a non-empty list or tuple), but that
        # narrowing does not carry across into this separate `if`, so it is
        # reasserted for the type checker rather than re-raising a
        # user-facing error twice.
        assert isinstance(rows, list | tuple)
        # Every row's shape is validated (and its amount collected) FIRST,
        # over the whole set, before the denominator is computed: this is
        # what guarantees `amounts` is never empty when a malformed row is
        # present, so _ranked_list_denominator's max()/sum() never sees a
        # bare empty-iterable failure instead of this validator's own
        # TemplateSyntaxError.
        amounts = [_validate_ranked_list_row(raw, basis=basis) for raw in rows]
        denominator = _ranked_list_denominator(amounts, basis)
        rendered_rows = [
            _shape_ranked_list_row(raw, amount=amount, denominator=denominator)
            for raw, amount in zip(rows, amounts, strict=True)
        ]
    # ATTRIBUTE position (icvoss/django-brickwork#339): _ranked_list.html
    # renders this INSIDE the quotes, as aria-label="{{ label }}", with no
    # template filter, so a mark_safe'd label reached that attribute
    # unescaped and closed the quote (the #349 defect class this file's
    # escape_attribute_value already exists for). Computed from the RAW
    # label parameter, never from a conditional_escape/normalise_accessible_
    # name result, which would double-escape. Unlike row.label below (TEXT
    # position inside the <ol>, correctly left raw for the template's own
    # auto-escaping to handle), this list-level label is an accessible name
    # rendered only into an attribute, so it takes escape_attribute_value's
    # unconditional escape() rather than the row values' ordinary escaping.
    # Stripped, not merely truthy, so a whitespace-only label renders no
    # aria-label at all, matching bw_chart_mount's own aria_label precedent.
    label = escape_attribute_value(label)
    return {
        "rows": rendered_rows,
        "label": label,
        "loading": bool(loading),
        "empty_heading": empty_heading,
        "empty_body": empty_body,
        "empty_action_href": empty_action_href,
        "empty_action_label": empty_action_label,
        "attrs_html": bw_data_attrs(data, "ranked list"),
    }


_SPARKLINE_TONES = {"neutral", "trend"}


def _sparkline_path(points: list[float], *, width: float, height: float) -> str:
    """Return an SVG ``<path>`` ``d=`` attribute value tracing ``points`` as a
    polyline across a ``width`` x ``height`` viewBox (VIZ-003: pure geometry,
    computed here so the template only ever consumes the finished string,
    matching ``_shape_ranked_list_row``'s split between Python geometry and
    template rendering).

    ``points`` has already been checked non-empty by the caller. A single
    point draws a flat line across the full width at its own height (there is
    no second x position to interpolate toward), and a flat series (every
    value equal) draws a flat line at vertical centre rather than dividing by
    zero: both degrade to a visible, honest line rather than raising or
    collapsing to a zero-height sliver.

    Coordinates are rounded to 2 decimal places: full float repr (e.g.
    ``33.33333333333333``) would still be valid SVG but bloats every rendered
    page for precision no viewBox at typical sparkline sizes can resolve.
    """
    count = len(points)
    lo = min(points)
    hi = max(points)
    spread = hi - lo

    def _y(value: float) -> float:
        if spread == 0:
            return height / 2
        # SVG y grows downward, so the largest value maps to the SMALLEST y
        # (the top of the box), matching every chart reading convention.
        return height - (value - lo) / spread * height

    def _x(index: int) -> float:
        if count == 1:
            return 0.0
        return index / (count - 1) * width

    coords = [f"{_x(i):.2f},{_y(v):.2f}" for i, v in enumerate(points)]
    return "M" + " L".join(coords)


def _sparkline_point(points: list[float], index: int, *, width: float, height: float) -> tuple[str, str]:
    """Return the ``(cx, cy)`` string pair for ``points[index]``, using the
    SAME normalisation ``_sparkline_path`` uses, so a highlighted point (VIZ-
    005) always lands exactly on the line it is marking rather than drifting
    from a second, slightly different calculation."""
    count = len(points)
    lo = min(points)
    hi = max(points)
    spread = hi - lo
    cy = height / 2 if spread == 0 else height - (points[index] - lo) / spread * height
    cx = 0.0 if count == 1 else index / (count - 1) * width
    return f"{cx:.2f}", f"{cy:.2f}"


@register.simple_tag
def bw_sparkline(
    points: object,
    *,
    label: str,
    value: str = "",
    tone: str = "neutral",
    highlight_index: int | None = None,
    width: float = 100,
    height: float = 32,
    data: object = None,
) -> SafeString:
    """An inline sparkline (VIZ-003/004/005/006): a single-series trend line
    drawn as a pure server-rendered SVG ``<path>``, no engine, no JS, working
    identically with scripts disabled (VIZ-006: a sparkline is geometry, not
    an interactive chart; an interactive-tooltip sparkline mounts a real
    engine at ``{% bw_chart_mount %}`` instead, which this component is not).

    Because that slot does not sanitise, this output is safe BY
    CONSTRUCTION rather than by the caller's diligence. Every interpolated
    value is classified as exactly one of three things, and the class decides
    the handling:

    * **attribute value** (``tone``, ``direction``, and every SVG coordinate):
      ``escape()``, never ``conditional_escape``, which honours ``__html__``
      and would let a ``SafeString`` break out of the attribute. The
      coordinates go further and are safe by construction, not by escaping:
      each is built as ``f"{float:.2f}"``, so no quote character can reach a
      ``d=`` or ``viewBox=`` attribute at all. A type constraint is stronger
      than an escaping step, because escaping is something a later edit can
      remove.
    * **text content** (``label``, ``value``): Django's ordinary
      auto-escaping, which DELIBERATELY honours ``mark_safe``.
    * **trusted markup** (``attrs_html`` from ``bw_data_attrs``): already a
      ``SafeString``, assembled from values that were escaped individually.

    That middle case looks alarming next to icvoss/django-brickwork#329 and
    is not the same defect. A ``mark_safe``'d ``label`` renders its markup
    raw, exactly as ``_stat.html`` and ``_ranked_list.html`` do, because
    ``mark_safe`` there is the caller asserting "this is HTML I authored and
    vouch for", which is Django's contract. In an ATTRIBUTE value no markup
    can ever be legitimate, so honouring that assertion means honouring a
    claim that cannot be true, and #329 is where that went wrong. A component
    that escaped its label would be wrong in the other direction: it would
    break every caller passing a formatted string.

    ``--bw-color-sparkline-stroke`` defaults to ``--bw-color-chart-1``, whose
    contrast was measured **against the chart card surface**. A sparkline is
    placed by its consumer, so it may sit in a table row, a stat tile, or a
    surface this package never sees. **The default is verified for the card
    and nowhere else**: a consumer placing a sparkline elsewhere verifies the
    stroke against that surface or overrides the token, which is exactly what
    the token exists for. Documented rather than tested because the set of
    surfaces is unbounded by construction, so a test would enumerate the ones
    we imagined rather than the ones a consumer uses.

    Composes with ``_stat.html``'s ``sparkline=`` slot (#60): that slot takes
    pre-rendered, ALREADY-TRUSTED markup and does not sanitise it, so this
    tag is the thing a caller renders and passes in, e.g.::

        {% bw_sparkline points=values label="Revenue trend" value="1,234" as spark %}
        {% include "brickwork/components/_stat.html" with label="Revenue" value="1,234" sparkline=spark %}

    The two never need to change together: ``_stat.html`` accepts any safe
    markup in that slot, and this tag is only one possible source of it.

    Required context:
      points: a non-empty list/tuple of numbers (int, float, or Decimal; VIZ-
          020 numbers are never formatted by the package, so the geometry
          accepts whatever numeric type the caller already has). Fewer than
          two points still renders (a flat line, see ``_sparkline_path``),
          but a sparkline of one point communicates nothing: that is a
          caller authoring choice, not something this tag corrects for.
      label: the accessible summary of what the line shows (e.g. "Revenue,
          last 12 months"), rendered as VISIBLE text (COL-030): a sparkline
          has no adjacent row/heading of its own the way a ranked-list row or
          a stat tile's label does, so unlike ``bw_ranked_list``'s optional
          ``label`` (which only sets an aria-label because the visible text
          lives in each row), this one is REQUIRED and always visible, or the
          line's meaning rides on shape alone for a screen reader.
    Optional:
      value (str): a pre-formatted current/latest-value string (VIZ-020: the
          package never formats numbers), rendered as visible text beside
          the label. Omitted renders no value text, only the label.
      tone ("neutral" | "trend", default "neutral"): "neutral" strokes the
          line with the shared chart palette's first colour (VIZ-026:
          --bw-color-chart-1, reused rather than a new sparkline-only token,
          since nothing about a neutral sparkline needs a colour distinct
          from any other single-series chart line the package already
          tokenises). "trend" strokes positive or negative (--bw-color-
          success-fg / --bw-color-danger-fg: the SAME per-theme-authored,
          AA-verified ink _stat.html's own trend text already uses, reused
          rather than a duplicate --bw-sparkline-stroke-positive/-negative
          pair with identical values) based on the DIRECTION COMPUTED HERE
          from points[-1] vs points[0], never a caller-supplied flag: the
          direction is a fact about the data, not an opinion a call site
          could get out of sync with the line it is describing.

          COL-030 (colour is never the only signal): "trend" ALWAYS pairs
          the stroke colour with a decorative directional glyph (arrow-up/
          arrow-down/minus, matching _stat.html's own trend iconography
          exactly) plus visually-hidden text naming the direction in words
          ("increased"/"decreased"/"unchanged"), rendered by the template
          regardless of whether the caller supplies a visible ``value``.
          This mirrors _stat.html's BR-BW-TPL-007 contract precisely: a
          second implementation of the identical rule would only invite the
          two drifting apart.
      highlight_index (int): renders a filled --bw-sparkline-marker circle
          (VIZ-005) at ``points[highlight_index]``, e.g. the latest point or
          a caller-chosen point of interest. Silently ignored (no marker
          rendered) when out of range, matching ``list_item``'s own
          fail-quiet convention elsewhere in this module, since a marker is
          decorative reinforcement, not a contract a bad index should 500 a
          page over.
      width, height (default 100 x 32): the SVG viewBox dimensions in
          unitless user units. The rendered element fills its container at
          100% width/height (CSS), so these only set the ASPECT RATIO the
          line is drawn against, not an on-page pixel size; a caller wanting
          a taller or shallower line passes a different height for a more or
          less dramatic-looking trend.
      data: a mapping of consumer-owned data-* attributes for the component
          root (component-level test hooks, mirroring _stat.html's and
          _ranked_list.html's own root data seam).

    States: neutral and trend (positive/negative sub-states, always paired
      with the glyph+hidden-text signal above); no loading or empty state
      (VIZ-003: a caller with no data yet simply does not render this tag,
      matching how _stat.html's own sparkline slot is omitted rather than
      rendering an empty box).
    Accessibility: the label and, when given, the value render as VISIBLE
      text (COL-030); the line itself and any highlight marker are
      aria-hidden="true" and carry no text of their own (the numeric meaning
      never rides on the line's shape or colour alone). tone="trend" adds
      the decorative glyph + visually-hidden direction text pairing
      described above.
    Responsive: no breakpoint switch; the SVG scales to its container via
      viewBox (no width-dependent CSS on any .bw-sparkline* selector), so a
      caller controls on-page size entirely through the container it places
      this component in (matching _stat.html's own bw-stat__sparkline slot,
      which this tag is designed to fill).
    """
    if not isinstance(points, list | tuple) or not points:
        raise TemplateSyntaxError(f"bw_sparkline points must be a non-empty list/tuple of numbers, got {points!r}")
    try:
        numeric_points = [float(point) for point in points]
    except (TypeError, ValueError) as exc:
        raise TemplateSyntaxError(f"bw_sparkline points must all be numbers, got {points!r}") from exc
    if not all(math.isfinite(point) for point in numeric_points):
        raise TemplateSyntaxError(f"bw_sparkline points must all be finite numbers, got {points!r}")
    if tone not in _SPARKLINE_TONES:
        raise TemplateSyntaxError(f"bw_sparkline tone must be one of {sorted(_SPARKLINE_TONES)}, got {tone!r}")

    path_d = _sparkline_path(numeric_points, width=width, height=height)

    marker_cx = marker_cy = ""
    if highlight_index is not None and 0 <= highlight_index < len(numeric_points):
        marker_cx, marker_cy = _sparkline_point(numeric_points, highlight_index, width=width, height=height)

    direction = ""
    if tone == "trend":
        delta = numeric_points[-1] - numeric_points[0]
        direction = "up" if delta > 0 else "down" if delta < 0 else "flat"

    # A simple_tag returning rendered markup, NOT an inclusion_tag, and the
    # reason is the composition this component exists for: _stat.html's
    # sparkline slot takes pre-rendered markup, so a caller needs
    # {% bw_sparkline ... as spark %} to hand it over. Django's inclusion_tag
    # cannot do `as var` at all (its parser reads `as` as a positional
    # argument after keywords and raises), so registering it that way made the
    # documented call unwritable. bw_icon is the same shape for the same
    # reason: a tag whose output a caller composes with, rather than a block a
    # caller places.
    #
    # Safety is earned at assembly, exactly as bw_data_attrs earns it: every
    # value in the context below is either machine-built (the coordinates, as
    # f"{float:.2f}") or escaped by the template that renders it, so the
    # SafeString is a statement about how this string was made, not a request
    # to trust its origin.
    return mark_safe(  # noqa: S308
        render_to_string(
            "brickwork/components/_sparkline.html",
            {
                "path_d": path_d,
                "label": label,
                "value": value,
                "tone": tone,
                "direction": direction,
                "marker_cx": marker_cx,
                "marker_cy": marker_cy,
                "width": width,
                "height": height,
                "attrs_html": bw_data_attrs(data, "sparkline"),
            },
        )
    )
