"""Unit tests for the {% bw_nav_header %} and {% bw_nav_rail %} renderers.

Two additional renderers over the SAME prepared NavItem tree bw_nav consumes
(brickwork#102 the horizontal marketing-header row, brickwork#82 the compact
two-tier rail). Both share bw_nav's prepare pipeline (URL resolution, the
BRICKWORK_NAV_FALLBACK handling, active/ancestor state, the NAV-019 href
seam), so these tests cover the render contracts that differ per renderer:
the flat-by-design flattening rules, the per-renderer class vocabulary, and
aria-current placement. bw_nav's own output stays byte-compatible; the guard
test at the bottom pins that no new class vocabulary leaks into it.
"""

from __future__ import annotations

from django.template import Context, Template
from django.test import RequestFactory, override_settings

from brickwork.models import NavItem


def _render(tag: str, items, *, path: str | None = None, active: NavItem | None = None) -> str:
    source = "{% load brickwork_nav %}{% " + tag + " items=items active=active %}"
    ctx = {"items": items, "active": active}
    if path is not None:
        ctx["request"] = RequestFactory().get(path)
    return Template(source).render(Context(ctx))


# --- {% bw_nav_header %}: the marketing-header row (#102) ------------------


def test_header_renders_its_own_class_vocabulary() -> None:
    out = _render("bw_nav_header", (NavItem(key="d", label="Docs", href="/docs/"),))
    assert "bw-nav-header__list" in out
    assert "bw-nav-header__link" in out
    # never the sidebar renderer's classes: the two skins are independent
    assert "bw-nav__list" not in out
    assert "bw-nav__link" not in out


def test_header_emits_a_list_not_a_nav_landmark() -> None:
    # callers place the tag inside a labelled <nav> (the marketing shell's
    # marketing_nav block already is one), so the renderer must not nest one.
    out = _render("bw_nav_header", (NavItem(key="d", label="Docs", href="/docs/"),))
    assert "<nav" not in out
    assert '<ul class="bw-nav-header__list" role="list">' in out


def test_header_href_item_active_by_path_with_aria_current() -> None:
    # the NAV-019 href seam (CMS menus) keeps active state in the header row
    out = _render(
        "bw_nav_header",
        (NavItem(key="d", label="Docs", href="/docs/"),),
        path="/docs/",
    )
    assert "bw-nav-header__link--active" in out
    assert 'aria-current="page"' in out


def test_header_href_item_inactive_on_other_path() -> None:
    out = _render(
        "bw_nav_header",
        (NavItem(key="d", label="Docs", href="/docs/"),),
        path="/pricing/",
    )
    assert "bw-nav-header__link--active" not in out
    assert 'aria-current="page"' not in out


def test_header_ancestor_gets_treatment_without_aria_current() -> None:
    child = NavItem(key="detail", label="Detail", href="/projects/detail/")
    parent = NavItem(key="projects", label="Projects", href="/projects/", children=(child,))
    out = _render("bw_nav_header", (parent,), active=child)
    assert "bw-nav-header__link--active-ancestor" in out
    # aria-current marks the exact page only; the ancestor is visual treatment
    assert 'aria-current="page"' not in out


def test_header_does_not_render_children_of_link_items() -> None:
    # flat by design: a link item's subtree belongs elsewhere (a drawer, the
    # page body); the header shows the parent with ancestor state only.
    child = NavItem(key="archived", label="Archived widgets", href="/projects/archived/")
    parent = NavItem(key="projects", label="Projects", href="/projects/", children=(child,))
    out = _render("bw_nav_header", (parent,))
    assert "Projects" in out
    assert "Archived widgets" not in out


def test_header_flattens_section_headers_to_top_level_items() -> None:
    header = NavItem(
        key="grp",
        label="Admin",
        section_header=True,
        children=(
            NavItem(key="settings", label="Settings", href="/settings/"),
            NavItem(key="billing", label="Billing", href="/billing/"),
        ),
    )
    out = _render("bw_nav_header", (header,))
    # the children join the row; the group label has no place in a one-line
    # header and is not rendered
    assert "Settings" in out
    assert "Billing" in out
    assert "Admin" not in out
    assert "bw-nav__section-label" not in out


def test_header_external_link_keeps_new_tab_and_affordance() -> None:
    out = _render("bw_nav_header", (NavItem(key="x", label="Docs", external_url="https://x.test"),))
    assert 'target="_blank"' in out
    assert 'rel="noopener noreferrer"' in out
    assert "bw-nav-header__external" in out


def test_header_badge_renders_as_chip() -> None:
    out = _render("bw_nav_header", (NavItem(key="i", label="Inbox", href="/inbox/", badge=7),))
    assert "bw-nav-header__badge" in out
    assert "7" in out


@override_settings(BRICKWORK_NAV_FALLBACK="disabled")
def test_header_disabled_fallback_renders_aria_disabled_span() -> None:
    out = _render("bw_nav_header", (NavItem(key="bad", label="Bad", url_name="does-not-exist"),))
    assert "bw-nav-header__link--disabled" in out
    assert 'aria-disabled="true"' in out


def test_header_bad_url_omitted_under_default_fallback() -> None:
    out = _render("bw_nav_header", (NavItem(key="bad", label="Bad", url_name="does-not-exist"),))
    assert "Bad" not in out


# --- {% bw_nav_rail %}: the compact two-tier rail (#82) --------------------


def test_rail_renders_icon_and_visible_label() -> None:
    out = _render("bw_nav_rail", (NavItem(key="h", label="Home", href="/", icon="home"),))
    assert "bw-nav-rail__list" in out
    assert "bw-nav-rail__icon" in out
    assert "bw-nav-rail__label" in out
    assert "Home" in out
    # the label is a designed visible caption, never clipped out of view
    assert "bw-visually-hidden" not in out


def test_rail_emits_a_list_not_a_nav_landmark() -> None:
    out = _render("bw_nav_rail", (NavItem(key="h", label="Home", href="/"),))
    assert "<nav" not in out
    assert '<ul class="bw-nav-rail__list" role="list">' in out


def test_rail_entry_is_a_real_link() -> None:
    # a rail entry navigates; it is never a JS-only trigger (BR-BW-HTMX-001)
    out = _render("bw_nav_rail", (NavItem(key="h", label="Home", href="/home/"),))
    assert '<a class="bw-nav-rail__link' in out
    assert 'href="/home/"' in out


def test_rail_href_item_active_by_path_with_aria_current() -> None:
    out = _render(
        "bw_nav_rail",
        (NavItem(key="h", label="Home", href="/home/"),),
        path="/home/",
    )
    assert "bw-nav-rail__link--active" in out
    assert 'aria-current="page"' in out


def test_rail_ancestor_area_gets_treatment_without_aria_current() -> None:
    # the rail highlights its AREA: a descendant route lights the rail entry,
    # while the exact aria-current lives in the contextual tier's render
    child = NavItem(key="detail", label="Detail", href="/projects/detail/")
    parent = NavItem(key="projects", label="Projects", href="/projects/", children=(child,))
    out = _render("bw_nav_rail", (parent,), active=child)
    assert "bw-nav-rail__link--active-ancestor" in out
    assert 'aria-current="page"' not in out


def test_rail_does_not_render_children_of_link_items() -> None:
    # children belong to the paired contextual {% bw_nav %}, never the rail
    child = NavItem(key="archived", label="Archived widgets", href="/projects/archived/")
    parent = NavItem(key="projects", label="Projects", href="/projects/", children=(child,))
    out = _render("bw_nav_rail", (parent,))
    assert "Projects" in out
    assert "Archived widgets" not in out


def test_rail_flattens_section_headers_to_rail_entries() -> None:
    header = NavItem(
        key="grp",
        label="Admin",
        section_header=True,
        children=(NavItem(key="settings", label="Settings", href="/settings/"),),
    )
    out = _render("bw_nav_rail", (header,))
    assert "Settings" in out
    # the collapsed-rail precedent (SHL-004): the group label is not rendered
    assert "Admin" not in out


def test_rail_badge_renders_as_corner_chip() -> None:
    out = _render("bw_nav_rail", (NavItem(key="i", label="Inbox", href="/inbox/", badge=12),))
    assert "bw-nav-rail__badge" in out
    assert "12" in out


def test_rail_external_link_keeps_new_tab_and_affordance() -> None:
    out = _render("bw_nav_rail", (NavItem(key="x", label="Docs", external_url="https://x.test"),))
    assert 'target="_blank"' in out
    assert 'rel="noopener noreferrer"' in out
    assert "bw-nav-rail__external" in out


@override_settings(BRICKWORK_NAV_FALLBACK="disabled")
def test_rail_disabled_fallback_renders_aria_disabled_span() -> None:
    out = _render("bw_nav_rail", (NavItem(key="bad", label="Bad", url_name="does-not-exist"),))
    assert "bw-nav-rail__link--disabled" in out
    assert 'aria-disabled="true"' in out


def test_rail_bad_url_omitted_under_default_fallback() -> None:
    out = _render("bw_nav_rail", (NavItem(key="bad", label="Bad", url_name="does-not-exist"),))
    assert "Bad" not in out


# --- byte-compat guard: bw_nav is untouched by the new renderers -----------


def test_bw_nav_output_carries_no_new_renderer_vocabulary() -> None:
    # the sibling renderers are additive: the existing renderer's DOM keeps
    # its exact class vocabulary for existing callers (and their CSS)
    items = (
        NavItem(key="d", label="Docs", href="/docs/"),
        NavItem(
            key="grp",
            label="Admin",
            section_header=True,
            children=(NavItem(key="s", label="Settings", href="/settings/"),),
        ),
    )
    out = _render("bw_nav", items)
    assert "bw-nav__list" in out
    assert "bw-nav__link" in out
    assert "bw-nav__section-label" in out
    assert "bw-nav-header" not in out
    assert "bw-nav-rail" not in out
