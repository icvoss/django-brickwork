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
from pathlib import Path

import pytest
from django import forms
from django.template import Context, Engine, TemplateDoesNotExist
from django.template.backends.django import get_installed_libraries as get_default_libraries
from django.template.loader import get_template
from django.utils import dates as django_dates
from django.utils.formats import get_format
from django.utils.html import escape as django_escape
from django.utils.safestring import mark_safe

from brickwork import examples
from tests._class_contract import unstyled_classes

# The COMPILED stylesheet, not the frontend source: the source is the build's
# input, and it is the built artefact that reaches a consumer's page. A rule
# present in frontend/src but absent here (a build not re-run before commit) is
# exactly the drift these tests exist to catch.
_COMPILED_CSS = (
    Path(__file__).resolve().parent.parent / "src" / "brickwork" / "static" / "brickwork" / "dist" / "brickwork.css"
).read_text(encoding="utf-8")

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

# app/date-range-picker.html's own header comment documents this exact
# computation as what a consumer's view supplies: django.utils.dates'
# lazily-translated calendar names, resolved against the active language,
# never a hand-written English list.
_DRP_CONTEXT: dict[str, object] = {
    "bw_drp_weekday_labels": [str(django_dates.WEEKDAYS_ABBR[i]) for i in range(7)],
    "bw_drp_month_labels": [str(django_dates.MONTHS[i]) for i in range(1, 13)],
    "bw_drp_first_day": get_format("FIRST_DAY_OF_WEEK"),
}

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
    "app/date-range-picker.html": {**_NAV_CONTEXT, **_DRP_CONTEXT},
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
    "ops/queue.html": {
        **_NAV_CONTEXT,
        "filter_form": (),
        "queue_tabs": [
            {"key": "mine", "label": "Waiting on you", "badge": 18},
            {"key": "blocked", "label": "Blocked", "badge": 4},
        ],
        "queue_active": "mine",
        "queue_columns": _TABLE_COLUMNS,
        "queue_rows": _TABLE_ROWS,
        "queue_page": None,
    },
    "ops/audit-trail.html": {
        **_NAV_CONTEXT,
        "filter_form": (),
        "audit_columns": _TABLE_COLUMNS,
        "audit_rows": _TABLE_ROWS,
        "audit_page": None,
        # Pre-rendered markup, exactly as _disclosure.html's content
        # parameter documents: the caller marks it safe at the call site.
        "entry_detail": mark_safe("<p>Plan changed from Team to Scale by Priya Raman.</p>"),
        "top_actors": [
            {"label": "Priya Raman", "amount": 412, "value": "412 actions"},
            {"label": "Tom Ashworth", "amount": 198, "value": "198 actions"},
        ],
    },
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

# --- The example SECTIONS (3.1.0, plan Phase 6a) ----------------------------
#
# A section is a fragment, not a document: it is the band a consumer copies
# into a page they already own. So sections are held to a different contract
# from the whole-page examples above (no doctype, no <html>, no #bw-main), and
# are listed separately rather than folded into _EXAMPLE_CONTEXTS.
#
# Only _feature_grid.html needs context, for the same reason the landing page
# does: a Django template cannot build a list of dicts inline. Every other
# section carries its copy inline and renders from an empty context, which is
# the property that makes it genuinely copy-paste.
_SECTION_FEATURES = [
    {
        "icon": "bell",
        "heading": "Automatic reminders",
        "body": "Chase on your schedule, not when you remember.",
        "url": "/features/reminders/",
    },
    {
        "icon": "calendar",
        "heading": "Late-payment prediction",
        "body": "Know which accounts slip before they do.",
    },
    {
        "icon": "check",
        "heading": "Reconciliation",
        "body": "Payments matched to invoices automatically.",
    },
]

# The listing entry contract (3.2.0, plan Phase 6a wave 2). One list serves all
# three listing variants, which is the whole finding those variants produced:
# what they share is the ENTRY SHAPE, not a grid, so no grid component was
# promoted out of them. A fourth variant that cannot render from this list is
# evidence the contract is wrong, not a reason to add a second list here.
_SECTION_ENTRIES = [
    {
        "title": "Chasing without the awkwardness",
        "summary": "How to write a reminder that gets paid without costing you the relationship.",
        "url": "/blog/chasing-without-the-awkwardness/",
        "meta": "14 July 2026",
        "tag": "Guides",
        "image": "/static/blog/chasing.jpg",
        "image_alt": "A printed invoice on a desk beside a phone",
        "category": "Chasing",
        "updated": "14 July 2026",
    },
    {
        "title": "What thirty days actually means",
        "summary": "Payment terms are a negotiation, not a setting. Here is how to pick yours.",
        "url": "/blog/what-thirty-days-means/",
        "meta": "2 July 2026",
        "tag": "Cashflow",
        "image": "/static/blog/terms.jpg",
        "image_alt": "A calendar with a payment date circled",
        "category": "Terms",
        "updated": "2 July 2026",
    },
    {
        "title": "Reconciliation, and why it is nobody's favourite",
        "summary": "Matching payments to invoices by hand is the tax you pay for getting paid.",
        "url": "/blog/reconciliation/",
        "meta": "20 June 2026",
        "tag": "Operations",
        "image": "/static/blog/reconciliation.jpg",
        "image_alt": "A bank statement beside a stack of invoices",
        "category": "Accounting",
        "updated": "20 June 2026",
    },
]

# The pricing tiers, in the shape sections/pricing/three-tier.html documents.
# Note the key is cta_url even though the kwarg _pricing_table.html forwards is
# cta_href: that asymmetry is deliberate (consumer data vs an emitted
# attribute), documented in the plan, and pinned by the CTA-href test below.
_SECTION_TIERS = [
    {
        "name": "Solo",
        "price": "£9",
        "period": "/month",
        "description": "For one person invoicing a handful of clients.",
        "features": ["Unlimited invoices", "Automatic reminders"],
        "cta_label": "Start free trial",
        "cta_url": "/accounts/signup/?plan=solo",
    },
    {
        "name": "Team",
        "price": "£29",
        "period": "/month",
        "description": "For a finance function of two to ten.",
        "features": ["Everything in Solo", "Up to 10 users"],
        "cta_label": "Start free trial",
        "cta_url": "/accounts/signup/?plan=team",
        "highlighted": True,
        "badge": "Most popular",
    },
    {
        "name": "Scale",
        "price": "£89",
        "period": "/month",
        "description": "Multi-entity, multi-currency, audit trails.",
        "features": ["Everything in Team", "Multi-currency"],
        "cta_label": "Talk to sales",
        "cta_url": "/contact/",
    },
]

# Every trend carries a trend_label: a trend without one is a template-authoring
# defect _stat.html enforces at its own render (VIZ-002 / BR-BW-TPL-007), and the
# third stat omits both because not every number has a delta worth showing.
_SECTION_STATS = [
    {
        "value": "21 days",
        "label": "Average time to pay",
        "trend": "down",
        "trend_label": "17 days faster than before",
    },
    {
        "value": "£1.4m",
        "label": "Chased and collected this quarter",
        "trend": "up",
        "trend_label": "up 12% on last quarter",
    },
    {"value": "94%", "label": "Invoices paid without a phone call"},
]

_SECTION_CONTEXTS: dict[str, dict[str, object]] = {
    "sections/content/callout.html": {},
    "sections/content/media-and-text.html": {},
    "sections/content/prose-block.html": {},
    "sections/cta/centred-band.html": {},
    "sections/cta/full-bleed.html": {},
    "sections/cta/split.html": {},
    "sections/features/alternating-rows.html": {},
    "sections/features/icon-grid.html": {"features": _SECTION_FEATURES},
    "sections/features/simple-list.html": {},
    "sections/hero/centred.html": {},
    "sections/hero/media-behind.html": {},
    "sections/hero/minimal.html": {},
    "sections/hero/split-media.html": {},
    "sections/listing/card-grid.html": {"entries": _SECTION_ENTRIES},
    "sections/listing/compact-table.html": {"entries": _SECTION_ENTRIES},
    "sections/listing/media-list.html": {"entries": _SECTION_ENTRIES},
    "sections/faq/single-column.html": {},
    "sections/faq/two-column.html": {},
    "sections/pricing/comparison-table.html": {},
    "sections/pricing/single-plan.html": {},
    "sections/pricing/three-tier.html": {"tiers": _SECTION_TIERS},
    "sections/stats/card-row.html": {},
    "sections/stats/inline-band.html": {"stats": _SECTION_STATS},
    "sections/testimonial/logo-and-quote.html": {},
    "sections/testimonial/quote-grid.html": {},
    "sections/testimonial/single-quote.html": {},
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
    assert set(examples.list_examples()) == set(_EXAMPLE_CONTEXTS) | set(_SECTION_CONTEXTS)


def test_every_page_example_is_listed_in_the_examples_readme() -> None:
    """A new example with no README row is silently unfindable.

    icvoss/django-brickwork#199: ``app/date-range-picker.html`` shipped
    without ever being added to ``src/brickwork/examples/README.md``'s file
    table, so a consumer had no way to discover it short of reading the
    examples directory itself, and filed icvoss/django-brickwork#172 asking
    for the component it deliberately replaces. Sections are excluded: they
    are listed in their own table, under a different heading, in the same
    file.
    """
    on_disk = {name for name in examples.list_examples() if not name.startswith("sections/")}

    readme_text = (Path(__file__).resolve().parent.parent / "src" / "brickwork" / "examples" / "README.md").read_text(
        encoding="utf-8"
    )
    listed = set(re.findall(r"^\|\s*`([\w./-]+\.html)`\s*\|", readme_text, flags=re.MULTILINE))

    missing = on_disk - listed
    assert not missing, (
        f"{sorted(missing)} shipped in src/brickwork/examples/ but not listed in "
        "src/brickwork/examples/README.md's file table (icvoss/django-brickwork#199)"
    )


@pytest.mark.parametrize(
    ("name", "media_placement", "obsolete_class"),
    [
        ("sections/hero/media-behind.html", "behind", "bw-hero-behind"),
        ("sections/hero/split-media.html", "beside", "bw-hero-split"),
    ],
)
def test_hero_examples_use_the_shipped_media_placement_contract(
    name: str, media_placement: str, obsolete_class: str
) -> None:
    source = examples.read_example(name)
    assert "brickwork_marketing/components/_hero.html" in source
    assert f'media_placement="{media_placement}"' in source
    assert obsolete_class not in source


# --- 3. The example sections (3.1.0, plan Phase 6a) -------------------------


@pytest.mark.parametrize("name", sorted(_SECTION_CONTEXTS))
def test_every_section_renders(name: str) -> None:
    html = _example_engine().get_template(name).render(Context(_SECTION_CONTEXTS[name]))
    assert html.strip(), f"{name} rendered empty"


@pytest.mark.parametrize("name", sorted(_SECTION_CONTEXTS))
def test_a_section_is_a_fragment_not_a_document(name: str) -> None:
    """The contract that separates a section from a whole-page example.

    A section is dropped INTO a page the consumer already owns, so emitting a
    doctype or an <html> element would produce a nested document the moment it
    was used as intended.
    """
    html = _example_engine().get_template(name).render(Context(_SECTION_CONTEXTS[name]))
    lowered = html.lower()
    assert "<!doctype" not in lowered
    assert "<html" not in lowered
    assert "<body" not in lowered


@pytest.mark.parametrize("name", sorted(_SECTION_CONTEXTS))
def test_no_section_leaks_an_unresolved_template_variable(name: str) -> None:
    html = _example_engine().get_template(name).render(Context(_SECTION_CONTEXTS[name]))
    assert "{{" not in html
    assert "{%" not in html


@pytest.mark.parametrize("name", sorted(_SECTION_CONTEXTS))
def test_the_loader_cannot_resolve_a_section_either(name: str) -> None:
    """ADR-056 applies to sections exactly as it does to pages."""
    with pytest.raises(TemplateDoesNotExist):
        get_template(f"brickwork/examples/{name}")


@pytest.mark.parametrize("name", sorted(_SECTION_CONTEXTS))
def test_every_section_class_it_emits_is_actually_styled(name: str) -> None:
    """The icvoss/django-brickwork#120 defect class, applied to sections.

    A section whose markup names a class the shipped stylesheet does not define
    renders unstyled in the consumer's project while passing every "does it
    render" test. Catching that needs the compiled CSS, not the source, because
    the source is what the build consumes rather than what ships.

    Structural hooks with no styling of their own are exempt by name: block
    roots whose children carry every rule. They are listed explicitly so a
    genuinely dead class cannot hide among them.
    """
    unstyled_by_design = {
        # Block roots positioned entirely by their own children's rules.
        "bw-btn__label",
        "bw-feature-grid-section",
        "bw-feature-list-section",
        "bw-content-section",
        # Shared by all three listing variants, which have no layout in common:
        # every rule lives on __intro/__heading/__lede and the per-variant roots.
        "bw-listing-section",
        # Wave 2 (3.2.0). Each is a section root whose children carry every
        # rule, verified individually: none has a bare rule and all have styled
        # descendants. bw-pricing-table-section is the shipped component's own
        # root, in the same position as bw-feature-grid-section above.
        "bw-pricing-table-section",
        "bw-pricing-comparison",
        "bw-single-plan",
        "bw-faq-columns",
        "bw-testimonial-grid-section",
        "bw-stat-cards-section",
    }
    html = _example_engine().get_template(name).render(Context(_SECTION_CONTEXTS[name]))
    missing = unstyled_classes(html, allowlist=unstyled_by_design)
    assert not missing, f"{name} emits classes with no rule in the shipped CSS: {missing}"


def test_the_prose_floor_styles_the_elements_long_form_content_actually_uses() -> None:
    """Plan Phase 6 gate 2: blog and docs pages are mostly unclassed markup.

    Before 3.1.0 the package shipped no element-level rule at all, so a rendered
    Markdown body fell back to UA defaults inside an otherwise themed page. Each
    element below appears in a real shipped section, so a regression here is a
    visible defect on a page a consumer copied.
    """
    for selector in (
        "blockquote",
        "code",
        "pre",
        "table",
        "th",
        "caption",
        "figcaption",
        "hr",
    ):
        assert f".bw-prose :where({selector}" in _COMPILED_CSS or f", {selector}" in _COMPILED_CSS, (
            f"the prose floor does not style <{selector}>"
        )


def test_the_prose_floor_lands_at_zero_specificity() -> None:
    """Every descendant rule is wrapped in :where() so a consumer's own class on
    any child wins without !important. That is what makes it a floor rather than
    a style to fight."""
    assert ".bw-prose :where(" in _COMPILED_CSS
    # The block itself must never resort to !important to hold its ground.
    prose_block = _COMPILED_CSS[_COMPILED_CSS.index(".bw-prose") :]
    prose_block = (
        prose_block[: prose_block.index("/* --- Dark-theme resets")]
        if "/* --- Dark-theme resets" in prose_block
        else prose_block[:6000]
    )
    assert "!important" not in prose_block


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


# --- A fixture value must actually survive into the render (#232) -----------
#
# icvoss/django-brickwork#232: app/detail.html passed items=breadcrumb_items
# into _breadcrumbs.html, whose required key is crumbs, so the breadcrumb
# region rendered empty. Every OTHER test above only checks structural
# completeness (a doctype, no leaked "{{", a styled class): none of them ever
# looks at whether a SPECIFIC fixture value made it into the HTML, so an
# include-kwarg mismatch like #232's renders a complete, validly structured,
# silently WRONG page and nothing here would have failed.
#
# The fix is a literal-text contract, not a per-example hand-list (which is
# exactly the kind of assertion that goes stale the day someone adds a new
# example and forgets to add its check alongside it). _EXAMPLE_CONTEXTS and
# _SECTION_CONTEXTS already carry the fixture data; the DESIGN here is to walk
# each fixture dict and, for a fixed set of key names that every consuming
# component renders VERBATIM as visible text (see _LITERAL_TEXT_KEYS below),
# assert the string on that key reaches the rendered HTML. That is derived
# from the context data itself, so a new example needs no new assertion here:
# it is covered the moment its fixture uses one of these key names, exactly
# the shape that would have caught #232 (breadcrumb_items' "label" values).
#
# This intentionally does NOT try to assert on every string in a fixture.
# Several keys are real but non-literal: an enum consumed as a class suffix or
# an aria state (status, variant, trend), an icon registry name (icon) that
# renders as an SVG reference rather than text, or a sort/lookup key
# (sort_key, key, id). Asserting those "appear" would either be trivially true
# (icon names collide with real copy) or actively wrong (status values like
# "current" never appear as visible text at all), so they are left out on
# purpose rather than swept in via a blanket string walk.
_LITERAL_TEXT_KEYS = frozenset(
    {
        "label",
        "heading",
        "lede",
        "body",
        "title",
        "description",
        "message",
        "question",
        "answer",
        "author",
        "role",
        "quote",
        "name",
        "value",
        "summary",
        "meta",
        "tag",
        "eyebrow",
        "action_label",
        "cta_label",
        "primary_cta_label",
        "secondary_cta_label",
        "trend_label",
        "badge",
    }
)

# Fixture values that are real literal-text keys by name but do not survive
# byte-for-byte, or that the consuming template legitimately never renders.
# Each entry names the example and the exact fixture values that are exempt,
# with the reason, so a new mismatch cannot hide behind a growing allowlist
# without a citation.
#
# sections/listing/*.html share ONE fixture, `_SECTION_ENTRIES` (deliberately:
# test_examples.py's own module comment above documents that the three
# listing variants share the ENTRY CONTRACT, not a grid), but each variant's
# own "WHAT YOUR VIEW MUST SUPPLY" header comment names a narrower subset of
# that shape than the fixture as a whole carries. compact-table.html renders
# only title/category/updated (no tag, no summary, by its own header
# comment); media-list.html renders title/summary/meta/image/image_alt (no
# tag). Their "missing" tag/summary values are that documented, deliberate
# narrowing, not a dropped include kwarg, so they are exempted here rather
# than in a wider `_LITERAL_TEXT_KEYS` change that would reintroduce false
# negatives on tags/summaries that genuinely do need to render elsewhere.
_LITERAL_TEXT_EXEMPTIONS: dict[str, set[str]] = {
    "sections/listing/compact-table.html": {entry["tag"] for entry in _SECTION_ENTRIES}
    | {entry["summary"] for entry in _SECTION_ENTRIES},
    "sections/listing/media-list.html": {entry["tag"] for entry in _SECTION_ENTRIES},
}


def _iter_literal_text_values(value: object, *, under_literal_key: bool) -> list[str]:
    """Every string this fixture tree carries under a `_LITERAL_TEXT_KEYS` key.

    Recurses through dicts and lists/tuples so a nested shape (breadcrumbs'
    list of {label, url} dicts, a table's list of {label, value} rows, a
    pricing tier's list of feature strings) is covered without each example
    hand-listing its own nested keys. A bare string is only collected when it
    is reached while ``under_literal_key`` is True, i.e. it sits directly on,
    or inside a list directly on, one of `_LITERAL_TEXT_KEYS`.
    """
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(_iter_literal_text_values(child, under_literal_key=key in _LITERAL_TEXT_KEYS))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_iter_literal_text_values(item, under_literal_key=under_literal_key))
    elif isinstance(value, str) and under_literal_key and len(value.strip()) >= 4:
        # A short or blank string (e.g. a one-word status-like label) is too
        # likely to appear in the rendered HTML by coincidence (whitespace,
        # markup fragments) to be useful signal either way.
        found.append(value)
    return found


def _expected_literal_strings(context: dict[str, object]) -> set[str]:
    found: set[str] = set()
    for value in context.values():
        found.update(_iter_literal_text_values(value, under_literal_key=False))
    return found


def _missing_literal_strings(expected: set[str], html: str) -> list[str]:
    """Which of ``expected`` never reached ``html``.

    Django autoescapes ``{{ value }}`` by default, so a value carrying an
    apostrophe or ampersand (several examples' fixture copy does) reaches the
    HTML as its escaped form, not byte-for-byte. A value counts as present if
    either the raw or the HTML-escaped spelling appears, which is the correct
    reading of "survived the render" for ordinary (non `|safe`) template
    variables.
    """
    return sorted(value for value in expected if value not in html and django_escape(value) not in html)


@pytest.mark.parametrize("name", sorted(_EXAMPLE_CONTEXTS))
def test_every_fixture_literal_survives_into_the_example_render(name: str) -> None:
    """Derived regression coverage for #232's defect class.

    For every string the fixture carries under a key a component is documented
    to render verbatim (see `_LITERAL_TEXT_KEYS`), assert it actually reaches
    the rendered HTML. An include-kwarg mismatch (the component binds a
    different name than the example passes) means the value is dropped
    silently, exactly as `crumbs`/`items` was: the page still renders a
    complete, validly structured document, and only a check like this one
    notices the content never arrived.

    KNOWN LIMITATION: this searches the WHOLE rendered page, not the specific
    region the fixture value is meant to reach, so a value duplicated
    elsewhere on the page can mask a dropped kwarg for that one value. In
    `app/detail.html`, `"INV-2417"` is both a breadcrumb fixture value AND
    appears independently in the page title, page header and button hrefs
    (`{% block page_title %}Invoice INV-2417 - Northwind{% endblock %}` and
    similar); a regression that dropped ONLY the breadcrumb's `"INV-2417"`
    crumb would still pass this test, because the string is present anyway
    from those other, unrelated places. The #232 defect itself is still
    caught here because the breadcrumb fixture's OTHER label, `"Invoices"`,
    is distinctive: it appears nowhere else on the page, so its absence is
    real signal. Scoping each assertion to the component's own rendered
    region (rather than the full page) would close this gap; not done here
    because no shipped fixture today has a genuine collision on its only
    distinctive value, so the current whole-page check is the simpler check
    that still catches every real case in the shipped tree.
    """
    context = _EXAMPLE_CONTEXTS[name]
    expected = _expected_literal_strings(context) - _LITERAL_TEXT_EXEMPTIONS.get(name, set())
    if not expected:
        pytest.skip(f"{name}'s fixture carries no literal-text values to check")

    template = _example_engine().get_template(name)
    html = template.render(Context(context))

    missing = _missing_literal_strings(expected, html)
    assert not missing, (
        f"{name} rendered without these fixture values reaching the HTML "
        f"(an include-kwarg mismatch silently drops the value, #232): {missing}"
    )


@pytest.mark.parametrize("name", sorted(_SECTION_CONTEXTS))
def test_every_fixture_literal_survives_into_the_section_render(name: str) -> None:
    """The section-fixture counterpart of the example check above.

    Only sections whose context genuinely carries list-shaped data
    (`_SECTION_FEATURES`, `_SECTION_ENTRIES`, `_SECTION_TIERS`, `_SECTION_STATS`)
    have anything to check; the rest render from an empty context and are
    skipped rather than asserting on nothing.

    Carries the same whole-page-search limitation as the example-level check
    above (see that docstring's `"INV-2417"` example): a fixture value
    duplicated elsewhere on the same rendered page can mask a dropped kwarg
    for that one value specifically.
    """
    context = _SECTION_CONTEXTS[name]
    expected = _expected_literal_strings(context) - _LITERAL_TEXT_EXEMPTIONS.get(name, set())
    if not expected:
        pytest.skip(f"{name}'s fixture carries no literal-text values to check")

    html = _example_engine().get_template(name).render(Context(context))

    missing = _missing_literal_strings(expected, html)
    assert not missing, (
        f"{name} rendered without these fixture values reaching the HTML "
        f"(an include-kwarg mismatch silently drops the value, #232): {missing}"
    )
