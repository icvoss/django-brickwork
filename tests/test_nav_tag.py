"""Direct unit tests for the {% bw_nav %} tag's prepare + render logic.

Covers the branch paths of RenderedNavItem preparation the integration suite only
touches through full pages: external links, section headers, badges, the bad-url
fallback (omit vs disabled), and active/ancestor state, without needing the
testapp's URLconf (external + header items need no reverse; the disabled path is
forced via the setting).
"""

from __future__ import annotations

from django.template import Context, Template
from django.test import override_settings

from brickwork.models import NavItem
from brickwork.templatetags.brickwork_nav import RenderedNavItem, _prepare, bw_nav


def _render_tree(tree) -> str:
    return Template("{% load brickwork_nav %}{% bw_nav items=items %}").render(Context({"items": tree}))


# --- _prepare branch paths ------------------------------------------------


def test_external_link_prepared_with_external_flag() -> None:
    item = NavItem(key="docs", label="Docs", external_url="https://example.com")
    prepared = _prepare(item, None, "omit")
    assert prepared.is_external is True
    assert prepared.href == "https://example.com"


def test_section_header_with_children_prepared() -> None:
    header = NavItem(
        key="grp",
        label="Group",
        section_header=True,
        children=(NavItem(key="ext", label="Ext", external_url="https://x.test"),),
    )
    prepared = _prepare(header, None, "omit")
    assert prepared.is_section_header is True
    assert len(prepared.children) == 1


def test_section_header_with_no_surviving_children_is_dropped() -> None:
    # a header whose only child has a bad url and fallback=omit loses its child,
    # so the header itself should be dropped.
    header = NavItem(
        key="grp",
        label="Group",
        section_header=True,
        children=(NavItem(key="bad", label="Bad", url_name="does-not-exist"),),
    )
    assert _prepare(header, None, "omit") is None


def test_bad_url_omit_fallback_drops_item() -> None:
    item = NavItem(key="bad", label="Bad", url_name="does-not-exist")
    assert _prepare(item, None, "omit") is None


def test_bad_url_disabled_fallback_renders_disabled() -> None:
    item = NavItem(key="bad", label="Bad", url_name="does-not-exist")
    prepared = _prepare(item, None, "disabled")
    assert prepared is not None
    assert prepared.is_disabled is True


def test_badge_is_carried_through() -> None:
    item = NavItem(key="inbox", label="Inbox", external_url="https://x.test", badge=12)
    prepared = _prepare(item, None, "omit")
    assert prepared.badge == 12


def test_active_item_is_flagged() -> None:
    active = NavItem(key="me", label="Me", external_url="https://x.test")
    prepared = _prepare(active, active, "omit")
    assert prepared.is_active is True


# --- render output --------------------------------------------------------


def test_render_external_link_has_target_blank() -> None:
    out = _render_tree((NavItem(key="d", label="Docs", external_url="https://x.test"),))
    assert 'target="_blank"' in out and 'rel="noopener noreferrer"' in out


def test_render_section_header_label() -> None:
    out = _render_tree(
        (
            NavItem(
                key="grp",
                label="Admin",
                section_header=True,
                children=(NavItem(key="e", label="E", external_url="https://x.test"),),
            ),
        )
    )
    assert "bw-nav__section-label" in out and "Admin" in out


def test_render_badge() -> None:
    out = _render_tree((NavItem(key="i", label="Inbox", external_url="https://x.test", badge=7),))
    assert "bw-nav__badge" in out and "7" in out


@override_settings(BRICKWORK_NAV_FALLBACK="disabled")
def test_render_disabled_item_via_setting() -> None:
    out = _render_tree((NavItem(key="bad", label="Bad", url_name="nope"),))
    assert "bw-nav__link--disabled" in out
    assert 'aria-disabled="true"' in out


def test_bw_nav_returns_prepared_tree_dict() -> None:
    result = bw_nav(items=(NavItem(key="e", label="E", external_url="https://x.test"),))
    assert "bw_nav_tree" in result
    assert isinstance(result["bw_nav_tree"][0], RenderedNavItem)
