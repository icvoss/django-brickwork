"""Render brickwork pages to standalone HTML fixtures for the axe + no-JS suite.

Renders the testapp's real pages (list, dashboard, form, form-with-errors)
through the full shell, with list and dashboard routed through the shipped
0.5.0 page patterns, in both light and dark themes, inlines the compiled
brickwork.css, and writes self-contained HTML files under a11y/fixtures/.
Playwright then loads each file:// and runs axe-core (WCAG 2.2 AA) plus a
no-JS assertion.

Rendering the REAL pages (not a hand-written sample) means the a11y gate tests
exactly what a consumer ships, and it catches a contrast regression from a bad
token or a missing aria wiring on any shipped component.

Run: DJANGO_SETTINGS_MODULE=tests.settings_seams PYTHONPATH=src:tests \
     python a11y/generate_fixtures.py
"""

from __future__ import annotations

import re
from pathlib import Path

import django

django.setup()

from django.template.loader import render_to_string  # noqa: E402
from django.test import RequestFactory  # noqa: E402

from brickwork.models import NavContext  # noqa: E402
from brickwork.services.navigation import resolve_active_item, visible_items  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "src/brickwork/static/brickwork/dist/brickwork.css").read_text()
OUT = Path(__file__).resolve().parent / "fixtures"
OUT.mkdir(exist_ok=True)

_STATIC_LINK = re.compile(r'<link rel="stylesheet" href="[^"]*brickwork\.css">')


def _inline_css(html: str) -> str:
    """Replace the {% static %} stylesheet link with the compiled CSS inline, so
    the fixture is self-contained for a file:// load."""
    return _STATIC_LINK.sub(f"<style>{CSS}</style>", html)


def _nav_context(request):
    from brickwork_testapp.nav import MAIN_NAV

    ctx = NavContext(request=request, permission_checker=lambda _p: True, feature_checker=lambda _f: True)
    items = visible_items(MAIN_NAV, ctx)
    active = resolve_active_item(items, request.resolver_match)
    return items, active


def _base_context(request, theme: str):
    items, active = _nav_context(request)
    return {
        "request": request,
        "bw_nav_items": items,
        "bw_active_nav_item": active,
        "bw_theme": theme,
        "bw_density": "comfortable",
        "bw_dir": "ltr",
    }


def render_list(theme: str, *, menu_open: bool = False) -> str:
    from brickwork_testapp.forms import WidgetFilterForm
    from django.urls import resolve

    rf = RequestFactory()
    request = rf.get("/widgets/")
    request.resolver_match = resolve("/widgets/")
    rows = [
        # row 1 is selected so the axe gate covers the selected-row treatment
        # (bw-data-table__row--selected) in both themes
        {"id": 1, "cells": ["Alpha", "Active"], "url": "/widgets/1/edit/", "selected": True},
        {"id": 2, "cells": ["Beta", "Draft"], "url": "/widgets/2/edit/"},
    ]
    columns = [
        {"label": "Name", "sortable": True, "sort_key": "name", "sort_key_desc": "-name", "next_sort": "-name"},
        {"label": "Status", "sortable": True, "sort_key": "status", "sort_key_desc": "-status", "next_sort": "status"},
    ]
    # the definition-variant facts table on the list page (matches the view's
    # summary_facts shape)
    summary_facts = [
        {"label": "Total widgets", "value": "2"},
        {"label": "Active", "value": "1"},
        {"label": "Draft", "value": "1"},
    ]
    ctx = _base_context(request, theme)
    ctx.update(
        {
            # route through patterns/list.html, exactly as the view does, so
            # the axe gate examines the fully-composed pattern page
            # (AC-BW-077): populated filter bar, table card, badges, titled
            # alert, definition table, selected row. columns/rows/table_id/
            # empty_* feed the pattern's own default table card.
            "base_parent": "brickwork/patterns/list.html",
            "title": "Widgets",
            "description": "Everything in the harness.",
            "filter_form": WidgetFilterForm(),
            "table_id": "widgets-table",
            "columns": columns,
            "rows": rows,
            "current_sort": "",
            "empty_heading": "No widgets yet",
            "empty_body": "Create your first widget to get started.",
            "summary_facts": summary_facts,
        }
    )
    if menu_open:
        # render the account-menu disclosure initially open so axe examines the
        # open panel (colour contrast, landmark labelling) in this theme
        ctx["account_menu_open"] = True
    return _inline_css(render_to_string("brickwork_testapp/widget_list.html", ctx, request=request))


def render_dashboard(theme: str) -> str:
    from django.urls import resolve

    rf = RequestFactory()
    request = rf.get("/dashboard/")
    request.resolver_match = resolve("/dashboard/")
    ctx = _base_context(request, theme)
    ctx.update(
        {
            # route through patterns/dashboard.html, exactly as the view does:
            # three stat tiles (up + down deltas so the glyph + accessible-text
            # pairing is examined in both themes, BR-BW-TPL-007), the content
            # card, and the recent-activity table card (AC-BW-077).
            "base_parent": "brickwork/patterns/dashboard.html",
            "title": "Dashboard",
            "description": "The workspace at a glance.",
            "stats": {"total": 2, "active": 1, "draft": 1},
            # the pattern's dashboard_activity default reads these from context
            "table_id": "activity-table",
            "columns": [
                {"label": "Name", "sortable": False},
                {"label": "Status", "sortable": False},
            ],
            "rows": [
                {"id": 1, "cells": ["Alpha", "Active"], "url": "/widgets/1/edit/"},
                {"id": 2, "cells": ["Beta", "Draft"], "url": "/widgets/2/edit/"},
            ],
            "empty_heading": "No activity yet",
            "empty_body": "Create a widget to see it appear here.",
        }
    )
    return _inline_css(render_to_string("brickwork_testapp/dashboard.html", ctx, request=request))


def render_form(theme: str, *, with_errors: bool) -> str:
    from brickwork_testapp.forms import WidgetForm
    from django.urls import resolve

    rf = RequestFactory()
    request = rf.get("/widgets/new/")
    request.resolver_match = resolve("/widgets/new/")
    # name="invalid" + status="archived" triggers BOTH a field error (inline,
    # aria-describedby wired) and the non-field form-errors block, so the axe
    # gate sees both error surfaces in both themes.
    form = WidgetForm(data={"name": "invalid", "status": "archived"}) if with_errors else WidgetForm()
    if with_errors:
        form.is_valid()  # populate errors
    ctx = _base_context(request, theme)
    ctx["form"] = form
    return _inline_css(render_to_string("brickwork_testapp/widget_form.html", ctx, request=request))


def main() -> None:
    written = []
    for theme in ("light", "dark"):
        (OUT / f"list-{theme}.html").write_text(render_list(theme))
        (OUT / f"list-menu-open-{theme}.html").write_text(render_list(theme, menu_open=True))
        (OUT / f"dashboard-{theme}.html").write_text(render_dashboard(theme))
        (OUT / f"form-{theme}.html").write_text(render_form(theme, with_errors=False))
        (OUT / f"form-errors-{theme}.html").write_text(render_form(theme, with_errors=True))
        written += [
            f"list-{theme}",
            f"list-menu-open-{theme}",
            f"dashboard-{theme}",
            f"form-{theme}",
            f"form-errors-{theme}",
        ]
    print("fixtures written:", ", ".join(written))


if __name__ == "__main__":
    main()
