# Adoption quickstart

A short "start here" for a Django developer bringing brickwork into an app.
Pick the row that matches where you are today:

| You have | Start at |
|---|---|
| An empty directory | [Path A](#path-a-from-an-empty-directory): one command emits a running project |
| An existing Django project | [Path B](#path-b-an-existing-project-one-complete-page): one complete page, every seam in one place |
| An existing UI to migrate, cluster by cluster | [docs/ADOPTION.md](ADOPTION.md) |

This page is deliberately thin: it gets you to a running, branded page, and
[docs/INTEGRATION.md](INTEGRATION.md) holds the wiring depth once you are past
it.

## Path A: from an empty directory

You need Python 3.12 or later and nothing else. You do **not** need a Django
project first: `startsite` is the project scaffold, so do not run
`django-admin startproject` before it.

```
mkdir mysite && cd mysite
python -m venv .venv && source .venv/bin/activate    # or: uv venv && source .venv/bin/activate
pip install django-brickwork                         # or: uv pip install django-brickwork
python -m brickwork startsite .
python manage.py runserver
```

1. **Install.** `pip install django-brickwork` brings Django 6 with it, its
   only hard dependency. `python -m brickwork` is the entry point that needs no
   project, because there is not one yet; it runs the one command it exposes,
   `startsite`.
2. **Emit.** `python -m brickwork startsite .` writes a complete project into
   the current directory: `manage.py`, settings with `brickwork` wired in, the
   theme context processor, URLs, a validated nav config, a brand token file,
   a `requirements.txt` that pins the brickwork that wrote it, and the pages
   of the starter you chose. A `.venv`, `venv` or `.git` entry does not count
   as "not empty"; anything else does, and the command refuses before it
   writes a file. Pass a path instead of `.` to emit into a new subdirectory.
3. **Run.** `python manage.py runserver`, then open
   <http://127.0.0.1:8000/>. The emitted `README.md` lists the pages.

### Choose a starter

`--starter` selects what is emitted. There are two, and the default is
`public-site`.

| Starter | You get | Database | After emitting |
|---|---|---|---|
| `public-site` (default) | A marketing landing page at `/` and a docs home at `/docs/`, each with the view that feeds it. Installs `brickwork.marketing` for the landing shell. | None | `python manage.py runserver` |
| `data-app` | An invoices dashboard at `/` whose figures are aggregates over real rows, and a filterable, sortable, paginated list at `/invoices/`. One model, its migration, and a `seed_demo` command. | SQLite | `python manage.py migrate`, `python manage.py seed_demo`, `python manage.py runserver` |

```
python -m brickwork startsite --starter data-app .
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Pick `public-site` when the content lives in templates (a brochure, a docs
site, a landing page) and `data-app` when the screens read from your own
models. The `data-app` views are the worked answer to "what does a view that
feeds a brickwork page look like when the data is real": they turn rows into
the plain lists and dicts a component asks for, because brickwork never reads
your models. Without `seed_demo` its screens render honest empty states.

### What you own

**The emitted project is yours outright from the moment it is written.**
There is no update command and nothing here reaches back into it later
(ADR-095): it is the same one-time copy the example pages already are
(ADR-056), automated. Edit anything in it, starting with `static/brand.css`
(placeholder brand tokens with a contrast-verified
`--bw-color-fg-on-accent`). Open the pages, then adapt their content and
composition to your product. The emitted pages are starting examples, not
visual acceptance of the site you build. `requirements.txt` carries the one
pin, `django-brickwork==<version>`; you own it from there.

Already inside a Django project? `python manage.py startsite ../scratch` (with
`brickwork` in `INSTALLED_APPS`) emits a separate starter project beside yours
and never touches yours: use it as a reference to read and copy from, or follow
Path B to wire brickwork into the project you have.

## Path B: an existing project, one complete page

This is one complete integration in one place: a URL, a view, a template, the
context that template needs, and the static file that brands it, on a fresh
`django-admin startproject mysite .` and `python manage.py startapp reports`.
Every seam named in [INTEGRATION.md](INTEGRATION.md) appears once below; read
that guide for the reasoning behind each. The first block is a set of
additions to the bottom of your settings; the rest are whole files.

**`mysite/settings.py`** (add to the bottom)

```python
# brickwork is a plain Django app. The theme context processor wires the
# theme, density and direction onto <html>; without it the shell renders
# unstyled with no error (system check brickwork.W001 names the trap).
INSTALLED_APPS += ["brickwork", "reports"]
TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "brickwork.context_processors.theme",
]

# Your own static directory, where the brand stylesheet below lives.
STATICFILES_DIRS = [BASE_DIR / "static"]
```

**`mysite/urls.py`**

```python
from django.urls import path

from reports import views

urlpatterns = [
    path("reports/", views.index, name="reports"),
]
```

**`reports/views.py`**

```python
from django.shortcuts import render
from django.urls import resolve

from brickwork.models import NavItem
from brickwork.services.navigation import resolve_active_item, validate_nav_config

# The nav is declared once and validated at import, so a bad tree fails at
# startup rather than at first render.
NAV = (NavItem(key="reports", label="Reports", url_name="reports", icon="document"),)
validate_nav_config(NAV)


def index(request):
    # brickwork renders what you hand it; it never reads your models. The
    # table wants columns and rows as plain dicts, each row with a stable id
    # and its cells already formatted.
    columns = [
        {"label": "Report", "sortable": False},
        {"label": "Owner", "sortable": False},
        {"label": "Updated", "sortable": False},
    ]
    rows = [
        {"id": "r1", "cells": ["Quarterly summary", "Finance", "2 hours ago"]},
        {"id": "r2", "cells": ["Churn review", "Customer success", "Yesterday"]},
    ]
    return render(
        request,
        "reports/index.html",
        {
            "nav_items": NAV,
            "nav_active": resolve_active_item(NAV, resolve(request.path)),
            "report_columns": columns,
            "report_rows": rows,
        },
    )
```

**`reports/templates/reports/index.html`**

```html
{% extends "brickwork/shell/app.html" %}
{% load static brickwork_components brickwork_nav %}

{% block page_title %}Reports{% endblock %}

{# Your brand stylesheet MUST load after brickwork's, or your overrides lose the cascade. #}
{% block head_extra %}
  {{ block.super }}
  <link rel="stylesheet" href="{% static 'brand.css' %}">
{% endblock %}

{# The same nav in the desktop sidebar and in the mobile drawer. #}
{% block sidebar %}{% bw_nav nav_items nav_active %}{% endblock %}
{% block sidebar_mobile %}{% bw_nav nav_items nav_active %}{% endblock %}
{% block brand_wordmark %}Acme{% endblock %}

{% block page_header %}
  {% include "brickwork/components/_page_header.html" with title="Reports" description="Everything your team has published." %}
{% endblock %}

{% block content %}
  {% include "brickwork/components/_data_table.html" with table_id="reports-table" columns=report_columns rows=report_rows empty_heading="No reports yet" empty_body="Published reports will appear here." %}
{% endblock %}
```

**`static/brand.css`**

```css
/* Recolour: override the --bw-* tokens you want to change, nothing else. */
:root {
  --bw-color-accent: oklch(0.55 0.20 265);
  --bw-color-fg-on-accent: oklch(0.99 0 0);
}
[data-theme="dark"] {
  --bw-color-accent: oklch(0.68 0.17 265);
  --bw-color-fg-on-accent: oklch(0.16 0.02 270);
}
```

Run `python manage.py runserver` and open <http://127.0.0.1:8000/reports/>.
`runserver` serves the static files through Django's staticfiles app while
`DEBUG` is on; for production set `STATIC_ROOT` and run `collectstatic`, which
collects brickwork's compiled `brickwork/dist/brickwork.css` alongside your own
files (the shell links it for you). The two accent values differ between themes
on purpose: the safe `--bw-color-fg-on-accent` flips with the accent's
lightness, so author it for each theme and verify it at 4.5:1
([BRANDING.md](BRANDING.md#the-fg-on-accent-trap-do-not-assume-white-brickwork35)).

A public marketing page follows the same shape with two changes: add
`"brickwork.marketing"` to `INSTALLED_APPS` and extend
`brickwork_marketing/shell/marketing.html` (see [Install](#install) for why it
is a separate app). The shell's interactive pieces (the mobile drawer, menus,
toasts) register against your own Alpine 3 instance; see
[Prerequisites](#prerequisites). The page itself renders without it.

## One sitting: install to a branded page

Once a first page runs, by either path above, the rest of a first sitting is
recolouring it.

1. **Pin.** Record the exact version you tested (`pip freeze | grep -i
   brickwork`, giving `django-brickwork==<version>` in your requirements).
   Path A's `requirements.txt` already carries it; you own the pin.
2. **More pages.** Copy a Free page from the
   [brickworkui.com templates](https://brickworkui.com/templates/) (the
   homepage or the full landing page), or copy one from
   `src/brickwork/examples/` (see [Example pages](../README.md#example-pages)).
   A copied page is yours outright. The `head_extra` link in the Path B
   template is how any page loads your stylesheet.
3. **L1 recolour.** Paste about 16 colour overrides (eight tokens, light and
   dark, including `--bw-color-fg-on-accent`) in your own stylesheet,
   linked after brickwork's CSS via `head_extra`. Start from
   [northline/tokens.css](examples/brand-pack/northline/tokens.css) and edit
   the values; the rules and the contrast trap are in
   [BRANDING.md](BRANDING.md).
4. **Optional, when you want more.** L2 voice: set `--bw-font-family-sans`,
   `-display` and `-mono` (the northline file shows all three). L3 material:
   author `--bw-radius-sm/md/lg` and `--bw-elevation-1/2/3`; modal, toast and
   popover panels also read `--bw-radius-xl`, and open modal, slide-over and
   toast read `--bw-elevation-4` and `-5`, so author those steps if overlays
   should follow your brand. Levels, minimums and honesty rules:
   [THEME.md](THEME.md#depth-ladder).

## What brickwork is

**Beautiful by default.** Frontend your Django site fast, confident it
delivers an excellent experience across devices. brickwork is the
server-rendered Django interface foundation: brand-agnostic tokens, shells,
components, Theme profiles and copyable pages you own, on Tailwind 4
(CSS-first), Alpine 3 and HTMX 2. Django is its only hard runtime dependency.
It is not a Django-admin skin: it is for your hand-built interfaces across
public sites, product applications, data-heavy operations, documentation,
editorial publishing and transactional journeys. Quote shipping coverage from
[docs/POSITIONING.md](POSITIONING.md); do not claim every interface-system
archetype is done.

**Mechanism:** pin the foundation; own the pages; Theme with `--bw-*` (L1 to
L4). Rebranding is token-first: every visual value is a `--bw-*` custom
property, so you rebrand by overriding tokens, never by touching component
classes ([docs/BRANDING.md](BRANDING.md)).

## Prerequisites

- **Django 6.0 or later.** brickwork uses core `{% partialdef %}` template
  partials with no compatibility shim; there is no pre-6.0 path.
- **Python 3.12 or later.**
- Alpine 3 (plus `@alpinejs/focus`) and, if you want the interaction
  contracts, htmx 2.0 or later, both provided by your own frontend build.
  brickwork registers against your Alpine instance; it never calls
  `Alpine.start()` itself.

## Install

From public PyPI:

```
uv add django-brickwork             # or: pip install django-brickwork
```

```python
INSTALLED_APPS = [
    "brickwork",
    "brickwork.marketing",  # optional: public-site shell, see below
    # ...
]
```

The marketing surface is a second, opt-in app: add `brickwork.marketing`
alongside `brickwork`, never in place of it. Its templates live under their
own `brickwork_marketing/` namespace, so the marketing shell is
`brickwork_marketing/shell/marketing.html`, not `brickwork/shell/marketing.html`
(that path does not exist). This is deliberate: a consumer who never adds it
gets output byte-identical to a bare `brickwork` install, and the separate
namespace means the two apps version independently and neither shadows the
other.

The optional `[htmx]` extra (`django-htmx>=1.28`) is not required: brickwork
inlines the `HX-Request` header check itself and only uses the richer
`request.htmx` surface when you already run django-htmx. Add the extra only
if you want that.

## A first taste of re-skinning (L1 Recolour)

Seven load-bearing colour tokens start an **L1 Brickwork Theme**
([THEME.md](THEME.md)): base-theme derives the hover shades, subtle tints,
muted foregrounds, status tiers and component roles from these values, live
in the browser, with no rebuild. That is recolour, not a full brand; add fonts
(L2), material axes (L3), and rhythm (L4) when you need them.

```css
/* your brand.css, loaded after brickwork's tokens.css */
:root {
  --bw-color-surface: oklch(0.99 0.003 90);
  --bw-color-fg:      oklch(0.24 0.02 270);
  --bw-color-border:  oklch(0.90 0.008 270);
  --bw-color-accent:  oklch(0.55 0.20 265);
  --bw-color-danger:  oklch(0.55 0.19 25);
  --bw-color-success: oklch(0.56 0.14 150);
  --bw-color-warning: oklch(0.68 0.15 75);
}
[data-theme="dark"] {
  --bw-color-surface: oklch(0.22 0.015 270);
  --bw-color-fg:      oklch(0.93 0.01 90);
  --bw-color-border:  oklch(0.34 0.015 270);
  --bw-color-accent:  oklch(0.68 0.17 265);
  --bw-color-danger:  oklch(0.65 0.18 25);
  --bw-color-success: oklch(0.66 0.13 150);
  --bw-color-warning: oklch(0.72 0.14 80);
}
```

Load order is load-bearing and fails silently: your brand stylesheet must
load after brickwork's, or your overrides lose the cascade.

These seven are the L1 load-bearing minimum, not the whole theme story.
`--bw-color-fg-on-accent` is authored per theme, never derived, and must be
verified at 4.5:1 against its own accent: white is not a safe default, the
safe value flips with the accent's lightness, and a dark theme with a light
accent is the common case that inverts the intuition.
`--bw-color-surface-inverse` is conditional too, needed only when your ink is
not the inverse surface. See
[BRANDING.md's fg-on-accent section](BRANDING.md#the-fg-on-accent-trap-do-not-assume-white-brickwork35)
for the worked failure.

## Where to go next

- **Starting from nothing:** [Path A](#path-a-from-an-empty-directory). One
  command, `python -m brickwork startsite`, emits a running starter project
  (`public-site` or `data-app`) and is where a new consumer should start.
- **Adding brickwork to an existing project:**
  [Path B](#path-b-an-existing-project-one-complete-page), one complete page.
- **Building a new screen, or a project with no existing UI kit to
  displace:** go straight to [docs/INTEGRATION.md](INTEGRATION.md). It
  is the seam-by-seam cookbook: settings and static, the nav config, the
  context processor, a worked HTMX form (the 422 loop and the success
  redirect), and the chrome/body boundary for pages with app-owned
  JavaScript.
- **Migrating an existing app off a hand-built shell or component kit:**
  go to [docs/ADOPTION.md](ADOPTION.md). It is the strangle guide:
  moving cluster by cluster, keeping the old kit alive alongside brickwork
  until the last screen moves, with the wrinkles a real cutover hits
  (multi-host projects, asset-pipeline coexistence, a second component
  framework in the content block).
- **Copyable pages to start from:** the `src/brickwork/examples/` tree ships
  50 examples (22 pages, 28 sections), plus a separate document skeleton.
  They compose shipped tokens and components; the date range picker also
  supplies its own scoped token-based CSS. See [Example pages](../README.md#example-pages) in the README for
  how to use one.
- **Token reference:** [docs/DESIGN.md](DESIGN.md) is the authoritative
  list of every `--bw-*` token, its default, and its derivation rule.
- **Brickwork Theme:** [docs/THEME.md](THEME.md) defines L1 to L4 profiles on
  `--bw-*`. **A portable brand documentation pack:** [docs/brand-pack.md](brand-pack.md)
  binds measured identity prose to a `--bw-*` override delta, PROFILE level,
  and a preview path; copy the fictional
  [northline skeleton](examples/brand-pack/northline/) to start.
- **Own Vite + Tailwind layout utilities:** [INTEGRATION.md §1.3](INTEGRATION.md#13-vite--tailwind-4-consumer-recipe-brickwork-theme-phase-f)
  and [examples/vite-tailwind/](examples/vite-tailwind/); sync the projection
  with `manage.py sync_brickwork_projection` instead of copying from
  site-packages.
- **Re-skinning the whole site:** [docs/BRANDING.md](BRANDING.md) takes the
  seven tokens above further: dark mode, the four theme axes, and dynamic
  per-tenant or per-user theming.
- **Visual quality bar (maintainers):** [docs/VISUAL-BAR.md](VISUAL-BAR.md)
  stamps the Tailwind UI kit panel and scorecard brickwork must meet; it is
  not a consumer wiring guide.

## Accessibility

Accessibility is tested, not asserted by design: CI blocks every push on an
axe-core WCAG 2.2 AA scan across 178 documents (132 hand-maintained fixtures
plus 46 catalogue documents, being 22 archetypes and 1 skeleton, each x light
and dark themes), plus a no-JS
floor suite, keyboard suites, mobile-overflow checks, and pixel-level
composited contrast measurement. See [README.md](../README.md)
for detail, including why the automated gate has a known ceiling and what
closes the gap.
