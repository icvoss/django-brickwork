"""Navigation services: validation, visibility, active-route resolution, safe reverse.

The Navigation contract (contract #3 of 5). Every rule here is tested against
02-business-rules.md's BR-BW-NAV-* set:

- validate_nav_config: duplicate keys raise at import time (BR-BW-NAV-002).
- visible_items: permission/feature/policy filtering via host-injected callables
  only (BR-BW-NAV-004); visibility is display, never authorisation (BR-BW-NAV-005).
- resolve_active_item: active state via resolver_match, never path.startswith
  (BR-BW-NAV-001); a parent is active when a descendant matches (NAV-008).
- safe_reverse: a bad url_name never 500s (BR-BW-NAV-003); it logs and the
  renderer omits or disables the item per BRICKWORK_NAV_FALLBACK (NAV-015).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.urls import NoReverseMatch, reverse

from brickwork.exceptions import NavConfigError

if TYPE_CHECKING:
    from django.urls import ResolverMatch

    from brickwork.models import NavContext, NavItem

logger = logging.getLogger("brickwork.navigation")


def _walk(items: Iterable[NavItem]):
    """Yield every NavItem in the tree, depth-first (parents before children)."""
    for item in items:
        yield item
        yield from _walk(item.children)


def validate_nav_config(nav_items: Iterable[NavItem]) -> None:
    """Raise NavConfigError on a duplicate ``key`` anywhere in the tree.

    Called once at import time by the consuming project (BR-BW-NAV-002), so a
    nav-collision bug fails loudly on startup, never silently keeps one entry and
    never surfaces at request time. Keys must be unique across the WHOLE tree, not
    just per level, since ``key`` is how a consumer's context targets an item.
    """
    seen: set[str] = set()
    for item in _walk(nav_items):
        if item.key in seen:
            raise NavConfigError(
                f"Duplicate nav-item key {item.key!r}. Keys must be unique across "
                f"the whole navigation tree (BR-BW-NAV-002)."
            )
        seen.add(item.key)


def _item_visible(item: NavItem, context: NavContext) -> bool:
    """Whether one item passes its permission/feature/policy checks.

    Section headers are visible iff at least one descendant is visible (an empty
    group renders nothing). All checks go through the host-injected callables on
    ``context`` (BR-BW-NAV-004); brickwork calls no Django permission API itself.
    """
    check_perm = context.permission_checker
    check_feature = context.feature_checker

    if item.required_permissions and not all(check_perm(p) for p in item.required_permissions):
        return False
    if item.any_permissions and not any(check_perm(p) for p in item.any_permissions):
        return False
    if item.required_features and not all(check_feature(f) for f in item.required_features):
        return False
    return not (item.visibility_policy is not None and not item.visibility_policy(context))


def visible_items(nav_items: Iterable[NavItem], context: NavContext) -> tuple[NavItem, ...]:
    """Return the nav tree filtered to items visible to the current user.

    Recurses into ``children``, dropping hidden items. A section header is kept
    only if it still has at least one visible child after filtering (never an
    empty group label). Visibility is a display-layer convenience, NEVER
    authorisation (BR-BW-NAV-005): the consuming project's own views enforce
    access independently.
    """
    result: list[NavItem] = []
    for item in nav_items:
        if not _item_visible(item, context):
            continue
        visible_children = visible_items(item.children, context) if item.children else ()
        if item.section_header and not visible_children:
            continue  # an empty group renders nothing
        # rebuild the item with its filtered children (frozen dataclass)
        from dataclasses import replace

        result.append(replace(item, children=visible_children) if item.children else item)
    return tuple(result)


def resolve_active_item(
    nav_items: Iterable[NavItem],
    resolver_match: ResolverMatch | None,
) -> NavItem | None:
    """Return the deepest NavItem matching the current route, or None.

    Matches ``resolver_match.view_name`` against each item's ``url_name``
    (BR-BW-NAV-001), NEVER ``request.path.startswith(...)``. Returns the deepest
    (leaf) match, so a specific child wins over an ancestor; the renderer marks
    both the leaf and its ancestors active for styling (NAV-008), which it derives
    by checking whether the active item is within a given item's subtree.

    ``resolver_match`` is None for an unresolved request (e.g. a 404), in which
    case nothing is active.
    """
    if resolver_match is None:
        return None
    view_name = resolver_match.view_name
    match: NavItem | None = None
    for item in _walk(nav_items):
        if item.url_name is not None and item.url_name == view_name:
            match = item  # keep the last (deepest) match in depth-first order
    return match


def is_ancestor_of_active(item: NavItem, active: NavItem | None) -> bool:
    """Whether ``active`` is ``item`` itself or lies within its subtree (NAV-008).

    Used by the nav template to give an ancestor the active treatment when a
    descendant is the current route.
    """
    if active is None:
        return False
    return any(descendant.key == active.key for descendant in _walk([item]))


def safe_reverse(url_name: str, url_kwargs: dict | None = None) -> str | None:
    """Reverse ``url_name`` (with kwargs), returning None instead of raising.

    A NavItem whose ``url_name`` does not resolve (typo, removed URL, app not
    installed) must NEVER produce a 500 (BR-BW-NAV-003). This catches
    NoReverseMatch, logs at warning level so a consumer's logging can surface it,
    and returns None; the nav renderer then omits or disables the item per
    BRICKWORK_NAV_FALLBACK (NAV-015).
    """
    try:
        return reverse(url_name, kwargs=url_kwargs or None)
    except NoReverseMatch:
        logger.warning(
            "brickwork: nav item url_name %r did not resolve (kwargs=%r); "
            "item omitted or disabled per BRICKWORK_NAV_FALLBACK.",
            url_name,
            url_kwargs,
        )
        return None
