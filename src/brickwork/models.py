"""brickwork data shapes: the navigation dataclasses (01-models.md).

These are NOT Django ORM models: brickwork ships no migrations. ``NavItem`` and
``NavContext`` are plain, frozen dataclasses a consuming project instantiates in
its own nav configuration module (typically ``apps/core/nav.py``), never
persisted. See 01-models.md for why a dataclass, not an ORM model.

Phase-0 model-gap closures (the-wall "Model gaps"): ``NavItem`` gains ``badge``
(NAV-010, a count/tag), ``external_url`` (NAV-018, an off-site link), and a
``section_header`` variant (NAV-002, a non-navigable grouping label).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.urls import ResolverMatch


@dataclass(frozen=True)
class NavItem:
    """One entry in a consuming project's navigation configuration.

    Instantiated by the host application, never by brickwork itself. Immutable: a
    nav configuration is assembled once at startup (or per request for a
    request-scoped ``visibility_policy``), not mutated in place.

    An item is one of three shapes:

    - a normal link: ``url_name`` set (internal Django URL name).
    - an external link: ``external_url`` set instead of ``url_name`` (NAV-018).
    - a section header: ``section_header=True`` with neither URL (NAV-002); a
      non-navigable grouping label, optionally with ``children``.
    """

    key: str
    """Unique identifier within the enclosing nav configuration. Duplicate keys
    raise NavConfigError at startup (BR-BW-NAV-002), never silently overwrite."""

    label: str
    """Display text. The consumer supplies its own i18n-wrapped string."""

    url_name: str | None = None
    """A Django URL name, resolved via {% url %} at render time (never a raw path
    string, so the active-route resolver can use resolver_match). ``None`` for a
    section header or an external link."""

    active_url_names: tuple[str, ...] = ()
    """Additional URL names for which this item is the active section, beyond its
    own ``url_name`` (#20). A real section is "current" for its list view AND its
    detail/sub views: e.g. a Team item links to ``tenants:members`` but should
    stay active on ``tenants:member-invite`` too. List those secondary route
    names here. ``url_name`` remains the single LINK target; active-matching
    widens to ``url_name`` plus every name in this tuple. Does not affect
    reversal, only which route lights the item up (BR-BW-NAV-001, still
    resolver_match-based, never path.startswith)."""

    url_kwargs: dict = field(default_factory=dict)
    """Static keyword arguments passed when reversing ``url_name``, fixed at
    nav-definition time."""

    kwarg_name: str | tuple[str, str] | None = None
    """The declarative common case of ``url_kwargs_from_request`` (NAV, #19): copy
    ONE route parameter from the active route into this item's reverse kwargs.

    - ``kwarg_name="slug"``: take ``resolver_match.kwargs["slug"]`` from the
      current route and pass it to the reverse under the SAME name ``slug``.
    - ``kwarg_name=("project_slug", "slug")``: read it under the SOURCE name the
      active route uses (``project_slug``) and pass it to the reverse under the
      TARGET name this item's URL expects (``slug``). This covers the frequent
      case where one app names the same conceptual parameter differently across
      routes, without hand-writing a fallback callable.

    Resolved at render time and merged into the reverse kwargs alongside
    ``url_kwargs`` / ``url_kwargs_from_request``. If the source kwarg is absent
    from the current route (e.g. no project selected yet), it contributes
    nothing and the item follows BRICKWORK_NAV_FALLBACK like any unresolvable
    URL, never a 500 (BR-BW-NAV-003). For anything more complex than a single
    parameter copy/rename, use ``url_kwargs_from_request``."""

    url_kwargs_from_request: Callable[[ResolverMatch | None], dict] | None = None
    """An optional callable that derives reverse kwargs from the CURRENT request's
    route at render time (NAV, route-parameter-dependent URLs). Given the active
    ``request.resolver_match``, it returns a dict merged OVER ``url_kwargs``. This
    lets a project-scoped item (e.g. ``projects/<slug>/documents/``) live in the
    sidebar even though ``<slug>`` is only known per request, not at nav-assembly
    time. Typical use: ``lambda rm: {"slug": rm.kwargs["slug"]} if rm and "slug"
    in rm.kwargs else {}``. For the single-parameter common case prefer the
    declarative ``kwarg_name`` above. When both are set, ``url_kwargs_from_request``
    is applied last (it wins). If it returns kwargs that do not satisfy the pattern
    (e.g. no project selected yet), the item falls back to BRICKWORK_NAV_FALLBACK
    like any unresolvable URL, never a 500 (BR-BW-NAV-003)."""

    external_url: str | None = None
    """An off-site URL (NAV-018). Mutually exclusive with ``url_name``: an
    external link is rendered as an ordinary anchor and never participates in
    active-route resolution (resolver_match cannot match an external href)."""

    section_header: bool = False
    """True marks this a non-navigable grouping label (NAV-002), rendered as a
    header above its ``children`` rather than a link. Carries no URL."""

    icon: str | None = None
    """A brickwork icon registry name (ICO-011), resolved through {% bw_icon %};
    an opaque identifier here."""

    badge: str | int | None = None
    """An optional count or tag shown alongside the label (NAV-010), e.g. an
    unread count "12" or a "New" tag. Display-only; carries no behaviour."""

    children: tuple[NavItem, ...] = ()
    """Nested nav items, for a grouped/expandable section."""

    required_permissions: tuple[str, ...] = ()
    """ALL of these must be satisfied for visibility (AND). Checked via a
    host-injected callable, never a hardcoded permission call (BR-BW-NAV-004)."""

    any_permissions: tuple[str, ...] = ()
    """At least ONE of these must be satisfied (OR). Combined with
    ``required_permissions`` when both are set: both conditions must hold."""

    required_features: tuple[str, ...] = ()
    """Feature-flag names that must ALL be enabled, checked via the host-injected
    feature checker (independent of the permission checker)."""

    visibility_policy: Callable[[NavContext], bool] | None = None
    """An optional host predicate for visibility that does not fit the
    permission/feature shape. Evaluated last, after permission and feature checks
    pass; returning False hides the item regardless."""


@dataclass(frozen=True)
class NavContext:
    """Passed to a ``visibility_policy`` callable and to ``visible_items``.

    Deliberately minimal and host-agnostic: it carries only the callables the
    resolver needs, never a named tenant/user attribute brickwork would have to
    assume the shape of (BR-BW-NAV-004; request.tenant vs request.merchant
    diverge across consumers).
    """

    request: HttpRequest
    permission_checker: Callable[[str], bool] = lambda _perm: True
    feature_checker: Callable[[str], bool] = lambda _flag: True
    """``permission_checker`` and ``feature_checker`` both default to permissive
    (everything visible). An app that gates access with Django model permissions
    passes ``request.user.has_perm``; an app that authorises per object/scope in
    the view layer (RBAC, membership) leaves them at the default and relies on its
    own view-level enforcement, which is mandatory regardless (BR-BW-NAV-005: nav
    visibility is display, never authorisation). Neither is required."""
