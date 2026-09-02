"""Navigation contract tests (BR-BW-NAV-*).

Service-level tests use a fake resolver_match and mock checkers; safe_reverse
runs against the real (empty) urlconf plus a monkeypatched reverse for the
resolve cases. The end-to-end nav render (active state, badge, external, section
header) is exercised in test_integration.py against the testapp's real URLs.
"""

from __future__ import annotations

import pytest
from django.urls import NoReverseMatch

from brickwork.exceptions import NavConfigError
from brickwork.models import NavContext, NavItem
from brickwork.services import navigation


class _FakeMatch:
    def __init__(self, view_name: str, kwargs: dict | None = None) -> None:
        self.view_name = view_name
        self.kwargs = kwargs or {}


def _ctx(*, perms=(), features=()):
    return NavContext(
        request=None,
        permission_checker=lambda p: p in perms,
        feature_checker=lambda f: f in features,
    )


# --- #6: permission_checker / feature_checker are optional (permissive default) ---


def test_navcontext_permission_checker_is_optional() -> None:
    # An object/scope-authorised app (RBAC, not model perms) constructs a context
    # with neither checker and relies on its own view-level enforcement; brickwork
    # defaults to "everything visible" (BR-BW-NAV-005: visibility is not auth).
    ctx = NavContext(request=None)
    nav = (
        NavItem(key="a", label="A", url_name="a"),
        NavItem(key="b", label="B", url_name="b", required_permissions=("some.perm",)),
    )
    visible = navigation.visible_items(nav, ctx)
    # with the permissive default, a permission-gated item is still shown
    assert {i.key for i in visible} == {"a", "b"}


def test_navcontext_still_honours_a_supplied_permission_checker() -> None:
    ctx = NavContext(request=None, permission_checker=lambda p: p == "yes.perm")
    nav = (
        NavItem(key="ok", label="OK", url_name="ok", required_permissions=("yes.perm",)),
        NavItem(key="no", label="No", url_name="no", required_permissions=("nope",)),
    )
    assert {i.key for i in navigation.visible_items(nav, ctx)} == {"ok"}


# --- BR-BW-NAV-002: duplicate keys raise at config time ---------------------


def test_validate_nav_config_raises_on_duplicate_key() -> None:
    nav = (
        NavItem(key="dash", label="Dashboard", url_name="dash"),
        NavItem(key="dash", label="Other", url_name="other"),
    )
    with pytest.raises(NavConfigError):
        navigation.validate_nav_config(nav)


def test_validate_nav_config_catches_duplicate_in_children() -> None:
    nav = (
        NavItem(
            key="top",
            label="Top",
            section_header=True,
            children=(
                NavItem(key="a", label="A", url_name="a"),
                NavItem(key="a", label="A2", url_name="a2"),
            ),
        ),
    )
    with pytest.raises(NavConfigError):
        navigation.validate_nav_config(nav)


def test_validate_nav_config_accepts_unique_keys() -> None:
    nav = (
        NavItem(key="a", label="A", url_name="a"),
        NavItem(key="b", label="B", url_name="b"),
    )
    navigation.validate_nav_config(nav)  # must not raise


def test_validate_nav_config_rejects_active_url_names_without_url_name() -> None:
    # active_url_names on a link-less item can never match (only a LINK item
    # participates in active-route resolution), so the config-time validator
    # rejects it instead of leaving a silent no-op.
    nav = (
        NavItem(
            key="grp",
            label="Group",
            section_header=True,
            active_url_names=("tenants:members",),
        ),
    )
    with pytest.raises(NavConfigError):
        navigation.validate_nav_config(nav)


def test_validate_nav_config_accepts_active_url_names_with_url_name() -> None:
    nav = (
        NavItem(
            key="team",
            label="Team",
            url_name="tenants:members",
            active_url_names=("tenants:member-invite",),
        ),
    )
    navigation.validate_nav_config(nav)  # must not raise


# --- BR-BW-NAV-001 / NAV-008: active via resolver_match, tree walk ----------


def test_resolve_active_matches_view_name_not_path() -> None:
    nav = (NavItem(key="w", label="Widgets", url_name="testapp:widget-list"),)
    active = navigation.resolve_active_item(nav, _FakeMatch("testapp:widget-list"))
    assert active is not None
    assert active.key == "w"


def test_resolve_active_returns_none_for_no_match() -> None:
    nav = (NavItem(key="w", label="Widgets", url_name="a"),)
    assert navigation.resolve_active_item(nav, _FakeMatch("b")) is None


def test_resolve_active_returns_none_for_unresolved_request() -> None:
    nav = (NavItem(key="w", label="Widgets", url_name="a"),)
    assert navigation.resolve_active_item(nav, None) is None


def test_resolve_active_finds_a_child_and_parent_is_ancestor() -> None:
    child = NavItem(key="leaf", label="Leaf", url_name="leaf")
    parent = NavItem(key="grp", label="Group", section_header=True, children=(child,))
    active = navigation.resolve_active_item((parent,), _FakeMatch("leaf"))
    assert active.key == "leaf"
    assert navigation.is_ancestor_of_active(parent, active) is True
    assert navigation.is_ancestor_of_active(child, active) is True


# --- #20: active_url_names widens active-matching ----------------------------


def test_active_url_names_secondary_view_name_matches() -> None:
    # A section item is "current" on its detail/sub views too: the Team item
    # links to tenants:members but lights up on tenants:member-invite as well.
    nav = (
        NavItem(
            key="team",
            label="Team",
            url_name="tenants:members",
            active_url_names=("tenants:member-invite",),
        ),
    )
    active = navigation.resolve_active_item(nav, _FakeMatch("tenants:member-invite"))
    assert active is not None
    assert active.key == "team"


def test_active_url_names_primary_url_name_still_matches() -> None:
    nav = (
        NavItem(
            key="team",
            label="Team",
            url_name="tenants:members",
            active_url_names=("tenants:member-invite",),
        ),
    )
    active = navigation.resolve_active_item(nav, _FakeMatch("tenants:members"))
    assert active is not None
    assert active.key == "team"


def test_active_url_names_without_url_name_never_matches() -> None:
    # Only a LINK item participates in active-route resolution: an item with no
    # url_name (a section header) never becomes active via active_url_names.
    nav = (
        NavItem(
            key="grp",
            label="Group",
            section_header=True,
            active_url_names=("tenants:members",),
        ),
    )
    assert navigation.resolve_active_item(nav, _FakeMatch("tenants:members")) is None


def test_active_url_names_deepest_match_still_wins() -> None:
    # When a child's url_name equals a parent's active_url_names entry, the
    # child (the deepest match) takes the active state, not the widened parent.
    child = NavItem(key="invite", label="Invite", url_name="tenants:member-invite")
    parent = NavItem(
        key="team",
        label="Team",
        url_name="tenants:members",
        active_url_names=("tenants:member-invite",),
        children=(child,),
    )
    active = navigation.resolve_active_item((parent,), _FakeMatch("tenants:member-invite"))
    assert active is not None
    assert active.key == "invite"


def test_navitem_positional_construction_keeps_the_0_2_4_field_order() -> None:
    # active_url_names sits at the END of the dataclass so a 0.2.4 call site
    # constructing positionally (key, label, url_name, url_kwargs, ...) still
    # lands every argument on the field it targeted.
    item = NavItem("team", "Team", "tenants:members", {"pk": 1})
    assert item.url_name == "tenants:members"
    assert item.url_kwargs == {"pk": 1}
    assert item.active_url_names == ()


# --- #273: url_kwargs disambiguates items sharing one url_name --------------


def test_resolve_active_disambiguates_by_url_kwargs() -> None:
    # A docs nav over one parameterised route (docs:page) with six pages, all
    # sharing url_name and differing only by slug: only the item whose
    # url_kwargs match the request's kwargs is active, never a fixed "last
    # sorted" item regardless of the current page (icvoss/django-brickwork#273).
    intro = NavItem(key="intro", label="Intro", url_name="docs:page", url_kwargs={"slug": "intro"})
    install = NavItem(key="install", label="Install", url_name="docs:page", url_kwargs={"slug": "install"})
    nav = (intro, install)

    # The request is for the FIRST-declared item. This is the discriminating
    # case and the only one with teeth: the pre-fix code kept the LAST match in
    # depth-first order, so it returned "install" for every request over this
    # route. A test asserting the last-declared item is active passes against
    # BOTH the fixed and the broken implementation and proves nothing.
    active = navigation.resolve_active_item(nav, _FakeMatch("docs:page", kwargs={"slug": "intro"}))

    assert active is not None
    assert active.key == "intro"


def test_resolve_active_url_kwargs_mismatch_is_not_active() -> None:
    # The sibling case, again ordered so the assertion has teeth: the
    # non-matching item is declared LAST, which is exactly the item the pre-fix
    # "keep the last match" behaviour returned. Asserting it is NOT active can
    # therefore only pass once url_kwargs are actually compared.
    intro = NavItem(key="intro", label="Intro", url_name="docs:page", url_kwargs={"slug": "intro"})
    install = NavItem(key="install", label="Install", url_name="docs:page", url_kwargs={"slug": "install"})
    nav = (intro, install)

    active = navigation.resolve_active_item(nav, _FakeMatch("docs:page", kwargs={"slug": "intro"}))

    assert active is not install
    assert active.key != "install"


def test_resolve_active_no_url_kwargs_still_matches_whole_route() -> None:
    # An item with no url_kwargs (the default {}) is a whole-route match and is
    # unaffected by the request carrying kwargs it does not declare: {} is a
    # subset of any dict. No regression for a plain, unparameterised nav item.
    nav = (NavItem(key="w", label="Widgets", url_name="testapp:widget-list"),)

    active = navigation.resolve_active_item(nav, _FakeMatch("testapp:widget-list", kwargs={"pk": 7}))

    assert active is not None
    assert active.key == "w"


def test_resolve_active_url_kwargs_is_a_subset_match_not_equality() -> None:
    # The item's url_kwargs need only be a SUBSET of the request's kwargs: the
    # request may carry extra kwargs the item does not care about. Equality
    # would break as soon as the route gained an unrelated extra kwarg.
    item = NavItem(key="doc", label="Doc", url_name="docs:page", url_kwargs={"slug": "install"})

    active = navigation.resolve_active_item(
        (item,), _FakeMatch("docs:page", kwargs={"slug": "install", "version": "3"})
    )

    assert active is not None
    assert active.key == "doc"


def test_active_url_names_still_works_when_no_item_declares_url_kwargs() -> None:
    # Regression for the existing active_url_names contract: a section item
    # widened via active_url_names, with no url_kwargs on either name, still
    # lights up on its secondary route regardless of the request's kwargs.
    nav = (
        NavItem(
            key="team",
            label="Team",
            url_name="tenants:members",
            active_url_names=("tenants:member-invite",),
        ),
    )

    active = navigation.resolve_active_item(nav, _FakeMatch("tenants:member-invite", kwargs={"tenant_id": "42"}))

    assert active is not None
    assert active.key == "team"


def test_resolve_active_ties_keep_the_last_depth_first_match() -> None:
    # Documented tie-break: two SIBLINGS whose url_name and url_kwargs both
    # match the same request resolve to whichever is declared later in the nav
    # tree (last match wins in depth-first walk order). This is a genuine
    # misconfiguration (two items claiming the same route+kwargs); the
    # behaviour is documented, not validated against at config time.
    first = NavItem(key="first", label="First", url_name="docs:page", url_kwargs={"slug": "dup"})
    second = NavItem(key="second", label="Second", url_name="docs:page", url_kwargs={"slug": "dup"})
    nav = (first, second)

    active = navigation.resolve_active_item(nav, _FakeMatch("docs:page", kwargs={"slug": "dup"}))

    assert active is not None
    assert active.key == "second"


def test_resolve_active_deepest_match_wins_over_kwargs_matching_ancestor() -> None:
    # "Deepest match wins" still holds when url_kwargs is involved: a child
    # whose url_name/url_kwargs match the request wins over its parent even
    # though the parent's own url_kwargs also match (both walked, child last).
    child = NavItem(key="child", label="Child", url_name="docs:page", url_kwargs={"slug": "install"})
    parent = NavItem(
        key="parent",
        label="Parent",
        url_name="docs:page",
        url_kwargs={"slug": "install"},
        children=(child,),
    )

    active = navigation.resolve_active_item((parent,), _FakeMatch("docs:page", kwargs={"slug": "install"}))

    assert active is not None
    assert active.key == "child"


# --- BR-BW-NAV-004/005: visibility via host callables, empty groups drop -----


def test_visible_items_filters_by_required_permission() -> None:
    nav = (
        NavItem(key="pub", label="Public", url_name="pub"),
        NavItem(key="sec", label="Secret", url_name="sec", required_permissions=("view_secret",)),
    )
    visible = navigation.visible_items(nav, _ctx(perms=()))
    assert {i.key for i in visible} == {"pub"}
    visible2 = navigation.visible_items(nav, _ctx(perms=("view_secret",)))
    assert {i.key for i in visible2} == {"pub", "sec"}


def test_visible_items_any_permission_or_semantics() -> None:
    nav = (NavItem(key="x", label="X", url_name="x", any_permissions=("a", "b")),)
    assert navigation.visible_items(nav, _ctx(perms=("b",)))
    assert not navigation.visible_items(nav, _ctx(perms=("c",)))


def test_visible_items_feature_flag() -> None:
    nav = (NavItem(key="x", label="X", url_name="x", required_features=("beta",)),)
    assert not navigation.visible_items(nav, _ctx(features=()))
    assert navigation.visible_items(nav, _ctx(features=("beta",)))


def test_visibility_policy_predicate() -> None:
    nav = (NavItem(key="x", label="X", url_name="x", visibility_policy=lambda _c: False),)
    assert not navigation.visible_items(nav, _ctx())


def test_empty_section_header_is_dropped() -> None:
    # a header whose only child is permission-hidden should itself disappear
    nav = (
        NavItem(
            key="grp",
            label="Group",
            section_header=True,
            children=(NavItem(key="hidden", label="Hidden", url_name="h", required_permissions=("nope",)),),
        ),
    )
    assert navigation.visible_items(nav, _ctx()) == ()


# --- BR-BW-NAV-003: a bad url_name never 500s -------------------------------


def test_safe_reverse_returns_none_on_bad_name() -> None:
    assert navigation.safe_reverse("this-url-does-not-exist") is None


def test_safe_reverse_does_not_raise(monkeypatch) -> None:
    def boom(*a, **k):
        raise NoReverseMatch("nope")

    monkeypatch.setattr(navigation, "reverse", boom)
    assert navigation.safe_reverse("anything") is None  # caught, not raised


# --- icvoss/django-brickwork#131: label/badge accept lazy translations -----


def test_navitem_accepts_a_lazy_translated_label() -> None:
    # The correct way to supply a nav label is gettext_lazy(...), which
    # returns a django.utils.functional.Promise, not a str. Constructing a
    # NavItem with one must not raise, and the promise must resolve to the
    # real text on demand (str()), never forced eagerly at construction time.
    from django.utils.translation import gettext_lazy as _

    lazy_label = _("Dashboard")
    item = NavItem(key="dash", label=lazy_label, url_name="dashboard")
    assert item.label is lazy_label  # stored lazily, not eagerly resolved to str
    assert str(item.label) == "Dashboard"


def test_navitem_accepts_a_lazy_translated_badge() -> None:
    from django.utils.translation import gettext_lazy as _

    lazy_badge = _("New")
    item = NavItem(key="feat", label="Feature", url_name="feat", badge=lazy_badge)
    assert item.badge is lazy_badge
    assert str(item.badge) == "New"


def test_navitem_lazy_label_renders_correctly_through_bw_nav() -> None:
    # The end-to-end proof: a lazy label survives all the way through
    # {% bw_nav %} rendering to real text in the output, exactly as a plain
    # str label does, so the widened annotation has not changed behaviour.
    # href (a raw resolved path, NAV-019) is used rather than url_name so this
    # needs no urlconf entry: only the label's resolution is under test here.
    from django.template import Context, Template
    from django.utils.translation import gettext_lazy as _

    nav = (NavItem(key="dash", label=_("Dashboard"), href="/dashboard/"),)
    html = Template("{% load brickwork_nav %}{% bw_nav items=nav %}").render(Context({"nav": nav}))
    assert "Dashboard" in html
