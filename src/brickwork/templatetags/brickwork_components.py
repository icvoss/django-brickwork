"""Inclusion tags for the presentational components (button, badge, alert).

These carry a little logic (variant/size validation, the ICO-008 icon-only
accessible-name enforcement), so they are tags rather than bare {% include %}.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django import template
from django.template.exceptions import TemplateSyntaxError
from django.utils.html import escape, format_html
from django.utils.safestring import SafeString, mark_safe
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
    # Stripped before testing, not merely truthiness-tested: a whitespace-only
    # aria_label is truthy in Python and is NOT an accessible name to any
    # screen reader, so testing truthiness alone would let a consumer satisfy
    # a hard-required check by supplying nothing. A requirement that can be
    # met with " " is not a requirement, and this one exists precisely because
    # an unnamed chart is invisible.
    aria_label = aria_label.strip()
    aria_describedby = aria_describedby.strip()

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
    # the class attribute and landed a handler on the element. The a11y
    # arguments happened to be safe only because .strip() returns a plain str
    # and destroys the SafeString marker, which is protection by accident
    # rather than by design. A component that never emits consumer markup
    # wants escape() everywhere.
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
