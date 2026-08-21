"""Direct unit tests for the {% bw_nav %} tag's prepare + render logic.

Covers the branch paths of RenderedNavItem preparation the integration suite only
touches through full pages: external links, section headers, badges, the bad-url
fallback (omit vs disabled), and active/ancestor state, without needing the
testapp's URLconf (external + header items need no reverse; the disabled path is
forced via the setting).
"""

from __future__ import annotations

from types import SimpleNamespace

from django.template import Context, Template
from django.test import override_settings

from brickwork.models import NavItem
from brickwork.templatetags.brickwork_nav import (
    RenderedNavItem,
    _effective_kwargs,
    _prepare,
    bw_nav,
)


def _render_tree(tree) -> str:
    return Template("{% load brickwork_nav %}{% bw_nav items=items %}").render(Context({"items": tree}))


# --- _prepare branch paths ------------------------------------------------


def test_external_link_prepared_with_external_flag() -> None:
    item = NavItem(key="docs", label="Docs", external_url="https://example.com")
    prepared = _prepare(item, None, "omit", None)
    assert prepared.is_external is True
    assert prepared.href == "https://example.com"


def test_section_header_with_children_prepared() -> None:
    header = NavItem(
        key="grp",
        label="Group",
        section_header=True,
        children=(NavItem(key="ext", label="Ext", external_url="https://x.test"),),
    )
    prepared = _prepare(header, None, "omit", None)
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
    assert _prepare(header, None, "omit", None) is None


def test_bad_url_omit_fallback_drops_item() -> None:
    item = NavItem(key="bad", label="Bad", url_name="does-not-exist")
    assert _prepare(item, None, "omit", None) is None


def test_bad_url_disabled_fallback_renders_disabled() -> None:
    item = NavItem(key="bad", label="Bad", url_name="does-not-exist")
    prepared = _prepare(item, None, "disabled", None)
    assert prepared is not None
    assert prepared.is_disabled is True


def test_badge_is_carried_through() -> None:
    item = NavItem(key="inbox", label="Inbox", external_url="https://x.test", badge=12)
    prepared = _prepare(item, None, "omit", None)
    assert prepared.badge == 12


def test_active_item_is_flagged() -> None:
    active = NavItem(key="me", label="Me", external_url="https://x.test")
    prepared = _prepare(active, active, "omit", None)
    assert prepared.is_active is True


# --- kwarg_name declarative route-param copy (#19) ------------------------


def _rm(**kwargs):
    """A stand-in resolver_match carrying only the kwargs we assert on."""
    return SimpleNamespace(kwargs=kwargs)


def test_kwarg_name_same_name_copies_route_param() -> None:
    item = NavItem(key="proj", label="Project", url_name="x", kwarg_name="slug")
    assert _effective_kwargs(item, _rm(slug="acme")) == {"slug": "acme"}


def test_kwarg_name_rename_reads_source_writes_target() -> None:
    # the route names it project_slug; the item's URL expects slug
    item = NavItem(key="proj", label="Project", url_name="x", kwarg_name=("project_slug", "slug"))
    assert _effective_kwargs(item, _rm(project_slug="acme")) == {"slug": "acme"}


def test_kwarg_name_absent_source_contributes_nothing() -> None:
    # no project selected yet: the source kwarg is not on the route
    item = NavItem(key="proj", label="Project", url_name="x", kwarg_name="slug")
    assert _effective_kwargs(item, _rm()) == {}
    assert _effective_kwargs(item, None) == {}


def test_kwarg_name_merges_with_static_url_kwargs() -> None:
    item = NavItem(
        key="proj",
        label="Project",
        url_name="x",
        url_kwargs={"tab": "overview"},
        kwarg_name="slug",
    )
    assert _effective_kwargs(item, _rm(slug="acme")) == {"tab": "overview", "slug": "acme"}


def test_url_kwargs_from_request_wins_over_kwarg_name() -> None:
    # both set: the callable is applied last and overrides
    item = NavItem(
        key="proj",
        label="Project",
        url_name="x",
        kwarg_name="slug",
        url_kwargs_from_request=lambda rm: {"slug": "override"},
    )
    assert _effective_kwargs(item, _rm(slug="fromroute")) == {"slug": "override"}


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


@override_settings(BRICKWORK_NAV_FALLBACK="disabled")
def test_render_disabled_item_preserves_badge() -> None:
    out = _render_tree((NavItem(key="bad", label="Marketplace", url_name="nope", badge="Coming soon"),))
    assert "bw-nav__link--disabled" in out
    assert "bw-nav__badge" in out
    assert "Coming soon" in out


def test_bw_nav_returns_prepared_tree_dict() -> None:
    # bw_nav is takes_context=True; pass a minimal context (no request).
    result = bw_nav({}, items=(NavItem(key="e", label="E", external_url="https://x.test"),))
    assert "bw_nav_tree" in result
    assert isinstance(result["bw_nav_tree"][0], RenderedNavItem)


# --- #5: route-parameter-dependent URLs -----------------------------------


class _Match:
    def __init__(self, kwargs):
        self.kwargs = kwargs
        self.view_name = "x"


def test_effective_kwargs_merges_request_derived_over_static() -> None:
    from brickwork.templatetags.brickwork_nav import _effective_kwargs

    item = NavItem(
        key="docs",
        label="Docs",
        url_name="proj:docs",
        url_kwargs={"tab": "all"},
        url_kwargs_from_request=lambda rm: {"slug": rm.kwargs["slug"]} if rm and "slug" in rm.kwargs else {},
    )
    # with a matching route, the slug is pulled from the current request
    assert _effective_kwargs(item, _Match({"slug": "acme"})) == {"tab": "all", "slug": "acme"}
    # with no slug in the route (nothing selected yet), only the static kwargs remain
    assert _effective_kwargs(item, _Match({})) == {"tab": "all"}
    assert _effective_kwargs(item, None) == {"tab": "all"}


def test_route_param_item_reverses_with_the_current_slug(monkeypatch) -> None:
    # a project-scoped item resolves against the CURRENT route's slug at render.
    import brickwork.templatetags.brickwork_nav as navtag

    captured = {}

    def fake_reverse(url_name, kwargs=None):
        captured["kwargs"] = kwargs
        return f"/projects/{kwargs['slug']}/documents/"

    monkeypatch.setattr(navtag, "safe_reverse", lambda name, kw: fake_reverse(name, kwargs=kw))
    item = NavItem(
        key="docs",
        label="Docs",
        url_name="proj:docs",
        url_kwargs_from_request=lambda rm: {"slug": rm.kwargs["slug"]},
    )
    prepared = navtag._prepare(item, None, "omit", _Match({"slug": "acme"}))
    assert prepared.href == "/projects/acme/documents/"
    assert captured["kwargs"] == {"slug": "acme"}


def test_route_param_item_omitted_when_kwargs_unavailable() -> None:
    # no project selected -> the reverse fails -> the item follows NAV_FALLBACK.
    item = NavItem(
        key="docs",
        label="Docs",
        url_name="does-not-exist",
        url_kwargs_from_request=lambda rm: {"slug": rm.kwargs["slug"]} if rm and "slug" in rm.kwargs else {},
    )
    # omit (default): a route-param item with no slug and an unresolvable name drops out
    from brickwork.templatetags.brickwork_nav import _prepare

    assert _prepare(item, None, "omit", _Match({})) is None
