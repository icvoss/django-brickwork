"""The nav renderers: filtered, active-aware renders over one NavItem tree.

Three tags share one prepare pipeline (URL resolution via safe_reverse,
honouring BRICKWORK_NAV_FALLBACK for a bad url_name per BR-BW-NAV-003, and
the active/ancestor-active state per NAV-008); each renders a different
template over the SAME prepared tree, so there is never a second nav data
model (brickwork#82's founding constraint):

- ``{% bw_nav %}``: the recursive sidebar/tree renderer (nav/_nav.html).
  One render is shared by the desktop sidebar and the mobile drawer
  (NAV-016).
- ``{% bw_nav_header %}`` (brickwork#102): the horizontal marketing-header
  row (nav/_nav_header.html), plain-anchor visual weight with active state,
  for the marketing shell's ``marketing_nav`` block and menu-driven header
  navs on the NAV-019 href seam.
- ``{% bw_nav_rail %}`` (brickwork#82): the compact icon+label rail
  (nav/_nav_rail.html), tier one of the capability-rail + contextual-sidebar
  layout, paired with an ordinary ``{% bw_nav %}`` as tier two.

Usage (in a shell block, after a context processor has run visible_items +
resolve_active_item)::

    {% load brickwork_nav %}
    {% bw_nav items=bw_nav_items active=bw_active_nav_item %}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django import template
from django.utils.functional import Promise

from brickwork.conf import get_setting
from brickwork.icons.registry import IconNotFoundError, _suggest, has_icon
from brickwork.services.navigation import is_ancestor_of_active, safe_reverse

if TYPE_CHECKING:
    from brickwork.models import NavItem

register = template.Library()


@dataclass(frozen=True)
class RenderedNavItem:
    """A NavItem prepared for template rendering: URL resolved, state computed."""

    key: str
    # str | Promise, matching NavItem.label (models.py, brickwork#131): a
    # gettext_lazy() label is passed straight through unresolved here too, so
    # per-request language switching keeps working. Narrowing this to str would
    # require forcing it with str() somewhere upstream, evaluating the
    # translation once instead of per render.
    label: str | Promise
    href: str | None  # resolved URL, external URL, or None (header/disabled)
    icon: str | None
    badge: str | Promise | int | None  # matches NavItem.badge; same lazy-label reasoning as label above
    is_active: bool  # this exact item is the current route
    is_active_ancestor: bool  # a descendant is the current route (NAV-008)
    is_section_header: bool
    is_external: bool
    is_disabled: bool  # a bad url_name under the "disabled" fallback
    opens_in_new_tab: bool  # target=_blank, independent of is_external (NAV-020)
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


def _resolve_new_tab(opens_in_new_tab: bool | None, is_external: bool) -> bool:
    """Resolve the tri-state NavItem.opens_in_new_tab to a concrete bool.

    ``None`` keeps the historical default (external links open a new tab, internal
    links do not, so existing configs are byte-identical); an explicit bool wins.
    """
    if opens_in_new_tab is None:
        return is_external
    return opens_in_new_tab


def _prepare(
    item: NavItem, active: NavItem | None, fallback: str, resolver_match, current_path: str | None = None
) -> RenderedNavItem | None:
    """Prepare one item for render, or None if it should be omitted entirely."""
    href: str | None = None
    is_disabled = False
    is_external = item.external_url is not None

    # Validate the icon name here, at prepare time, rather than letting an
    # unregistered name reach {% bw_icon %} inside the recursive {% partialdef %}
    # in nav/_nav.html. Historically a get_icon() miss raised mid-partialdef was
    # swallowed by Django's template-partials machinery (its bare `except
    # KeyError`) and re-surfaced as a misleading "Partial 'nav_item' is not
    # defined in the current template." (icvoss/django-brickwork#89). #74 fixed
    # the masking at the root (IconNotFoundError is no longer a KeyError), but
    # this eager check stays: raising at prepare time names the offending
    # NavItem, a better diagnostic than a miss deep inside the recursive render.
    # Mirrors the eager url_name resolution below (both catch a bad NavItem
    # before render).
    if item.icon is not None and not has_icon(item.icon):
        suggestion = _suggest(item.icon)
        hint = f" Did you mean {suggestion!r}?" if suggestion else ""
        raise IconNotFoundError(
            f"NavItem {item.key!r} has icon {item.icon!r}, which is not a registered "
            f"brickwork icon.{hint} Use a registered name (brickwork.icons.ICON_NAMES) "
            f"or register it via brickwork.icons.register_icons()."
        )

    if item.section_header:
        href = None
    elif is_external:
        href = item.external_url
    elif item.href is not None:
        # A raw, already-resolved internal path (NAV-019): rendered as-is, no
        # reverse, no external affordance. Active state is by path match below.
        href = item.href
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
        if (prepared := _prepare(child, active, fallback, resolver_match, current_path)) is not None
    )

    # a section header with no surviving children renders nothing
    if item.section_header and not children:
        return None

    # Active state: normally by the resolved `active` NavItem (key match). A raw
    # `href` item cannot participate in that resolution (it has no url_name for
    # resolve_active_item to match), so it falls back to a direct path match
    # against the current request path (NAV-019). The key match still wins when
    # present, so an href item explicitly passed as `active` is honoured too.
    is_active = active is not None and item.key == active.key
    if not is_active and item.href is not None and current_path is not None:
        is_active = item.href == current_path

    return RenderedNavItem(
        key=item.key,
        label=item.label,
        href=href,
        icon=item.icon,
        badge=item.badge,
        is_active=is_active,
        is_active_ancestor=is_ancestor_of_active(item, active) and (active is None or item.key != active.key),
        is_section_header=item.section_header,
        is_external=is_external,
        is_disabled=is_disabled,
        # New-tab is its own axis (NAV-020), tri-state: None keeps the historical
        # default (external links open a new tab, internal links do not), an
        # explicit bool overrides either way. Never on a section header (no link).
        opens_in_new_tab=_resolve_new_tab(item.opens_in_new_tab, is_external) and not item.section_header,
        children=children,
    )


def _prepare_tree(
    context,
    items: tuple[NavItem, ...],
    active: NavItem | None,
    resolver_match,
) -> tuple[RenderedNavItem, ...]:
    """The shared prepare step behind every renderer tag: resolve the request's
    resolver_match and path from the template context, then prepare each item.
    One pipeline, several renderers (brickwork#82/#102), so the three tags can
    never drift in URL resolution, fallback handling, or active-state rules."""
    request = context.get("request")
    if resolver_match is None:
        resolver_match = getattr(request, "resolver_match", None)
    # The current path drives active state for raw-`href` items (NAV-019), which
    # cannot be matched via resolver_match. None when there is no request (a
    # context-free render), in which case href items simply never read active.
    current_path = getattr(request, "path", None)
    fallback = get_setting("BRICKWORK_NAV_FALLBACK")
    return tuple(
        p for item in items if (p := _prepare(item, active, fallback, resolver_match, current_path)) is not None
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
    return {"bw_nav_tree": _prepare_tree(context, items, active, resolver_match)}


@register.inclusion_tag("brickwork/nav/_nav_header.html", takes_context=True)
def bw_nav_header(
    context,
    items: tuple[NavItem, ...],
    active: NavItem | None = None,
    resolver_match=None,
) -> dict:
    """Render the horizontal marketing-header row over the same NavItem tree
    (brickwork#102): plain-anchor visual weight matching the marketing shell's
    own header links, with the active state and visibility gating plain anchors
    lose. Same arguments and preparation as ``{% bw_nav %}``; only the render
    target differs. Flat by design: see nav/_nav_header.html's own contract."""
    return {"bw_nav_tree": _prepare_tree(context, items, active, resolver_match)}


@register.inclusion_tag("brickwork/nav/_nav_rail.html", takes_context=True)
def bw_nav_rail(
    context,
    items: tuple[NavItem, ...],
    active: NavItem | None = None,
    resolver_match=None,
) -> dict:
    """Render the compact icon+label rail over the same NavItem tree
    (brickwork#82): tier one of the capability-rail + contextual-sidebar
    layout, paired with an ordinary ``{% bw_nav %}`` as the contextual second
    tier. Same arguments and preparation as ``{% bw_nav %}``; only the render
    target differs. See nav/_nav_rail.html's own contract."""
    return {"bw_nav_tree": _prepare_tree(context, items, active, resolver_match)}
