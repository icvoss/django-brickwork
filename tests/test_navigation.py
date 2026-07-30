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
    def __init__(self, view_name: str) -> None:
        self.view_name = view_name


def _ctx(*, perms=(), features=()):
    return NavContext(
        request=None,
        permission_checker=lambda p: p in perms,
        feature_checker=lambda f: f in features,
    )


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
