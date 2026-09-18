"""Direct unit tests for the {% bw_nav %} tag's prepare + render logic.

Covers the branch paths of RenderedNavItem preparation the integration suite only
touches through full pages: external links, section headers, badges, the bad-url
fallback (omit vs disabled), and active/ancestor state, without needing the
testapp's URLconf (external + header items need no reverse; the disabled path is
forced via the setting).
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
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


def test_orientation_horizontal_marks_the_root_list() -> None:
    items = (NavItem(key="home", label="Home", external_url="https://example.com/"),)
    html = Template("{% load brickwork_nav %}{% bw_nav items=items orientation='horizontal' %}").render(
        Context({"items": items})
    )
    assert 'class="bw-nav__list bw-nav__list--horizontal"' in html


def test_orientation_default_and_invalid_stay_vertical() -> None:
    items = (NavItem(key="home", label="Home", external_url="https://example.com/"),)
    default_html = _render_tree(items)
    assert "bw-nav__list--horizontal" not in default_html
    invalid_html = Template("{% load brickwork_nav %}{% bw_nav items=items orientation='diagonal' %}").render(
        Context({"items": items})
    )
    assert "bw-nav__list--horizontal" not in invalid_html
    assert 'class="bw-nav__list"' in invalid_html


# --- label ellipsis width constraint (icvoss/django-brickwork#623) -------------

_ROOT = Path(__file__).resolve().parent.parent
_NAV_CSS = _ROOT / "frontend" / "src" / "nav.css"
_DIST_CSS = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist" / "brickwork.css"


def _css_rules(css: str) -> list[tuple[str, str]]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(sel.strip(), body) for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


def _rule_body(rules: list[tuple[str, str]], selector: str) -> str:
    matches = [body for sel, body in rules if sel.strip() == selector]
    assert matches, f"missing {selector} rule"
    return matches[0]


def test_vertical_nav_link_constrains_width_so_label_ellipsis_can_fire() -> None:
    # .bw-nav__label already declares text-overflow: ellipsis; without a width
    # constraint on the flex link the label never overflows its own box and the
    # ellipsis stays inert (docs rail long titles, #623).
    rules = _css_rules(_NAV_CSS.read_text(encoding="utf-8"))
    body = _rule_body(rules, ".bw-nav__link")
    compact = body.replace(" ", "").replace("\n", "")
    assert "inline-size:100%" in compact
    assert "min-inline-size:0" in compact

    label = _rule_body(rules, ".bw-nav__label")
    label_compact = label.replace(" ", "").replace("\n", "")
    assert "text-overflow:ellipsis" in label_compact
    assert "overflow:hidden" in label_compact
    assert "white-space:nowrap" in label_compact


def test_horizontal_nav_link_resets_to_content_sized_inline_size() -> None:
    # Vertical gets inline-size: 100%; a wrapping topbar / orientation=horizontal
    # band must stay content-sized chips, not stretch each link across the row.
    rules = _css_rules(_NAV_CSS.read_text(encoding="utf-8"))
    bodies = [
        body for sel, body in rules if "bw-nav__list--horizontal" in sel and ".bw-nav__link" in sel and "topbar" in sel
    ]
    assert bodies, "expected the shared topbar/horizontal .bw-nav__link rule"
    compact = bodies[0].replace(" ", "").replace("\n", "")
    assert "inline-size:auto" in compact


def test_dist_css_ships_nav_ellipsis_width_constraint() -> None:
    # Consumers load dist/brickwork.css; a source-only fix is invisible until
    # npm run build. Assert the compiled bundle carries both halves.
    compact = _DIST_CSS.read_text(encoding="utf-8").replace(" ", "")
    assert ".bw-nav__link{" in compact
    # Minified: properties may sit anywhere in the rule; require the pair that
    # unlocks ellipsis, and the horizontal reset so header nav is not stretched.
    link_match = re.search(r"\.bw-nav__link\{([^}]*)\}", compact)
    assert link_match is not None
    link_body = link_match.group(1)
    assert "inline-size:100%" in link_body
    assert "min-inline-size:0" in link_body

    assert "text-overflow:ellipsis" in compact
    # Horizontal reset lands in a multi-selector rule that includes the list modifier.
    assert re.search(
        r"\.bw-nav__list--horizontal\s*\.bw-nav__link\{[^}]*inline-size:auto",
        compact,
    )


# --- labels wrap option (icvoss/django-brickwork#671) --------------------------


def test_labels_wrap_marks_the_root_list() -> None:
    items = (NavItem(key="home", label="Home", external_url="https://example.com/"),)
    html = Template("{% load brickwork_nav %}{% bw_nav items=items labels='wrap' %}").render(Context({"items": items}))
    assert 'class="bw-nav__list bw-nav__list--labels-wrap"' in html


def test_labels_default_stays_truncate_without_modifier() -> None:
    items = (NavItem(key="home", label="Home", external_url="https://example.com/"),)
    html = _render_tree(items)
    assert "bw-nav__list--labels-wrap" not in html
    assert 'class="bw-nav__list"' in html


def test_labels_invalid_raises() -> None:
    from django.template import TemplateSyntaxError

    items = (NavItem(key="home", label="Home", external_url="https://example.com/"),)
    with pytest.raises(TemplateSyntaxError, match="bw_nav labels must be one of"):
        Template("{% load brickwork_nav %}{% bw_nav items=items labels='clip' %}").render(Context({"items": items}))


def test_labels_wrap_clears_ellipsis_on_nav_label() -> None:
    rules = _css_rules(_NAV_CSS.read_text(encoding="utf-8"))
    body = _rule_body(rules, ".bw-nav__list--labels-wrap .bw-nav__label")
    compact = body.replace(" ", "").replace("\n", "")
    assert "white-space:normal" in compact
    assert "overflow:visible" in compact
    assert "text-overflow:unset" in compact

    dist = _DIST_CSS.read_text(encoding="utf-8").replace(" ", "")
    assert ".bw-nav__list--labels-wrap.bw-nav__label{" in dist or ".bw-nav__list--labels-wrap .bw-nav__label{" in dist
    wrap_match = re.search(r"\.bw-nav__list--labels-wrap\s*\.bw-nav__label\{([^}]*)\}", dist)
    assert wrap_match is not None
    wrap_body = wrap_match.group(1)
    assert "white-space:normal" in wrap_body
    assert "overflow:visible" in wrap_body
