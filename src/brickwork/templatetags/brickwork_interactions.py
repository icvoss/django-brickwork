"""Inclusion tags for the interaction set (04-interfaces section 4b).

``{% bw_dropdown %}`` and ``{% bw_tabs %}`` (0.8.0) and ``{% bw_toast %}``
and ``{% bw_combobox %}`` (0.9.0) are tags, not includes, per the
tag-vs-include doctrine: each carries render-time a11y or shape enforcement
(the ICO-008 icon-only accessible-name rule, item intent validation, the
duplicate tab-key raise mirroring BR-BW-NAV-002, the CMP-022 toast-intent
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
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext

register = template.Library()

_TRIGGER_VARIANTS = {"primary", "secondary", "ghost", "danger"}
_ITEM_INTENTS = {"default", "danger"}
_TRIGGER_MODES = {"click", "hover"}
_TAB_STYLES = {"underline", "pill"}
# CMP-022: "neutral" is deliberately NOT a toast intent; a toast always
# carries a real outcome.
_TOAST_INTENTS = {"success", "warning", "danger", "info"}
_TOAST_DURATIONS = {"short", "normal", "long", "persistent"}
# Intent -> registry icon, mirroring bw_alert's variant map (danger takes the
# alert-circle glyph exactly as the alert's "error" variant does).
_TOAST_INTENT_ICONS = {"success": "success", "warning": "alert-triangle", "danger": "alert-circle", "info": "info"}
_FILTER_MODES = {"server", "client"}

# Keys and instance ids flow into HTML id attributes (the stable
# bw-tabpanel-<id>-<key> swap-target convention, BR-BW-HTMX-005) and into
# consumers' own hx-target CSS selectors, so they are constrained to a
# conservative id-safe token at render time rather than escaped into
# something a selector cannot address.
_ID_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

# Attribute NAMES cannot be escaped into safety (only values can), so the
# consumer pass-through mapping (the per-item hx-* seam) validates names
# against a conservative HTML attribute token.
_ATTR_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")


@dataclass(frozen=True)
class RenderedMenuItem:
    """A dropdown item prepared for template rendering (validated, attrs escaped)."""

    label: str
    url: str
    icon: str
    intent: str
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
    """Flatten a consumer attrs mapping (the per-item hx-* seam) into a safe
    leading-space attribute run. Attribute names are validated (they cannot be
    escaped); values are escaped."""
    if attrs in (None, ""):
        return mark_safe("")
    if not isinstance(attrs, Mapping):
        raise TemplateSyntaxError(f'{tag} item "attrs" must be a mapping of attribute name -> value, got {attrs!r}')
    parts = []
    for name, value in attrs.items():
        if not isinstance(name, str) or not _ATTR_NAME_RE.match(name):
            raise TemplateSyntaxError(f"{tag} item attrs contains an invalid attribute name: {name!r}")
        parts.append(format_html(' {}="{}"', name, value))
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
        return RenderedMenuItem(label="", url="", icon="", intent="default", is_divider=True, attrs_html=mark_safe(""))
    label = raw.get("label")
    url = raw.get("url")
    if not label or not url:
        raise TemplateSyntaxError(f'bw_dropdown items require "label" and "url" (04-interfaces 4b), got {dict(raw)!r}')
    intent = raw.get("intent", "default")
    if intent not in _ITEM_INTENTS:
        raise TemplateSyntaxError(f"bw_dropdown item intent must be one of {sorted(_ITEM_INTENTS)}, got {intent!r}")
    return RenderedMenuItem(
        label=str(label),
        url=str(url),
        icon=str(raw.get("icon", "") or ""),
        intent=intent,
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
    close_on_select: bool = True,
) -> dict:
    """A dropdown menu button (04-interfaces 4b). The rendered floor is a
    <details> disclosure of plain links (no ARIA menu roles); bwDropdown
    upgrades it to the APG Menu Button pattern at init. ICO-008: an icon-only
    trigger REQUIRES an accessible name (aria_label), else it is a render
    error, exactly as bw_button."""
    if not isinstance(items, list | tuple) or not items:
        raise TemplateSyntaxError("bw_dropdown requires items=, a non-empty list/tuple of item dicts")
    if trigger_variant not in _TRIGGER_VARIANTS:
        raise TemplateSyntaxError(
            f"bw_dropdown trigger_variant must be one of {sorted(_TRIGGER_VARIANTS)}, got {trigger_variant!r}"
        )
    if trigger_mode not in _TRIGGER_MODES:
        raise TemplateSyntaxError(
            f"bw_dropdown trigger_mode must be one of {sorted(_TRIGGER_MODES)}, got {trigger_mode!r}"
        )
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
        "close_on_select": bool(close_on_select),
    }


def _shape_tab(raw: object, *, tabs_id: str, active: str, current_path: str) -> RenderedTab:
    if not isinstance(raw, Mapping):
        raise TemplateSyntaxError(f"bw_tabs tabs must be mappings, got {raw!r}")
    key = raw.get("key")
    label = raw.get("label")
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
        label=str(label),
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
    style: str = "underline",
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
    if style not in _TAB_STYLES:
        raise TemplateSyntaxError(f"bw_tabs style must be one of {sorted(_TAB_STYLES)}, got {style!r}")
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
        "style": style,
        "url_sync": bool(url_sync),
        "lazy_load": bool(lazy_load),
    }


@register.inclusion_tag("brickwork/components/_toast.html")
def bw_toast(
    message: str,
    *,
    intent: str,
    duration: str = "normal",
    action_label: str = "",
    action_url: str = "",
    id: str = "",  # noqa: A002 - the documented argument name (04-interfaces 4b)
) -> dict:
    """One toast notification (04-interfaces 4b). Server-rendered ONLY
    (BR-BW-HTMX-007): an htmx response appends it out of band by rendering
    this tag inside a wrapper carrying
    hx-swap-oob="afterbegin:#bw-toast-region"; the no-JS floor is the same
    feedback as a django.contrib.messages banner rendered via _alert.html
    (STA-008). intent is validated (CMP-022: anything outside the four
    outcome intents, including "neutral", raises); the close control is
    ALWAYS rendered by the template (CBH-012, WCAG 2.2.1)."""
    if not message:
        raise TemplateSyntaxError("bw_toast requires message= (04-interfaces 4b)")
    if intent not in _TOAST_INTENTS:
        raise TemplateSyntaxError(
            f"bw_toast intent must be one of {sorted(_TOAST_INTENTS)}, got {intent!r} "
            '("neutral" is deliberately not a toast intent, CMP-022).'
        )
    if duration not in _TOAST_DURATIONS:
        raise TemplateSyntaxError(f"bw_toast duration must be one of {sorted(_TOAST_DURATIONS)}, got {duration!r}")
    if bool(action_label) != bool(action_url):
        raise TemplateSyntaxError(
            "bw_toast takes action_label= and action_url= together or not at all "
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
        "intent": intent,
        "duration": duration,
        "action_label": action_label,
        "action_url": action_url,
        "id": id,
        "icon": _TOAST_INTENT_ICONS[intent],
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
        label = field.label
        required = field.field.required
        help_text = field.help_text
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
