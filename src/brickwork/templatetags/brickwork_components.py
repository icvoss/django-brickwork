"""Inclusion tags for the presentational components (button, badge, alert).

These carry a little logic (variant/size validation, the ICO-008 icon-only
accessible-name enforcement), so they are tags rather than bare {% include %}.
"""

from __future__ import annotations

import html
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django import template
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.html import conditional_escape, escape, format_html, strip_tags
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
    # screen reader (bw_chart_mount's own aria_label precedent,
    # brickwork_components.py:517). normalise_accessible_name (not a bare
    # .strip()) also coerces a non-str value and preserves an already-safe
    # one without double-escaping it (icvoss/django-brickwork#330).
    aria_label = normalise_accessible_name(aria_label)
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


def _gauge_label_has_visible_text(gauge_label: object) -> bool:
    """Whether ``gauge_label`` carries any visible text, the same "stripped,
    not merely truthy" reasoning ``bw_chart_mount`` applies to ``aria_label``
    (see that tag's own comment): a whitespace-only string is truthy in
    Python and is not visible text, so testing truthiness alone would let
    ``{% if gauge_label %}`` render an empty-looking label with no numeric
    fallback, which is exactly the COL-030 defect this function exists to
    close (icvoss/django-brickwork COL-030).

    Unlike ``aria_label``, ``gauge_label`` is a TRUSTED MARKUP slot (VIZ-008):
    a caller may legitimately pass ``mark_safe("<strong>73%</strong>")``, so
    this cannot strip or reject markup the way ``bw_chart_mount`` does.
    Instead it tests for text CONTENT: strip the tags with
    ``django.utils.html.strip_tags`` and test what is left, while the caller
    (``bw_gauge``) keeps passing the ORIGINAL value, safe marker intact, to
    the template. This function only answers the yes/no question; it never
    mutates or returns the label itself.

    ``html.unescape`` runs before the final ``.strip()`` so an HTML entity
    that renders as whitespace is treated as no text, the same as the raw
    character would be: ``strip_tags`` removes tags but does not decode
    entities, so a label of only ``"&nbsp;"`` would otherwise survive as a
    non-empty string and wrongly count as visible text, even though a sighted
    user sees nothing there but a single space. ``html.unescape`` is the
    stdlib's own entity decoder (no new dependency), and is safe to use here
    because its output is discarded immediately after the truthiness check:
    it never reaches the template.

    ``None`` is guarded explicitly before ``strip_tags`` sees it:
    ``strip_tags(None)`` returns the literal string ``"None"`` (Django
    stringifies its argument first), which would wrongly test as visible
    text."""
    if not gauge_label:
        return False
    return bool(html.unescape(strip_tags(str(gauge_label))).strip())


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
