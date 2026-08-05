"""NAV-019 (raw internal href) + NAV-020 (opens_in_new_tab decoupled from external).

These add two independent axes to NavItem:
- href: a raw, already-resolved internal path (for CMS menus that only expose
  page.get_absolute_url() paths, never route names), rendered same-tab with no
  external affordance and active-by-path.
- opens_in_new_tab: a tri-state new-tab flag independent of external-ness, so an
  internal link can open a new tab and an external link can stay in the same one.
"""

import pytest
from django.template import Context, Template
from django.test import RequestFactory

from brickwork.exceptions import NavConfigError
from brickwork.models import NavItem
from brickwork.services.navigation import validate_nav_config


def _render(items, *, path="/"):
    request = RequestFactory().get(path)
    return Template("{% load brickwork_nav %}{% bw_nav items=items %}").render(
        Context({"items": items, "request": request})
    )


# --- href: raw internal path ------------------------------------------------


def test_href_renders_as_plain_internal_anchor():
    out = _render((NavItem(key="d", label="Docs", href="/docs/getting-started/"),))
    assert 'href="/docs/getting-started/"' in out
    # No external affordance: no target=_blank, no external-link icon.
    assert 'target="_blank"' not in out
    assert "bw-nav__external" not in out


def test_href_item_is_active_when_it_matches_request_path():
    out = _render(
        (NavItem(key="d", label="Docs", href="/docs/getting-started/"),),
        path="/docs/getting-started/",
    )
    assert "bw-nav__link--active" in out
    assert 'aria-current="page"' in out


def test_href_item_is_not_active_on_a_different_path():
    out = _render(
        (NavItem(key="d", label="Docs", href="/docs/getting-started/"),),
        path="/pricing/",
    )
    assert "bw-nav__link--active" not in out


# --- opens_in_new_tab: independent axis, backwards compatible ---------------


def test_external_link_defaults_to_new_tab_backwards_compatible():
    # opens_in_new_tab=None (default) -> external keeps its historical new-tab.
    out = _render((NavItem(key="x", label="X", external_url="https://x.test"),))
    assert 'target="_blank"' in out
    assert 'rel="noopener noreferrer"' in out


def test_external_link_can_be_forced_same_tab():
    out = _render((NavItem(key="x", label="X", external_url="https://x.test", opens_in_new_tab=False),))
    assert 'target="_blank"' not in out
    # Still shows the external-link icon: it IS an off-site link, just same-tab.
    assert "bw-nav__external" in out


def test_internal_href_can_be_forced_new_tab():
    out = _render((NavItem(key="d", label="Docs", href="/docs/", opens_in_new_tab=True),))
    assert 'target="_blank"' in out
    assert 'rel="noopener noreferrer"' in out
    # Internal: no external icon even in a new tab.
    assert "bw-nav__external" not in out


# --- config validation: one URL source only ---------------------------------


def test_config_rejects_href_plus_url_name():
    with pytest.raises(NavConfigError):
        validate_nav_config([NavItem(key="a", label="A", url_name="x", href="/y/")])


def test_config_rejects_href_plus_external_url():
    with pytest.raises(NavConfigError):
        validate_nav_config([NavItem(key="a", label="A", external_url="https://x.test", href="/y/")])


def test_config_allows_a_single_source():
    validate_nav_config([NavItem(key="a", label="A", href="/y/")])
    validate_nav_config([NavItem(key="b", label="B", external_url="https://x.test")])
    validate_nav_config([NavItem(key="c", label="C", url_name="x")])
