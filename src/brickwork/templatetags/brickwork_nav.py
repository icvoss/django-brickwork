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
- ``{% bw_flyout %}`` (brickwork#758): optional rail flyout panel companion
  for ``menu_trigger`` buttons (nav/_flyout.html). Progressive enhancement;
  the no-JS floor stays the drawer ``{% bw_nav %}`` tree.

Usage (in a shell block, after a context processor has run visible_items +
resolve_active_item)::

    {% load brickwork_nav %}
    {% bw_nav items=bw_nav_items active=bw_active_nav_item %}
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from django import template
from django.template import TemplateSyntaxError
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
    is_menu_trigger: bool  # rail button with aria-haspopup (brickwork#702)
    is_external: bool
    is_disabled: bool  # a bad url_name under the "disabled" fallback
    opens_in_new_tab: bool  # target=_blank, independent of is_external (NAV-020)
    children: tuple[RenderedNavItem, ...]


def _walk_rendered(tree: tuple[RenderedNavItem, ...]):
    """Yield every prepared item in the tree, depth-first."""
    for item in tree:
        yield item
        if item.children:
            yield from _walk_rendered(item.children)


def _collapsible_open_inactive(tree: tuple[RenderedNavItem, ...]) -> bool:
    """True when no section header in the tree is an active ancestor (#773)."""
    return not any(
        item.is_section_header and item.is_active_ancestor for item in _walk_rendered(tree)
    )

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

    if item.section_header or item.menu_trigger:
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
    # a menu trigger that only existed to group children drops when empty;
    # a childless trigger (panel content owned outside the tree) still renders
    if item.menu_trigger and item.children and not children:
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
        is_menu_trigger=item.menu_trigger,
        is_external=is_external,
        is_disabled=is_disabled,
        # New-tab is its own axis (NAV-020), tri-state: None keeps the historical
        # default (external links open a new tab, internal links do not), an
        # explicit bool overrides either way. Never on a section header or menu
        # trigger (no link).
        opens_in_new_tab=_resolve_new_tab(item.opens_in_new_tab, is_external)
        and not item.section_header
        and not item.menu_trigger,
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


_NAV_LABELS = frozenset({"truncate", "wrap"})
# ADR-125 (django-brickwork#745): the rail's labelled-or-icons choice is a
# component variant, not the global density axis (comfortable|compact|spacious).
_RAIL_VARIANTS = frozenset({"labelled", "icons"})


@register.inclusion_tag("brickwork/nav/_nav.html", takes_context=True)
def bw_nav(
    context,
    items: tuple[NavItem, ...],
    active: NavItem | None = None,
    resolver_match=None,
    orientation: str = "vertical",
    labels: str = "truncate",
    collapsible_sections: bool = False,
) -> dict:
    """Render the nav tree. ``items`` should already be visibility-filtered
    (via visible_items in a context processor); ``active`` from resolve_active_item.

    ``resolver_match`` drives route-parameter-dependent item URLs
    (``NavItem.url_kwargs_from_request``); it defaults to the current request's
    ``resolver_match`` from the template context, so a consumer rarely passes it
    explicitly.

    ``orientation`` is ``"vertical"`` (default, sidebar column) or
    ``"horizontal"`` (wrapping row with block-end active marker). Any other
    value falls back to vertical. App-shell horizontal chrome for the recursive
    sidebar renderer (icvoss/django-brickwork#430, NAV-024); marketing header
    rows stay on ``{% bw_nav_header %}``. The topbar shell layout still forces
    a horizontal band via its own layout CSS when ``data-layout="topbar"``.

    ``labels`` is ``"truncate"`` (default: ellipsis on overflow, right for an
    app sidebar) or ``"wrap"`` (multi-line labels, right for a docs rail of
    document titles). Closed vocabulary (icvoss/django-brickwork#671).
    
    collapsible_sections opts vertical section_header rows with children
    into native <details> folds (icvoss/django-brickwork#773). Default
    False preserves the historical span markup. Horizontal orientation and
    menu_trigger rows ignore the flag; the tag passes
    collapsible_open_inactive when no section in the tree is an active
    ancestor so top-level routes keep every section expanded.
    """
    resolved = orientation if orientation == "horizontal" else "vertical"
    if labels not in _NAV_LABELS:
        raise TemplateSyntaxError(f"bw_nav labels must be one of {sorted(_NAV_LABELS)}, got {labels!r}")
    tree = _prepare_tree(context, items, active, resolver_match)
    return {
        "bw_nav_tree": tree,
        "orientation": resolved,
        "labels": labels,
        "collapsible_sections": collapsible_sections,
        "collapsible_open_inactive": _collapsible_open_inactive(tree),
    }


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
    variant: str | None = None,
    density: str | None = None,
) -> dict:
    """Render the compact icon+label rail over the same NavItem tree
    (brickwork#82): tier one of the capability-rail + contextual-sidebar
    layout, paired with an ordinary ``{% bw_nav %}`` as the contextual second
    tier. Same arguments and preparation as ``{% bw_nav %}``; only the render
    target differs. See nav/_nav_rail.html's own contract.

    ``variant`` is ``"labelled"`` (default: caption labels always visible) or
    ``"icons"`` (icon-only at rest, labels on hover/focus-within expand;
    brickwork#701). Closed vocabulary.

    ``density`` is the DEPRECATED former spelling of ``variant`` (ADR-125,
    django-brickwork#745: ``density`` names the global comfortable, compact and
    spacious axis, and one name must not mean two things). It still accepts
    ``"labelled"`` / ``"icons"`` and emits a ``DeprecationWarning``; it is
    removed in the next major. Passing both with different values raises.
    """
    if density is not None:
        warnings.warn(
            "bw_nav_rail density= is deprecated; use variant= ('labelled' | 'icons'). "
            "density names the global comfortable|compact|spacious axis (ADR-125). "
            "It is removed in the next major.",
            DeprecationWarning,
            stacklevel=2,
        )
        if density not in _RAIL_VARIANTS:
            raise TemplateSyntaxError(
                f"bw_nav_rail density must be one of {sorted(_RAIL_VARIANTS)} (use variant= instead), got {density!r}"
            )
        if variant is not None and variant != density:
            raise TemplateSyntaxError(
                f"bw_nav_rail got variant={variant!r} and density={density!r}; pass variant= only."
            )
        variant = density
    if variant is None:
        variant = "labelled"
    if variant not in _RAIL_VARIANTS:
        raise TemplateSyntaxError(f"bw_nav_rail variant must be one of {sorted(_RAIL_VARIANTS)}, got {variant!r}")
    return {
        "bw_nav_tree": _prepare_tree(context, items, active, resolver_match),
        "variant": variant,
    }


def _normalise_flyout_link(link: object, *, panel_key: str, index: int) -> dict[str, Any]:
    """Coerce one flyout link mapping into the template contract."""
    if not isinstance(link, Mapping):
        raise TemplateSyntaxError(
            f"bw_flyout panels[{panel_key!r}][{index}] must be a mapping with href and label, got {type(link).__name__}"
        )
    if "href" not in link or "label" not in link:
        raise TemplateSyntaxError(f"bw_flyout panels[{panel_key!r}][{index}] requires href= and label= keys")
    return {
        "href": link["href"] or "#",
        "label": link["label"],
        "badge": link.get("badge"),
    }


def _panels_from_mapping(panels: Mapping[object, object]) -> list[dict[str, Any]]:
    """Turn a key -> links mapping into ordered panel dicts for the template."""
    out: list[dict[str, Any]] = []
    for key, links in panels.items():
        panel_key = str(key)
        if isinstance(links, (str, bytes)) or not isinstance(links, Sequence):
            raise TemplateSyntaxError(
                f"bw_flyout panels[{panel_key!r}] must be a sequence of link mappings, got {type(links).__name__}"
            )
        out.append(
            {
                "key": panel_key,
                "links": tuple(
                    _normalise_flyout_link(link, panel_key=panel_key, index=i) for i, link in enumerate(links)
                ),
            }
        )
    return out


def _panels_from_menu_triggers(
    context,
    items: tuple[NavItem, ...],
    active: NavItem | None,
    resolver_match,
) -> list[dict[str, Any]]:
    """Derive flyout panels from prepared menu_trigger items that have children."""
    tree = _prepare_tree(context, items, active, resolver_match)
    out: list[dict[str, Any]] = []

    def walk(nodes: tuple[RenderedNavItem, ...]) -> None:
        for node in nodes:
            if node.is_menu_trigger and node.children:
                out.append(
                    {
                        "key": node.key,
                        "links": tuple(
                            {
                                "href": child.href or "#",
                                "label": child.label,
                                "badge": child.badge,
                            }
                            for child in node.children
                            if not child.is_section_header and not child.is_menu_trigger
                        ),
                    }
                )
            if node.children:
                walk(node.children)

    walk(tree)
    return out


@register.inclusion_tag("brickwork/nav/_flyout.html", takes_context=True)
def bw_flyout(
    context,
    panels: Mapping[object, object] | None = None,
    items: tuple[NavItem, ...] | None = None,
    active: NavItem | None = None,
    resolver_match=None,
) -> dict:
    """Render the optional rail flyout panel companion (brickwork#758).

    Pass either:

    - ``panels``: a mapping of trigger key -> sequence of
      ``{href, label, badge?}`` link dicts (the host-prepared shape used by
      ui_studio), or
    - ``items``: the same NavItem tree as ``{% bw_nav_rail %}``; panels are
      derived from ``menu_trigger=True`` entries that have children.

    Passing both raises. Passing neither raises. Pair with
    ``{% bw_nav_rail %}`` buttons that emit ``data-bw-nav-menu-trigger``;
    ``bwNavFlyout`` (or host Alpine) toggles visibility and ``aria-expanded``.
    The no-JS floor is the drawer ``{% bw_nav %}`` tree, not this panel.
    """
    if panels is not None and items is not None:
        raise TemplateSyntaxError("bw_flyout accepts panels= or items=, not both")
    if panels is None and items is None:
        raise TemplateSyntaxError("bw_flyout requires panels= or items=")
    if panels is not None:
        if not isinstance(panels, Mapping):
            raise TemplateSyntaxError(
                f"bw_flyout panels= must be a mapping of key to link sequences, got {type(panels).__name__}"
            )
        prepared = _panels_from_mapping(panels)
    else:
        assert items is not None
        prepared = _panels_from_menu_triggers(context, items, active, resolver_match)
    return {"panels": prepared}
