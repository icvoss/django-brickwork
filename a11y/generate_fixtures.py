"""Render brickwork pages to standalone HTML fixtures for the axe + no-JS suite.

Renders the testapp's real pages (list, form, form-with-errors) through the full
shell in both light and dark themes, inlines the compiled brickwork.css, and
writes self-contained HTML files under a11y/fixtures/. Playwright then loads each
file:// and runs axe-core (WCAG 2.2 AA) plus a no-JS assertion.

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


def render_list(theme: str) -> str:
    from django.urls import resolve

    rf = RequestFactory()
    request = rf.get("/widgets/")
    request.resolver_match = resolve("/widgets/")
    rows = [
        {"id": 1, "cells": ["Alpha", "Active"], "url": "/widgets/1/edit/"},
        {"id": 2, "cells": ["Beta", "Draft"], "url": "/widgets/2/edit/"},
    ]
    columns = [
        {"label": "Name", "sortable": True, "sort_key": "name", "sort_key_desc": "-name", "next_sort": "-name"},
        {"label": "Status", "sortable": True, "sort_key": "status", "sort_key_desc": "-status", "next_sort": "status"},
    ]
    ctx = _base_context(request, theme)
    ctx.update({"table_columns": columns, "table_rows": rows, "current_sort": ""})
    return _inline_css(render_to_string("brickwork_testapp/widget_list.html", ctx, request=request))


def render_form(theme: str, *, with_errors: bool) -> str:
    from brickwork_testapp.forms import WidgetForm
    from django.urls import resolve

    rf = RequestFactory()
    request = rf.get("/widgets/new/")
    request.resolver_match = resolve("/widgets/new/")
    form = WidgetForm(data={"name": "invalid", "status": "draft"}) if with_errors else WidgetForm()
    if with_errors:
        form.is_valid()  # populate errors
    ctx = _base_context(request, theme)
    ctx["form"] = form
    return _inline_css(render_to_string("brickwork_testapp/widget_form.html", ctx, request=request))


def main() -> None:
    written = []
    for theme in ("light", "dark"):
        (OUT / f"list-{theme}.html").write_text(render_list(theme))
        (OUT / f"form-{theme}.html").write_text(render_form(theme, with_errors=False))
        (OUT / f"form-errors-{theme}.html").write_text(render_form(theme, with_errors=True))
        written += [f"list-{theme}", f"form-{theme}", f"form-errors-{theme}"]
    print("fixtures written:", ", ".join(written))


if __name__ == "__main__":
    main()
