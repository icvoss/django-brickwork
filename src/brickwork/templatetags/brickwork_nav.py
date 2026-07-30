"""The ``{% bw_nav %}`` tag: render a filtered, active-aware nav tree.

Usage (in a shell block, after a context processor has run visible_items +
resolve_active_item)::

    {% load brickwork_nav %}
    {% bw_nav items=bw_nav_items active=bw_active_nav_item %}

The tag resolves each item's URL via safe_reverse (honouring
BRICKWORK_NAV_FALLBACK for a bad url_name, BR-BW-NAV-003), computes the
active/ancestor-active state (NAV-008), and renders the recursive nav partial.
One nav render is shared by the desktop sidebar and the mobile drawer (NAV-016).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django import template

from brickwork.conf import get_setting
from brickwork.services.navigation import is_ancestor_of_active, safe_reverse

if TYPE_CHECKING:
    from brickwork.models import NavItem

register = template.Library()


@dataclass(frozen=True)
class RenderedNavItem:
    """A NavItem prepared for template rendering: URL resolved, state computed."""

    key: str
    label: str
    href: str | None  # resolved URL, external URL, or None (header/disabled)
    icon: str | None
    badge: str | int | None
    is_active: bool  # this exact item is the current route
    is_active_ancestor: bool  # a descendant is the current route (NAV-008)
    is_section_header: bool
    is_external: bool
    is_disabled: bool  # a bad url_name under the "disabled" fallback
    children: tuple[RenderedNavItem, ...]


def _prepare(item: NavItem, active: NavItem | None, fallback: str) -> RenderedNavItem | None:
    """Prepare one item for render, or None if it should be omitted entirely."""
    href: str | None = None
    is_disabled = False
    is_external = item.external_url is not None

    if item.section_header:
        href = None
    elif is_external:
        href = item.external_url
    elif item.url_name is not None:
        href = safe_reverse(item.url_name, item.url_kwargs)
        if href is None:
            # BR-BW-NAV-003 / NAV-015: a bad url_name never 500s. Either drop the
            # item ("omit") or render it disabled ("disabled"), per the setting.
            if fallback == "omit":
                return None
            is_disabled = True

    children = tuple(prepared for child in item.children if (prepared := _prepare(child, active, fallback)) is not None)

    # a section header with no surviving children renders nothing
    if item.section_header and not children:
        return None

    return RenderedNavItem(
        key=item.key,
        label=item.label,
        href=href,
        icon=item.icon,
        badge=item.badge,
        is_active=active is not None and item.key == active.key,
        is_active_ancestor=is_ancestor_of_active(item, active) and (active is None or item.key != active.key),
        is_section_header=item.section_header,
        is_external=is_external,
        is_disabled=is_disabled,
        children=children,
    )


@register.inclusion_tag("brickwork/nav/_nav.html")
def bw_nav(items: tuple[NavItem, ...], active: NavItem | None = None) -> dict:
    """Render the nav tree. ``items`` should already be visibility-filtered
    (via visible_items in a context processor); ``active`` from resolve_active_item."""
    fallback = get_setting("BRICKWORK_NAV_FALLBACK")
    prepared = tuple(p for item in items if (p := _prepare(item, active, fallback)) is not None)
    return {"bw_nav_tree": prepared}
