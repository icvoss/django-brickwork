# brickwork

**Beautiful defaults, proved by the examples.** brickwork ships 50 examples
(22 archetype pages, 28 sections; a 51st file, `base.html`, is a raw document
skeleton a consumer copies rather than a page in its own right) built from
nothing but its own shipped tokens and components. 50 of the 51 files add no
CSS at all. The one that does is the date range picker, whose scoped
`.bw-drp` block uses only existing `--bw-*`
tokens, because brickwork ships no date picker component for it to compose
(see [Example pages](#example-pages)). Every one is readable in the repo, so
"the defaults are beautiful" is a claim you check by opening a file rather
than one you take on trust.

A brand-agnostic interface foundation for server-rendered Django, on the
ecosystem stack: Tailwind 4 (CSS-first), Alpine 3, HTMX 2, Django 6.0.
Brickwork is designed to cover public sites, product applications, data-heavy
operations, documentation, editorial publishing and transactional journeys
through shared foundations, components, layouts and copyable archetypes.
Its target is that a team can deliver those interfaces without introducing a
second UI kit or design language. See [the interface-system
contract](docs/INTERFACE-SYSTEM.md) for the intended coverage and the current
example catalogue for what ships today.

**This is not a Django-admin skin.** Consumers provide data, permissions and
business behaviour; Brickwork owns the reusable interface design, on a
professional, tested-accessible baseline: RTL via logical properties, a real
themeable dark-mode system, and four composable theme axes (brand x theme x
density x direction). Rebranding is token-first: every visual value is a
`--bw-*` custom property, so a consumer rebrands by overriding tokens, never
by touching component classes.

Accessibility is tested, not asserted by design. CI blocks every push on an
axe-core WCAG 2.2 AA scan across 176 documents (130 hand-maintained fixtures
plus 46 catalogue documents, being 22 archetypes and 1 skeleton, each x light
and dark themes), plus a no-JS floor suite, keyboard suites,
mobile-overflow checks at
320/360/375/414px, and pixel-level composited contrast measurement. That last
check exists because the axe gate itself once ran green over a real 4.25:1
contrast defect (axe's contrast check does not rasterise the page, so text
over a background image reports "incomplete" rather than a violation); the
gate catching its own blind spot and adding a check for it is stronger
evidence than a gate that has never missed.

> Status: **stable**. This checkout is version 3.16.0 (`pip install
> django-brickwork` for the published package);
> [CHANGELOG.md](CHANGELOG.md) records the current release. The five
> semver-governed public-API contracts (token, template, navigation,
> interaction, JavaScript) are live. The surface covers the
> application shell and nav, the beautiful-by-default token system
> (elevation, state overlays, type
> roles, motion, borders, with fine colours derived live from a small
> load-bearing brand set via `color-mix()`), the interaction set (modal,
> toast, dropdown, combobox, tabs, disclosure, tooltip, slide-over), forms
> with the whole-form renderer and the HTMX 422 loop, the data table with
> sortable and selectable modes, the feedback and input-chrome primitives, the
> wizard/stepper, and a machine-readable token contract with a per-tenant
> brand-CSS emitter.
>
> **See it running:** [brickwork.icvoss.com](https://brickwork.icvoss.com) is
> the live interactive demo and template gallery, and
> [icvoss.com/packages/django-brickwork](https://icvoss.com/packages/django-brickwork)
> hosts the package documentation page.
>
> **Marketing kit (1.2.0+).** brickwork also ships an opt-in
> `brickwork.marketing` sub-app (a marketing shell and nine marketing
> components: hero, feature grid, pricing tier, pricing table, CTA,
> testimonial, logo cloud, stat band, FAQ) on the same `--bw-*` token and
> accessibility contract, so a consumer can build its public marketing pages
> on brickwork alongside its console. Worked landing/pricing/about pages are
> shipped as copy-paste examples, not importable templates: see
> [Example pages](#example-pages) below.

## Documentation

- [docs/DESIGN.md](docs/DESIGN.md): the canonical token reference; every
  `--bw-*` name, default value, and derivation rule.
- [docs/INTERFACE-SYSTEM.md](docs/INTERFACE-SYSTEM.md): the intended coverage,
  ownership boundary and required archetypes for the complete interface system.
- [docs/ROADMAP.md](docs/ROADMAP.md): the active plan from the current package
  to complete interface-system coverage.
- [docs/BRANDING.md](docs/BRANDING.md): how a consuming app brands brickwork
  (the load-bearing token minimum, dark mode, the four axes, the fg-on-accent
  contrast trap, and dynamic per-tenant / per-user theming recipes).
- [docs/QUICKSTART.md](docs/QUICKSTART.md): start here. Orients you, then
  routes you to the right guide below.
- [docs/INTEGRATION.md](docs/INTEGRATION.md): the greenfield integration
  cookbook, the seams a consuming app wires end to end (settings and static, nav
  config, context processor, a worked HTMX 422 form, the chrome/body boundary).
- [docs/ADOPTION.md](docs/ADOPTION.md): the strangle guide for migrating an
  existing app onto brickwork cluster by cluster (multi-host, asset coexistence,
  the htmx floor).
- [src/brickwork/examples/README.md](src/brickwork/examples/README.md): the
  copy-paste example pages, what each one is, and how to use one (see
  [Example pages](#example-pages) below).
- [frontend/README.md](frontend/README.md): the in-repo build that compiles
  the shipped static assets.

## Install

From public PyPI:

```
uv add django-brickwork             # or: pip install django-brickwork
```

```python
INSTALLED_APPS = [
    "brickwork",
    # ...
]
```

The compiled CSS and JS ship inside the package and are referenced with plain
`{% static %}`; no build-tool dependency (django-vite / django-tailwind) is
imposed on consumers. Consumers provide their own Alpine 3 +
`@alpinejs/focus` (and optionally htmx 2) via their own frontend build; brickwork
registers behaviour onto the host Alpine instance and never calls
`Alpine.start()`.

Starting a project from nothing? Skip ahead to `manage.py startsite` in the
Quickstart section below: it emits a running, designed project rather than
walking you through wiring one by hand.

### Supported versions

| Dependency | Supported |
|------------|-----------|
| Python | 3.12+ |
| Django | 6.0 (the CI-tested matrix; later majors are not yet asserted, and the dependency pin is deliberately floor-only) |
| htmx | >= 2.0 for the interaction contracts (see below); not required otherwise |
| Alpine.js | 3.x plus `@alpinejs/focus`, provided by the host app |
| Browsers | evergreen; the interaction suite is CI-tested on Chromium (Playwright) |

### htmx floor: htmx >= 2.0

brickwork's interaction contracts (the HTMX 422 form-swap loop, toast delivery
via `hx-swap-oob`, modal dismissal via the `HX-Trigger: bw:modal:close` response
header, combobox server filtering) are built and CI-gated on **htmx >= 2.0**
only. htmx 1.9 is out of contract (BR-BW-HTMX-010): htmx 2 changed default
response handling in ways the 422 loop relies on, and the interaction suites only
ever exercise htmx 2. A brownfield app on htmx 1.9 should upgrade htmx to 2.x as a
prerequisite before adopting brickwork's interaction primitives; see
[docs/ADOPTION.md](docs/ADOPTION.md).

## Quickstart: the fastest path is a command, not this section

```
python manage.py startsite myproject
```

emits a minimal, running project: settings wired for brickwork (and the
optional marketing kit), a contrast-verified brand file, a validated nav
config, and three real pages, each with the view that feeds it. `cd
myproject && python manage.py runserver` and the page looks designed, not
structurally correct and empty. The emitted project is yours outright from
the moment it is written, with no update path back into it (ADR-095); see
[docs/QUICKSTART.md](docs/QUICKSTART.md#the-fastest-path-emit-a-starter-project).

The rest of this section wires the same seams by hand, for a project that
already has its own settings and routing brickwork needs to fit into.

Five minutes from install to a themed, accessible console page. Wire the app
and the shell context processor:

```python
# settings.py
INSTALLED_APPS = [
    "brickwork",
    # ...
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        # ... Django's defaults ...
        "brickwork.context_processors.theme",   # wires theme/density/dir onto <html>
        "yourapp.context_processors.nav",
    ]},
}]
```

Declare the nav once, validated at import:

```python
# yourapp/nav.py
from brickwork.models import NavItem
from brickwork.services.navigation import validate_nav_config

NAV = [
    NavItem(label="Dashboard", url_name="dashboard"),
]
validate_nav_config(NAV)
```

```python
# yourapp/context_processors.py
from brickwork.services.navigation import resolve_active_item, visible_items
from yourapp.nav import NAV

def nav(request):
    return {
        "nav_items": visible_items(NAV, request),
        "nav_active": resolve_active_item(NAV, request),
    }
```

Extend the shell and fill its blocks:

```django
{# yourapp/templates/yourapp/dashboard.html #}
{% extends "brickwork/shell/app.html" %}
{% load brickwork_nav %}

{% block sidebar %}{% bw_nav nav_items nav_active %}{% endblock %}

{% block page_header %}
  {% include "brickwork/components/_page_header.html" with title="Dashboard" %}
{% endblock %}

{% block content %}
  {% include "brickwork/components/_empty_state.html" with heading="Nothing here yet" body="Create your first project to get going." %}
{% endblock %}
```

```python
# yourapp/views.py
from django.shortcuts import render

def dashboard(request):
    return render(request, "yourapp/dashboard.html", {"bw_page_title": "Dashboard"})
```

Run `collectstatic` and open the page: shell, sidebar nav with active-route
highlighting, skip link, dark mode and density axes, all on the default theme.
Branding it is a handful of `--bw-*` token overrides
([docs/BRANDING.md](docs/BRANDING.md)); the full seam-by-seam walkthrough is
[docs/INTEGRATION.md](docs/INTEGRATION.md).

## Example pages

A whole page is the most project-specific thing you own, so brickwork does not
ship one as a template you extend. Instead it ships sixteen complete, working
pages built from its tokens, components and shells, as copy-paste examples in
`src/brickwork/examples/` (`base.html`; `app/list`, `detail`, `dashboard`,
`date-range-picker`, `form`, `wizard`, `settings`, `console`, `confirm`;
`auth/signin`, `signup`, `reset`; `marketing/landing`, `pricing`, `about`).

Looking for a date picker: Brickwork does not currently ship a maintained
`bw_date_picker` component, but it does ship a complete copyable date-range
picker. `app/date-range-picker.html` provides a calendar popover with weekday
and month grids, locale-aware via Django's own `django.utils.dates`, including
single-date mode, over a native `<input type="date">` no-JavaScript floor that
stays the submitted control. Copy it and adapt it. Brickwork owns the
date-entry interface pattern, while the copied page remains yours outright.

They cannot be extended, by construction: the directory is package data, not
an app `templates/` folder, so Django's `APP_DIRS` loader cannot see it and
`{% extends "brickwork/examples/..." %}` raises `TemplateDoesNotExist`. That
is deliberate (ADR-056): a page you import is a page a dependency can reshape
on your next pin bump; a page you copy is yours outright.

To use one: open it (in the repo, or via `brickwork.examples.read_example()`),
copy it into your own `templates/` tree, and edit it. Each example is
annotated with what your view must supply and stays real, specific content
throughout, never `Lorem ipsum`. See
[src/brickwork/examples/README.md](src/brickwork/examples/README.md) for the
full list and how they are tested.

Extending a shell directly (`brickwork/shell/app.html`,
`brickwork_marketing/shell/marketing.html`, and friends) remains fully
supported and is the option that keeps receiving improvements automatically;
copying an example is the alternative for a project that wants to own its
page outright from day one.

## Contracts

brickwork's public API is five versioned contracts: **token**, **template**,
**navigation**, **interaction (HTMX)**, and **JavaScript (Alpine)**. Template
block names, HTMX target IDs, Alpine component names, event names and token
names are semver-governed. [docs/DESIGN.md](docs/DESIGN.md) enumerates the
token contract, [docs/INTEGRATION.md](docs/INTEGRATION.md) walks the template,
navigation and interaction seams, and [CHANGELOG.md](CHANGELOG.md) records
every contract change release by release.

## Usage

### Tags vs includes

Some components are consumed as **template tags**, others via `{% include %}`.
This is deliberate: a component that carries logic (variant validation, a11y
enforcement, icon resolution) ships as a tag so that logic is not duplicated at
every call site; a purely structural component is an include the consumer fills
with context.

- **Tags** (load the library first): `{% bw_icon %}`, `{% bw_button %}`,
  `{% bw_badge %}`, `{% bw_alert %}`, `{% bw_nav %}`, `{% bw_nav_header %}`,
  `{% bw_nav_rail %}`, `{% bw_field_widget %}`, `{% bw_dropdown %}`,
  `{% bw_tabs %}`, `{% bw_toast %}`, `{% bw_combobox %}`. The three nav tags
  are sibling renderers over the same `NavItem` tree: the sidebar/tree render,
  the horizontal marketing-header row, and the compact two-tier rail (see
  [INTEGRATION.md](docs/INTEGRATION.md) section 2).

  ```django
  {% load brickwork_components brickwork_icons brickwork_nav %}
  {% bw_button label="Save" variant="primary" %}
  {% bw_badge label="New" variant="info" %}
  ```

  The `_button.html` / `_badge.html` / `_alert.html` template files exist but are
  the tags' own render targets, **not** a consumer-facing `{% include %}` API.
  Call the tag, not the partial.

  `{% bw_dropdown %}` items may carry an optional `attrs` mapping for
  consumer-owned hooks on the rendered item, for example
  `{"data-item-id": widget.pk}`. Only `data-*` names are accepted; Brickwork's
  own `data-bw-*` hooks remain reserved (ADR-083: this is the same rule as the
  `data` seam below, not a wider one, since the seam protects what a
  component deliberately withholds, not just what it emits).

- **Includes** (structure you fill with context): `_page_header.html`,
  `_data_table.html`, `_pagination.html`, `_empty_state.html`,
  `_filter_bar.html`, `_spinner.html`, and the form partials `forms/_field.html`
  / `forms/_form_errors.html`.

  ```django
  {% include "brickwork/components/_data_table.html" with table_id="gadgets" columns=columns rows=rows %}
  ```

  Record rows may include a `data` mapping for consumer-owned hooks on the
  rendered row, for example `{"data-item-id": gadget.pk}`. Only `data-*`
  names are accepted; Brickwork's own `data-bw-*` hooks remain reserved.
  `_stat.html` accepts the same optional `data` mapping on its tile root.

### Icons: decorative or labelled, always

`{% bw_icon %}` **requires** exactly one of `decorative=True` or `label="..."`,
and raises `TemplateSyntaxError` if given neither or both. This is intentional
(ICO-007, WCAG 4.1.2): an icon is either purely presentational (aria-hidden) or
carries meaning (an accessible name), never ambiguous.

```django
{% bw_icon "search" decorative=True %}          {# beside a visible label #}
{% bw_icon "trash" label="Delete item" %}       {# standalone, meaningful #}
```

You rarely call `bw_icon` directly for the icon *inside* a `bw_button` or
`bw_nav` item: those tags take an `icon="..."` argument and handle the a11y
pairing for you. Reach for `bw_icon` directly only for a standalone icon in your
own markup, where this rule applies.

## Development

Python package:

```
pip install -e ".[dev]"
pytest
```

Frontend build (compiles tokens + component assets into the package's static
dir; see `frontend/README.md`):

```
npm install
npm run build
```

## Licence

MIT. See [LICENSE](LICENSE).
