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


def _kwarg_name_pair(kwarg_name: str | tuple[str, str]) -> tuple[str, str]:
    """Normalise a ``kwarg_name`` to a (source, target) pair. A bare string means
    the source and target names are the same."""
    if isinstance(kwarg_name, tuple):
        return kwarg_name
    return (kwarg_name, kwarg_name)


def _effective_kwargs(item: NavItem, resolver_match) -> dict:
    """The reverse kwargs for an item, merged in precedence order: static
    ``url_kwargs``, then the declarative ``kwarg_name`` copy (#19), then the
    ``url_kwargs_from_request`` callable (which wins for genuinely complex cases).
    """
    kwargs = dict(item.url_kwargs)
    if item.kwarg_name is not None and resolver_match is not None:
        source, target = _kwarg_name_pair(item.kwarg_name)
        route_kwargs = getattr(resolver_match, "kwargs", None) or {}
        if source in route_kwargs:
            kwargs[target] = route_kwargs[source]
    if item.url_kwargs_from_request is not None:
        derived = item.url_kwargs_from_request(resolver_match) or {}
        kwargs.update(derived)
    return kwargs


def _prepare(item: NavItem, active: NavItem | None, fallback: str, resolver_match) -> RenderedNavItem | None:
    """Prepare one item for render, or None if it should be omitted entirely."""
    href: str | None = None
    is_disabled = False
    is_external = item.external_url is not None

    if item.section_header:
        href = None
    elif is_external:
        href = item.external_url
    elif item.url_name is not None:
        href = safe_reverse(item.url_name, _effective_kwargs(item, resolver_match))
        if href is None:
            # BR-BW-NAV-003 / NAV-015: a bad url_name never 500s. Either drop the
            # item ("omit") or render it disabled ("disabled"), per the setting.
            # A route-parameter item whose kwargs are not yet available (e.g. no
            # project selected) resolves to None here and follows the same path.
            if fallback == "omit":
                return None
            is_disabled = True

    children = tuple(
        prepared
        for child in item.children
        if (prepared := _prepare(child, active, fallback, resolver_match)) is not None
    )

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


@register.inclusion_tag("brickwork/nav/_nav.html", takes_context=True)
def bw_nav(
    context,
    items: tuple[NavItem, ...],
    active: NavItem | None = None,
    resolver_match=None,
) -> dict:
    """Render the nav tree. ``items`` should already be visibility-filtered
    (via visible_items in a context processor); ``active`` from resolve_active_item.

    ``resolver_match`` drives route-parameter-dependent item URLs
    (``NavItem.url_kwargs_from_request``); it defaults to the current request's
    ``resolver_match`` from the template context, so a consumer rarely passes it
    explicitly."""
    if resolver_match is None:
        request = context.get("request")
        resolver_match = getattr(request, "resolver_match", None)
    fallback = get_setting("BRICKWORK_NAV_FALLBACK")
    prepared = tuple(p for item in items if (p := _prepare(item, active, fallback, resolver_match)) is not None)
    return {"bw_nav_tree": prepared}
