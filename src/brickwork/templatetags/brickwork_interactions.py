"""Inclusion tags for the interaction set (04-interfaces section 4b, 0.8.0).

``{% bw_dropdown %}`` and ``{% bw_tabs %}`` are tags, not includes, per the
tag-vs-include doctrine: each carries render-time a11y or shape enforcement
(the ICO-008 icon-only accessible-name rule, item intent validation, the
duplicate tab-key raise mirroring BR-BW-NAV-002), raising TemplateSyntaxError
at render time exactly as ``bw_button`` does. The disclosure stays a plain
``{% include %}`` (structure only, no enforcement) and the modal is consumed
by ``{% extends %}``; neither gets a tag.

Both tags ship their items to the private render targets pre-shaped
(RenderedMenuItem / RenderedTab), so the templates are pure presentation,
matching the ``{% bw_nav %}`` / RenderedNavItem precedent.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from django import template
from django.template.exceptions import TemplateSyntaxError
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.safestring import SafeString, mark_safe

register = template.Library()

_TRIGGER_VARIANTS = {"primary", "secondary", "ghost", "danger"}
_ITEM_INTENTS = {"default", "danger"}
_TRIGGER_MODES = {"click", "hover"}
_TAB_STYLES = {"underline", "pill"}

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


__all__ = ["RenderedMenuItem", "RenderedTab", "bw_dropdown", "bw_tabs"]
