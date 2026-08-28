"""Inclusion tags for the interaction set (04-interfaces section 4b).

``{% bw_dropdown %}`` and ``{% bw_tabs %}`` (0.8.0) and ``{% bw_toast %}``
and ``{% bw_combobox %}`` (0.9.0) are tags, not includes, per the
tag-vs-include doctrine: each carries render-time a11y or shape enforcement
(the ICO-008 icon-only accessible-name rule, item variant validation, the
duplicate tab-key raise mirroring BR-BW-NAV-002, the CMP-022 toast-variant
raise, the CBH-019 options_url requirement), raising TemplateSyntaxError
at render time exactly as ``bw_button`` does. The disclosure and the toast
region stay plain ``{% include %}`` (structure only, no enforcement) and
the modal is consumed by ``{% extends %}``; none of those gets a tag.

The tags ship their items to the private render targets pre-shaped
(RenderedMenuItem / RenderedTab / RenderedComboboxOption), so the templates
are pure presentation, matching the ``{% bw_nav %}`` / RenderedNavItem
precedent.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from uuid import uuid4

from django import template
from django.forms import BoundField
from django.template.exceptions import TemplateSyntaxError
from django.utils.html import escape, format_html
from django.utils.http import urlencode
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext

from brickwork.templatetags.brickwork_components import _DATA_ATTRIBUTE_NAME_RE

register = template.Library()

_TRIGGER_VARIANTS = {"primary", "secondary", "ghost", "danger"}
_ITEM_VARIANTS = {"default", "danger"}
_TRIGGER_MODES = {"click", "hover"}
# ADR-060 rule 1: `placement` is the settled name for edge anchoring across
# slide_over, tooltip, account_menu and now dropdown. The .bw-dropdown--end rule
# shipped from 0.8.0 with no way to reach it (icvoss/django-brickwork#120).
_DROPDOWN_PLACEMENTS = {"start", "end"}
_TAB_VARIANTS = {"underline", "pill"}
# CMP-022: "neutral" is deliberately NOT a toast variant; a toast always
# carries a real outcome.
_TOAST_VARIANTS = {"success", "warning", "danger", "info"}
_TOAST_DURATIONS = {"short", "normal", "long", "persistent"}
# Intent -> registry icon, mirroring bw_alert's variant map (danger takes the
# alert-circle glyph exactly as the alert's "error" variant does).
_TOAST_VARIANT_ICONS = {"success": "success", "warning": "alert-triangle", "danger": "alert-circle", "info": "info"}
_FILTER_MODES = {"server", "client"}

# Keys and instance ids flow into HTML id attributes (the stable
# bw-tabpanel-<id>-<key> swap-target convention, BR-BW-HTMX-005) and into
# consumers' own hx-target CSS selectors, so they are constrained to a
# conservative id-safe token at render time rather than escaped into
# something a selector cannot address.
_ID_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

# Attribute NAMES cannot be escaped into safety (only values can), so the
# consumer pass-through mapping (the per-item attrs seam) validates names.
# ADR-083: this seam protects what a component deliberately WITHHOLDS (a
# rejected ARIA role, an unstamped hx-* hook), not just what it emits; the
# browser's first-attribute-wins behaviour already defends the latter, but
# nothing defends the former unless the grammar itself refuses non-data-*
# names. So this reuses bw_data_attrs's own rule (_DATA_ATTRIBUTE_NAME_RE,
# including its data-bw-* reservation) rather than a second, wider regex:
# one rule, two call sites, not two rules that happen to overlap.


@dataclass(frozen=True)
class RenderedMenuItem:
    """A dropdown item prepared for template rendering (validated, attrs escaped)."""

    label: str
    url: str
    icon: str
    variant: str
    is_divider: bool
    attrs_html: SafeString  # "" or a leading-space run of escaped attributes


@dataclass(frozen=True)
class RenderedTab:
    """A tab prepared for template rendering: URL resolved, ids derived, state computed."""

    key: str
    label: str
    url: str
    badge: str | int | None
    is_active: bool
    tab_id: str  # bw-tab-<id>-<key>: the anchor id tab_panel's aria-labelledby pairs with
    panel_id: str  # bw-tabpanel-<id>-<key>: the stable panel/swap-target id (BR-BW-HTMX-005)


def _rendered_attrs(tag: str, attrs: object) -> SafeString:
    """Flatten a consumer attrs mapping (the per-item data-* metadata seam,
    ADR-083) into a safe leading-space attribute run. Attribute names are
    validated against the same rule bw_data_attrs enforces (they cannot be
    escaped); values are escaped.

    ADR-083: this seam is for consumer-owned data-* metadata only, never a
    general HTML attribute escape hatch, and never a way to fill in an
    attribute a component author deliberately chose not to emit (the
    _ranked_list.html VIZ-015 abstention is the worked example the ADR is
    built from). A consumer needing hx-* on a component-rendered element
    reaches for one of the two already-shipping answers instead: a stable
    id with the hx-* attributes authored on the consumer's own element
    (the _disclosure.html/_data_table.html pattern), or a named, validated
    kwarg on the component itself (the _filter_bar.html hx_get/hx_target
    pattern)."""
    if attrs in (None, ""):
        return mark_safe("")
    if not isinstance(attrs, Mapping):
        raise TemplateSyntaxError(f'{tag} item "attrs" must be a mapping of attribute name -> value, got {attrs!r}')
    parts = []
    for name, value in attrs.items():
        if not isinstance(name, str) or not _DATA_ATTRIBUTE_NAME_RE.match(name) or name.startswith("data-bw-"):
            raise TemplateSyntaxError(
                f"{tag} item attrs contains an invalid attribute name: {name!r}. This seam accepts only "
                'consumer-owned data-* metadata (matching "data-[a-z][a-z0-9_.:-]*", excluding brickwork\'s '
                "own reserved data-bw-* namespace); it is not a general attribute passthrough (ADR-083). "
                "For an htmx interaction, author hx-* on an element you render yourself, or use a named "
                "option where the component ships one (as _filter_bar.html does with hx_get/hx_target). "
                "Some components render stable ids you can target instead (_data_table.html does), so "
                f"check {tag}'s own documentation rather than assuming one is available."
            )
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


def _shape_menu_item(raw: object) -> RenderedMenuItem:
    if not isinstance(raw, Mapping):
        raise TemplateSyntaxError(f"bw_dropdown items must be mappings, got {raw!r}")
    if raw.get("divider"):
        extra = set(raw) - {"divider"}
        if extra:
            raise TemplateSyntaxError(
                f"bw_dropdown divider items carry no other keys (04-interfaces 4b), got extra {sorted(extra)}"
            )
        return RenderedMenuItem(label="", url="", icon="", variant="default", is_divider=True, attrs_html=mark_safe(""))
    label = raw.get("label")
    url = raw.get("url")
    # label is an accessible name and gets the strip-and-rebind treatment (a
    # whitespace-only label is truthy but is not a name to any screen reader,
    # the bw_chart_mount aria_label precedent, brickwork_components.py:517);
    # url is a URL, not a name, and keeps its plain truthiness test.
    label = str(label).strip() if label is not None else ""
    if not label or not url:
        raise TemplateSyntaxError(f'bw_dropdown items require "label" and "url" (04-interfaces 4b), got {dict(raw)!r}')
    variant = raw.get("variant", "default")
    if variant not in _ITEM_VARIANTS:
        raise TemplateSyntaxError(f"bw_dropdown item variant must be one of {sorted(_ITEM_VARIANTS)}, got {variant!r}")
    return RenderedMenuItem(
        label=str(label),
        url=str(url),
        icon=str(raw.get("icon", "") or ""),
        variant=variant,
        is_divider=False,
        attrs_html=_rendered_attrs("bw_dropdown", raw.get("attrs")),
    )


@register.inclusion_tag("brickwork/components/_dropdown.html")
def bw_dropdown(
    items: object,
    *,
    trigger_label: str = "",
    trigger_variant: str = "secondary",
    trigger_icon: str = "",
    icon_only: bool = False,
    aria_label: str = "",
    trigger_mode: str = "click",
    placement: str = "start",
    close_on_select: bool = True,
) -> dict:
    """A dropdown menu button (04-interfaces 4b). The rendered floor is a
    <details> disclosure of plain links (no ARIA menu roles); bwDropdown
    upgrades it to the APG Menu Button pattern at init. ICO-008: an icon-only
    trigger REQUIRES an accessible name (aria_label), else it is a render
    error, exactly as bw_button.

    Each item in ``items`` may carry an optional ``attrs`` mapping: consumer-
    owned ``data-*`` metadata rendered on that item's anchor, for the
    consumer's own JS or htmx to read back (mirroring the ``data`` seam
    ``_data_table.html``/``_stat.html``/``bw_ranked_list`` already accept).
    ADR-083: only ordinary ``data-*`` names are accepted (brickwork's own
    ``data-bw-*`` hooks stay reserved), and values are escaped; this is not a
    general attribute passthrough, so ``role``, ``aria-*``, ``hx-*``, and
    every other non-``data-*`` name raise ``TemplateSyntaxError``. An htmx
    interaction on a rendered item reaches for a stable id and its own
    consumer-authored element instead, or a named kwarg if the component
    ships one (as ``_filter_bar.html`` does with ``hx_get``/``hx_target``).
    """
    if not isinstance(items, list | tuple) or not items:
        raise TemplateSyntaxError("bw_dropdown requires items=, a non-empty list/tuple of item dicts")
    if trigger_variant not in _TRIGGER_VARIANTS:
        raise TemplateSyntaxError(
            f"bw_dropdown trigger_variant must be one of {sorted(_TRIGGER_VARIANTS)}, got {trigger_variant!r}"
        )
    if placement not in _DROPDOWN_PLACEMENTS:
        raise TemplateSyntaxError(
            f"bw_dropdown placement must be one of {sorted(_DROPDOWN_PLACEMENTS)}, got {placement!r}"
        )
    if trigger_mode not in _TRIGGER_MODES:
        raise TemplateSyntaxError(
            f"bw_dropdown trigger_mode must be one of {sorted(_TRIGGER_MODES)}, got {trigger_mode!r}"
        )
    # Stripped before testing, not merely truthiness-tested: a whitespace-only
    # accessible name is truthy in Python and is not a name to any screen
    # reader or, for trigger_label, a real visible label (the bw_chart_mount
    # aria_label precedent, brickwork_components.py:517).
    aria_label = aria_label.strip()
    trigger_label = trigger_label.strip()
    if icon_only and not aria_label:
        raise TemplateSyntaxError(
            "bw_dropdown icon_only=True requires aria_label= (an icon-only trigger "
            "with no accessible name is a WCAG 4.1.2 failure, ICO-008)."
        )
    if not icon_only and not trigger_label:
        raise TemplateSyntaxError("bw_dropdown requires trigger_label= unless icon_only=True (04-interfaces 4b)")
    return {
        "items": [_shape_menu_item(raw) for raw in items],
        "trigger_label": trigger_label,
        "trigger_variant": trigger_variant,
        "trigger_icon": trigger_icon,
        "icon_only": icon_only,
        "aria_label": aria_label,
        "trigger_mode": trigger_mode,
        "placement": placement,
        "close_on_select": bool(close_on_select),
    }


def _shape_tab(raw: object, *, tabs_id: str, active: str, current_path: str) -> RenderedTab:
    if not isinstance(raw, Mapping):
        raise TemplateSyntaxError(f"bw_tabs tabs must be mappings, got {raw!r}")
    key = raw.get("key")
    label = raw.get("label")
    # label is an accessible (and visible) name and gets the strip-and-rebind
    # treatment (the bw_chart_mount aria_label precedent, brickwork_components.py:517);
    # key is already correctly guarded below by _ID_TOKEN_RE, which rejects
    # whitespace outright, so it is left alone.
    label = str(label).strip() if label is not None else ""
    if not key or not label:
        raise TemplateSyntaxError(f'bw_tabs tabs require "key" and "label" (04-interfaces 4b), got {dict(raw)!r}')
    key = str(key)
    if not _ID_TOKEN_RE.match(key):
        raise TemplateSyntaxError(
            f"bw_tabs tab key {key!r} must be an id-safe token (letters, digits, hyphen, "
            "underscore): it derives the stable bw-tabpanel id (BR-BW-HTMX-005)."
        )
    url = raw.get("url") or f"{current_path}?{urlencode({'tab': key})}"
    return RenderedTab(
        key=key,
        label=label,
        url=str(url),
        badge=raw.get("badge"),
        is_active=key == active,
        tab_id=f"bw-tab-{tabs_id}-{key}",
        panel_id=f"bw-tabpanel-{tabs_id}-{key}",
    )


@register.inclusion_tag("brickwork/components/_tabs.html", takes_context=True)
def bw_tabs(
    context: template.Context,
    tabs: object,
    *,
    active: str,
    id: str,  # noqa: A002 - the documented argument name (04-interfaces 4b)
    variant: str = "underline",
    url_sync: bool = True,
    lazy_load: bool = False,
) -> dict:
    """A tablist (04-interfaces 4b). Renders the TABLIST ONLY: panels are
    consumer markup wrapped in _tabs.html's tab_panel partial, following the
    stable bw-tabpanel-<id>-<key> id convention (BR-BW-HTMX-005). The floor
    is real anchor links (default ?tab=<key> on the current path) with the
    server owning the active selection; bwTabs upgrades to the APG Tabs
    pattern at init. A duplicate tab key raises at render time (mirroring
    BR-BW-NAV-002's duplicate-key discipline)."""
    if not isinstance(tabs, list | tuple) or not tabs:
        raise TemplateSyntaxError("bw_tabs requires tabs=, a non-empty list/tuple of tab dicts")
    if not id or not isinstance(id, str) or not _ID_TOKEN_RE.match(id):
        raise TemplateSyntaxError(
            "bw_tabs requires id=, an id-safe token (letters, digits, hyphen, underscore): "
            "the bw-tabpanel-<id>-<key> panel convention derives from it (BR-BW-HTMX-005)."
        )
    if variant not in _TAB_VARIANTS:
        raise TemplateSyntaxError(f"bw_tabs variant must be one of {sorted(_TAB_VARIANTS)}, got {variant!r}")
    request = context.get("request")
    current_path = request.path if request is not None else ""
    rendered = [_shape_tab(raw, tabs_id=id, active=str(active), current_path=current_path) for raw in tabs]
    seen: set[str] = set()
    for tab in rendered:
        if tab.key in seen:
            raise TemplateSyntaxError(
                f"bw_tabs duplicate tab key {tab.key!r}: keys must be unique within one tablist "
                "(the BR-BW-NAV-002 duplicate-key discipline)."
            )
        seen.add(tab.key)
    if not active or str(active) not in seen:
        raise TemplateSyntaxError(
            f"bw_tabs active={active!r} does not match any tab key {sorted(seen)}: the view owns "
            "the server-selected tab (04-interfaces 4b), so an unknown key is an authoring error."
        )
    return {
        "tabs": rendered,
        "active": str(active),
        "id": id,
        "variant": variant,
        "url_sync": bool(url_sync),
        "lazy_load": bool(lazy_load),
    }


@register.inclusion_tag("brickwork/components/_toast.html")
def bw_toast(
    message: str,
    *,
    variant: str,
    duration: str = "normal",
    action_label: str = "",
    action_href: str = "",
    id: str = "",  # noqa: A002 - the documented argument name (04-interfaces 4b)
) -> dict:
    """One toast notification (04-interfaces 4b). Server-rendered ONLY
    (BR-BW-HTMX-007): an htmx response appends it out of band by rendering
    this tag inside a wrapper carrying
    hx-swap-oob="afterbegin:#bw-toast-region"; the no-JS floor is the same
    feedback as a django.contrib.messages banner rendered via _alert.html
    (STA-008). variant is validated (CMP-022: anything outside the four
    outcome intents, including "neutral", raises); the close control is
    ALWAYS rendered by the template (CBH-012, WCAG 2.2.1)."""
    if not message:
        raise TemplateSyntaxError("bw_toast requires message= (04-interfaces 4b)")
    if variant not in _TOAST_VARIANTS:
        raise TemplateSyntaxError(
            f"bw_toast variant must be one of {sorted(_TOAST_VARIANTS)}, got {variant!r} "
            '("neutral" is deliberately not a toast variant, CMP-022).'
        )
    if duration not in _TOAST_DURATIONS:
        raise TemplateSyntaxError(f"bw_toast duration must be one of {sorted(_TOAST_DURATIONS)}, got {duration!r}")
    if bool(action_label) != bool(action_href):
        raise TemplateSyntaxError(
            "bw_toast takes action_label= and action_href= together or not at all "
            "(the single optional inline action, CMP-023)."
        )
    if id:
        if not isinstance(id, str) or not _ID_TOKEN_RE.match(id):
            raise TemplateSyntaxError(
                f"bw_toast id {id!r} must be an id-safe token (letters, digits, hyphen, "
                "underscore): it is the DOM id carried in the bw:toast:show/dismiss details."
            )
    else:
        # Auto-generated instance id: the "bw-toast-" prefix keeps it letter-led
        # and id-safe; uniqueness matters because several toasts stack in one
        # region and the id is the event-detail identity.
        id = f"bw-toast-{uuid4().hex[:10]}"
    return {
        "message": message,
        "variant": variant,
        "duration": duration,
        "action_label": action_label,
        "action_href": action_href,
        "id": id,
        "icon": _TOAST_VARIANT_ICONS[variant],
    }


@dataclass(frozen=True)
class RenderedComboboxOption:
    """A combobox option prepared for template rendering: value/label paired,
    selection resolved, aria-activedescendant id derived."""

    value: str
    label: str
    is_selected: bool
    option_id: str  # <listbox id>-opt-<n>: the aria-activedescendant target


def _combobox_pairs_from_options(options: object) -> list[tuple[str, str]]:
    """Normalise the explicit options= argument to (value, label) pairs.
    Accepts mappings with "value"/"label" keys or two-item sequences."""
    if not isinstance(options, list | tuple) or not options:
        raise TemplateSyntaxError(
            "bw_combobox options= must be a non-empty list/tuple of options "
            '(mappings with "value" and "label", or (value, label) pairs)'
        )
    pairs: list[tuple[str, str]] = []
    for raw in options:
        if isinstance(raw, Mapping):
            if "value" not in raw or "label" not in raw:
                raise TemplateSyntaxError(f'bw_combobox option mappings require "value" and "label", got {dict(raw)!r}')
            pairs.append((str(raw["value"]), str(raw["label"])))
        elif isinstance(raw, list | tuple) and len(raw) == 2:
            pairs.append((str(raw[0]), str(raw[1])))
        else:
            raise TemplateSyntaxError(
                f"bw_combobox options entries must be value/label mappings or (value, label) pairs, got {raw!r}"
            )
    return pairs


def _combobox_pairs_from_field(field: BoundField) -> list[tuple[str, str]]:
    """(value, label) pairs from a bound choice field. Optgroups are flattened:
    the combobox listbox is a flat role=listbox (group semantics are not part
    of the 4b contract)."""
    choices = getattr(field.field, "choices", None)
    if choices is None:
        raise TemplateSyntaxError(
            "bw_combobox field= must be a bound CHOICE field (the field supplies the "
            f"option set); {field.name!r} has no choices"
        )
    pairs: list[tuple[str, str]] = []
    for value, label in choices:
        if isinstance(label, list | tuple):
            pairs.extend((str(group_value), str(group_label)) for group_value, group_label in label)
        else:
            pairs.append((str(value), str(label)))
    return pairs


def _combobox_selected_set(selected: object) -> set[str]:
    """Normalise a selected value (None, scalar, or list) to a set of strings
    for comparison against stringified option values."""
    if selected is None or selected == "":
        return set()
    if isinstance(selected, list | tuple | set):
        return {str(value) for value in selected}
    return {str(selected)}


@register.inclusion_tag("brickwork/components/_combobox.html")
def bw_combobox(
    field: object = None,
    *,
    name: str = "",
    options: object = None,
    selected: object = None,
    filter_mode: str = "server",
    options_url: str = "",
    multiple: bool = False,
    allow_create: bool = False,
    empty_message: str = "",
    placeholder: str = "",
) -> dict:
    """A filterable select (04-interfaces 4b). ONE markup, progressively
    enhanced (BR-BW-HTMX-006): the rendered floor is a native <select> (or
    <select multiple>) built from the choices, and it STAYS the submitted
    form control at all times; bwCombobox upgrades it at init. Given a bound
    field this renders inside the forms/_field.html chrome (label, help,
    errors, aria-describedby), exactly as bw_field_widget-composed fields do;
    given the explicit name=/options=/selected= trio it renders the bare
    control (the consumer owns labelling). field wins when both are passed.
    filter_mode="server" (the default) REQUIRES options_url (CBH-019)."""
    if filter_mode not in _FILTER_MODES:
        raise TemplateSyntaxError(
            f"bw_combobox filter_mode must be one of {sorted(_FILTER_MODES)}, got {filter_mode!r}"
        )
    if filter_mode == "server" and not options_url:
        raise TemplateSyntaxError(
            'bw_combobox filter_mode="server" (the default) requires options_url=, the '
            "consumer view returning the filtered option-list partial (CBH-019)."
        )
    label = ""
    required = False
    help_text = ""
    errors: list = []
    if field is not None:
        if not isinstance(field, BoundField):
            raise TemplateSyntaxError(f"bw_combobox field= must be a bound form field (BoundField), got {field!r}")
        field_id = field.auto_id
        if not field_id or not _ID_TOKEN_RE.match(field_id):
            raise TemplateSyntaxError(
                f"bw_combobox needs an id-safe widget id (letters, digits, hyphen, underscore) "
                f"to derive the stable bw-listbox-<field id> target (BR-BW-HTMX-005); "
                f"got auto_id {field_id!r} for field {field.name!r}."
            )
        html_name = field.html_name
        pairs = _combobox_pairs_from_field(field)
        selected_set = _combobox_selected_set(field.value())
        # field.label / field.help_text are str | Promise (Django lazy translation);
        # coerced to str here, matching the label=str(label) pattern already used
        # elsewhere in this module, rather than widening label/help_text's type and
        # threading Promise through the rest of the function and the template
        # context dict returned below.
        label = str(field.label)
        required = field.field.required
        help_text = str(field.help_text)
        errors = list(field.errors)
    elif name:
        if not isinstance(name, str) or not _ID_TOKEN_RE.match(name):
            raise TemplateSyntaxError(
                f"bw_combobox name {name!r} must be an id-safe token (letters, digits, hyphen, "
                "underscore): it derives the widget id and the stable listbox id (BR-BW-HTMX-005)."
            )
        field_id = f"id_{name}"  # mirror Django's auto_id convention
        html_name = name
        pairs = _combobox_pairs_from_options(options)
        selected_set = _combobox_selected_set(selected)
    else:
        raise TemplateSyntaxError(
            "bw_combobox requires field= (a bound choice field) or the explicit trio "
            "name=/options=/selected= (04-interfaces 4b)."
        )
    listbox_id = f"bw-listbox-{field_id}"
    rendered = [
        RenderedComboboxOption(
            value=value,
            label=option_label,
            is_selected=value in selected_set,
            option_id=f"{listbox_id}-opt-{index}",
        )
        for index, (value, option_label) in enumerate(pairs)
    ]
    # aria-describedby mirrors bw_field_widget: the help id and the error
    # container id the field chrome renders (BR-BW-A11Y-002).
    described_by_ids: list[str] = []
    if help_text:
        described_by_ids.append(f"{field_id}_help")
    if errors:
        described_by_ids.append(f"{field_id}_errors")
    return {
        "has_field": field is not None,
        "label": label,
        "label_id": f"{field_id}_label" if field is not None else "",
        "required": required,
        "help_text": help_text,
        "errors": errors,
        "help_id": f"{field_id}_help",
        "error_id": f"{field_id}_errors",
        "described_by": " ".join(described_by_ids),
        "field_id": field_id,
        "html_name": html_name,
        "listbox_id": listbox_id,
        "options": rendered,
        "filter_mode": filter_mode,
        "options_url": options_url,
        "multiple": bool(multiple),
        "allow_create": bool(allow_create),
        "empty_message": empty_message or gettext("No matches"),
        "placeholder": placeholder,
    }


__all__ = [
    "RenderedComboboxOption",
    "RenderedMenuItem",
    "RenderedTab",
    "bw_combobox",
    "bw_dropdown",
    "bw_tabs",
    "bw_toast",
]
