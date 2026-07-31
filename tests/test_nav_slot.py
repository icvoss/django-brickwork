"""The 0.5.0 nav slot (brickwork#21): AC-BW-078 / BR-BW-NAV-007.

brickwork ships the sidebar_switcher / mobile_nav_switcher seams and a styled
container positioned above the nav render, and NOTHING else: no switcher
component, no data source, no interaction behaviour. A consumer's own
<details>-based fragment (the worked example in spec 04 section 5d) renders
inside the container with no brickwork-specific configuration beyond the
block override itself.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.template import Context, Template
from django.template.loader import render_to_string

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATES = _ROOT / "src" / "brickwork" / "templates"
_FRONTEND = _ROOT / "frontend" / "src"
_DIST = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "dist"

# The worked consumer fragment from spec 04 section 5d (consentics-shaped).
_SWITCHER_FRAGMENT = (
    '<details class="bw-sidebar__switcher-trigger" id="probe-switcher">'
    "<summary>Acme Ltd</summary>"
    '<nav aria-label="Switch property">'
    '<a href="/properties/1/switch/">Acme Ltd</a>'
    "</nav>"
    "</details>"
)


def _extend(blocks: str, **ctx: object) -> str:
    return Template("{% extends 'brickwork/shell/app.html' %}" + blocks).render(Context(ctx))


# --- empty by default -------------------------------------------------------


def test_slots_render_no_switcher_markup_by_default() -> None:
    html = render_to_string("brickwork/shell/app.html", {})
    # An empty styled container is permitted (AC-BW-078); switcher CONTENT is not.
    for container_class in ("bw-sidebar__switcher", "bw-drawer__switcher"):
        for match in re.finditer(rf'<div class="{container_class}"[^>]*>(.*?)</div>', html, re.S):
            assert match.group(1).strip() == "", f"the {container_class} container ships non-empty by default"
    assert "switcher-trigger" not in html
    assert "Switch property" not in html


def test_brickwork_ships_no_switcher_component_in_any_source() -> None:
    # Static check (AC-BW-078): the only shipped mentions of "switcher" are the
    # seam itself (the two block names and the container div in shell/app.html)
    # and the container's styling in CSS. No shipped template or JS implements
    # a workspace/property/tenant switcher.
    allowed_tokens = ("sidebar_switcher", "mobile_nav_switcher", "bw-sidebar__switcher", "bw-drawer__switcher")
    offenders: list[str] = []
    sources = list(_TEMPLATES.rglob("*.html")) + list(_FRONTEND.glob("*.js")) + [_DIST / "brickwork.js"]
    for path in sources:
        # comments never render; only shipped markup/behaviour is in scope
        text = re.sub(r"\{% comment %\}.*?\{% endcomment %\}", "", path.read_text(encoding="utf-8"), flags=re.S)
        if "switcher" not in text.lower():
            continue
        if path.name != "app.html":
            offenders.append(str(path))
            continue
        residue = text
        for token in allowed_tokens:
            residue = residue.replace(token, "")
        if "switcher" in residue.lower():
            offenders.append(f"{path} (beyond the seam tokens)")
    assert not offenders, f"shipped source implements switcher behaviour: {offenders}"


# --- a filled slot renders inside the styled container, above the nav -------


def test_sidebar_switcher_renders_inside_the_container_above_the_nav() -> None:
    html = _extend("{% block sidebar_switcher %}" + _SWITCHER_FRAGMENT + "{% endblock %}")
    assert 'id="probe-switcher"' in html
    container = html.index("bw-sidebar__switcher")
    probe = html.index('id="probe-switcher"')
    nav = html.index('class="bw-sidebar__nav"')
    assert container < probe < nav, "the sidebar switcher must render inside the styled container, above the nav render"


def test_mobile_nav_switcher_renders_inside_the_drawer_above_the_mobile_nav() -> None:
    html = _extend(
        "{% block mobile_nav_switcher %}MOBILE-SWITCHER-SENTINEL{% endblock %}"
        "{% block mobile_nav %}MOBILE-NAV-SENTINEL{% endblock %}"
    )
    drawer = html.index("bw-drawer__panel")
    switcher = html.index("MOBILE-SWITCHER-SENTINEL")
    nav = html.index("MOBILE-NAV-SENTINEL")
    assert drawer < switcher < nav, "the mobile switcher must render inside the drawer panel, above the mobile nav"


def test_one_fragment_fills_both_containers() -> None:
    # NAV-016 mirroring: the same include fills both slots, one per container.
    html = _extend(
        "{% block sidebar_switcher %}SHARED-SWITCHER-SENTINEL{% endblock %}"
        "{% block mobile_nav_switcher %}SHARED-SWITCHER-SENTINEL{% endblock %}"
    )
    assert html.count("SHARED-SWITCHER-SENTINEL") == 2
