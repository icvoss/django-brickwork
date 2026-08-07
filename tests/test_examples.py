"""The copy-paste example pages (2.0.0, ADR-056).

Two things are under test, and they pull in opposite directions on purpose:

1. **The loader CANNOT resolve an example.** This is the structural mechanism
   that makes "you cannot extend a brickwork page" true rather than merely
   requested. If a refactor ever moved the examples under an app ``templates/``
   directory, ADR-056's core decision would silently revert, and these tests
   are what catches that.

2. **Every example still renders.** The examples compose real components, so a
   component change can break one. Rendering each on every CI run turns that
   from "a consumer discovers it after copying" into a failing build. Because
   of (1) this needs a standalone Engine pointed at the examples directory,
   which is also exactly how the gallery renders them.
"""

from __future__ import annotations

import re

import pytest
from django import forms
from django.template import Context, Engine, TemplateDoesNotExist
from django.template.backends.django import get_installed_libraries as get_default_libraries
from django.template.loader import get_template

from brickwork import examples

# Every example, with the context its own header comment says the view must
# supply. The examples deliberately carry their copy inline (that is the whole
# point of ADR-056), so this is only the list-shaped data a Django template
# cannot build for itself.
_NAV_CONTEXT: dict[str, object] = {"nav_items": (), "nav_active": None}


class _ExampleForm(forms.Form):
    """Stands in for the consumer's own form.

    The examples deliberately name no field (brickwork ships no auth or model
    form, so a hard-coded field name would break whichever backend does not
    use it). Any form renders through {% bw_form %}, so a plain two-field form
    is a faithful stand-in for all of them.
    """

    name = forms.CharField(label="Name")
    email = forms.EmailField(label="Email address")


_TABLE_COLUMNS = [
    {"label": "Number", "sortable": True, "sort_key": "number"},
    {"label": "Account", "sortable": False},
    {"label": "Amount", "sortable": True, "sort_key": "amount"},
]
_TABLE_ROWS = [
    {"id": 1, "cells": ["INV-2417", "Acme Corp", "£1,240.00"]},
    {"id": 2, "cells": ["INV-2418", "Halden Group", "£880.00"]},
]

_EXAMPLE_CONTEXTS: dict[str, dict[str, object]] = {
    "base.html": {},
    "app/list.html": {
        **_NAV_CONTEXT,
        "filter_form": (),
        "invoice_columns": _TABLE_COLUMNS,
        "invoice_rows": _TABLE_ROWS,
        "current_sort": "number",
        "invoices": None,
    },
    "app/detail.html": {
        **_NAV_CONTEXT,
        "breadcrumb_items": [
            {"label": "Invoices", "url": "/invoices/"},
            {"label": "INV-2417"},
        ],
        "invoice_facts": [
            {"label": "Account", "value": "Acme Corp"},
            {"label": "Raised", "value": "14 July 2026"},
        ],
        "line_columns": _TABLE_COLUMNS,
        "line_rows": _TABLE_ROWS,
    },
    "app/dashboard.html": {
        **_NAV_CONTEXT,
        "activity_columns": _TABLE_COLUMNS,
        "activity_rows": _TABLE_ROWS,
    },
    "app/form.html": {**_NAV_CONTEXT, "form": _ExampleForm()},
    "app/wizard.html": {
        **_NAV_CONTEXT,
        "form": _ExampleForm(),
        "steps": [
            {"label": "Company", "status": "complete"},
            {"label": "Team", "status": "current"},
            {"label": "Billing", "status": "upcoming"},
        ],
    },
    "app/settings.html": {
        **_NAV_CONTEXT,
        "form": _ExampleForm(),
        "settings_tabs": [
            {"key": "organisation", "label": "Organisation"},
            {"key": "billing", "label": "Billing"},
        ],
        "active_tab": "organisation",
    },
    "app/console.html": _NAV_CONTEXT,
    "app/confirm.html": {},
    "auth/signin.html": {"form": _ExampleForm()},
    "auth/signup.html": {"form": _ExampleForm()},
    "auth/reset.html": {"form": _ExampleForm()},
    "marketing/landing.html": {
        "logos": [{"src": "/static/logo-acme.svg", "alt": "Acme Corp"}],
        "features": [
            {"icon": "bell", "heading": "Automatic reminders", "body": "Chases send themselves."},
            {"icon": "check", "heading": "Reconciliation", "body": "Payments match themselves off."},
        ],
        "stats": [{"value": "21 days", "label": "Average time to pay"}],
    },
    "marketing/pricing.html": {
        "solo_features": ["Unlimited invoices", "Automatic reminders"],
        "team_features": ["Everything in Solo", "Up to 10 users"],
        "scale_features": ["Everything in Team", "Multi-currency"],
        "faq_items": [{"question": "Can I cancel?", "answer": "Any time, from the billing page."}],
    },
    "marketing/about.html": {
        "stats": [{"value": "11", "label": "People"}, {"value": "4", "label": "Countries"}],
    },
}


def _example_engine() -> Engine:
    """A standalone engine that CAN see the examples.

    This is the only supported way to render an example, and the gallery uses
    the same shape. It deliberately does not touch the project's configured
    engines: pointing those at the examples directory would rebuild the
    extendable-page contract ADR-056 retires.

    ``app_dirs=True`` so the examples can resolve the brickwork components and
    shells they compose, exactly as they will in the project that copies them.

    The library set comes from ``get_default_libraries()``, the same discovery
    the configured DjangoTemplates backend runs. A bare ``Engine()`` does NOT
    inherit it, so ``{% load static %}`` and ``{% load i18n %}`` would fail;
    passing an explicit ``libraries`` dict instead REPLACES the set rather than
    extending it, with the same result. This is the one non-obvious line in
    rendering off-loader templates, and the gallery needs it too.
    """
    return Engine(
        dirs=[str(examples.examples_root())],
        app_dirs=True,
        libraries=get_default_libraries(),
    )


# --- 1. The loader cannot resolve an example --------------------------------


@pytest.mark.parametrize("name", sorted(_EXAMPLE_CONTEXTS))
def test_the_template_loader_cannot_resolve_an_example(name: str) -> None:
    """ADR-056 section 3: examples are package data, never on the loader path.

    A consumer must not be able to {% extends %} an example even by accident,
    which is what makes "pages are yours" structural rather than a request.
    """
    with pytest.raises(TemplateDoesNotExist):
        get_template(f"brickwork/examples/{name}")


@pytest.mark.parametrize("name", sorted(_EXAMPLE_CONTEXTS))
def test_no_example_is_reachable_under_any_plausible_prefix(name: str) -> None:
    # The bare name and the marketing namespace are the two other spellings a
    # consumer might reasonably try after seeing the file in the wheel.
    for candidate in (name, f"examples/{name}", f"brickwork_marketing/examples/{name}"):
        with pytest.raises(TemplateDoesNotExist):
            get_template(candidate)


def test_examples_do_not_live_under_any_app_templates_directory() -> None:
    """The mechanism itself, asserted directly rather than through its effect.

    APP_DIRS walks <app>/templates/. An examples tree that ended up inside one
    would be loadable no matter what the tests above happened to probe for.
    """
    root = examples.examples_root()
    assert root.name == "examples"
    assert "templates" not in root.parts[len(root.parts) - 3 :]


# --- 2. Every example renders, so drift against components fails CI ---------


@pytest.mark.parametrize("name", sorted(_EXAMPLE_CONTEXTS))
def test_every_example_renders_a_complete_document(name: str) -> None:
    template = _example_engine().get_template(name)
    html = template.render(Context(_EXAMPLE_CONTEXTS[name]))

    assert html.lstrip().lower().startswith("<!doctype html>")
    assert "<html" in html and "</html>" in html
    # The skip link's target: every example is a real, navigable page.
    assert 'id="bw-main"' in html


@pytest.mark.parametrize("name", sorted(_EXAMPLE_CONTEXTS))
def test_no_example_leaks_an_unresolved_template_variable(name: str) -> None:
    """An example is copy-paste source, so a stray {{ placeholder }} that never
    resolves would be shipped into a consumer's project verbatim."""
    template = _example_engine().get_template(name)
    html = template.render(Context(_EXAMPLE_CONTEXTS[name]))
    assert "{{" not in html
    assert "{%" not in html


def test_the_shipped_example_set_matches_what_the_tests_cover() -> None:
    """A new example with no context entry would otherwise be silently untested."""
    assert set(examples.list_examples()) == set(_EXAMPLE_CONTEXTS)


# --- CTA hrefs actually reach the rendered anchors (ADR-060 spelling hunt) ---

# _hero.html and _cta.html accept the flat kwargs as *_href (#98); the
# marketing examples once passed the pre-#98 *_url spelling, which the
# templates never read, so the CTA buttons silently rendered with no href.
# This pins that every documented CTA link in the shipped examples is real.
_EXAMPLE_CTA_HREFS: dict[str, list[str]] = {
    "marketing/landing.html": ["/accounts/signup/", "/demo/", "/contact/"],
    "marketing/pricing.html": ["/accounts/signup/"],
    "marketing/about.html": ["/accounts/signup/", "/docs/"],
}


@pytest.mark.parametrize("name,hrefs", sorted(_EXAMPLE_CTA_HREFS.items()))
def test_example_marketing_cta_hrefs_reach_the_rendered_button(name: str, hrefs: list[str]) -> None:
    template = _example_engine().get_template(name)
    html = template.render(Context(_EXAMPLE_CONTEXTS[name]))
    for href in hrefs:
        assert f'href="{href}"' in html, f"{name} lost its CTA href={href!r} (flat kwarg must be *_href, not *_url)"


# --- The base example carries every load-bearing line -----------------------

# examples/base.html is a STANDALONE document a consumer copies, so it cannot
# extend shell/base.html: copying a one-line extends would gain them nothing.
# That independence means it can drift. This is the drift check: each element
# below is load-bearing infrastructure the shell provides, and the base example
# must carry it or a consumer who copies the example silently loses it.
_LOAD_BEARING = {
    "the stylesheet link": r"brickwork/dist/brickwork\.css",
    "the skip link": r'class="bw-skip-link"\s+href="#bw-main"',
    "the skip link target": r'id="bw-main"',
    "the main element is focusable": r'id="bw-main"[^>]*tabindex="-1"',
    "the toast swap root": r"_toast_region\.html",
    "the modal swap root": r'id="bw-modal-root"',
    "the slide-over swap root": r'id="bw-slide-over-root"',
    "the theme axis": r"data-theme=",
    "the density axis": r"data-density=",
    "the direction axis": r"\bdir=",
    "the language attribute": r"\blang=",
    "the brand hook": r"data-bw-brand=",
    "the viewport meta": r'name="viewport"',
}


@pytest.mark.parametrize("description,pattern", sorted(_LOAD_BEARING.items()))
def test_the_base_example_carries_every_load_bearing_line(description: str, pattern: str) -> None:
    source = examples.read_example("base.html")
    assert re.search(pattern, source), f"examples/base.html has lost {description}"


def test_the_base_example_does_not_extend_a_shipped_shell() -> None:
    """It is a standalone document on purpose: a consumer copies it to OWN the
    skeleton. An extends line here would make the copy pointless."""
    assert "{% extends" not in examples.read_example("base.html")


def test_the_base_example_annotates_its_load_bearing_lines() -> None:
    # The annotation IS the deliverable for this file (ADR-056 section 4), so
    # an unannotated base example has failed at its job even if it renders.
    source = examples.read_example("base.html")
    assert source.count("LOAD-BEARING") >= 5


# --- The accessor module ----------------------------------------------------


def test_list_examples_returns_posix_relative_names() -> None:
    names = examples.list_examples()
    assert "base.html" in names
    assert "marketing/landing.html" in names
    assert all(not name.startswith("/") for name in names)
    assert names == sorted(names)


def test_read_example_returns_the_source_text() -> None:
    assert "{% extends" in examples.read_example("marketing/landing.html")


def test_read_example_rejects_an_unknown_name() -> None:
    with pytest.raises(examples.ExampleNotFoundError):
        examples.read_example("app/nope.html")


def test_read_example_rejects_path_traversal() -> None:
    # A gallery passing a user-supplied name must not be able to read the
    # package's own source, let alone outside it.
    with pytest.raises(examples.ExampleNotFoundError):
        examples.read_example("../templates/brickwork/shell/base.html")


def test_example_not_found_is_not_a_key_error() -> None:
    # Same reason IconNotFoundError stopped subclassing KeyError (#74): a
    # KeyError inside a template variable resolution is swallowed and
    # re-surfaces as silently empty output.
    assert not issubclass(examples.ExampleNotFoundError, KeyError)
