# brickwork

A brand-agnostic, app-facing professional UI substrate for server-rendered
Django, on the ecosystem stack: Tailwind 4 (CSS-first), Alpine 3, HTMX 2,
Django 6.0. It provides the application shell, navigation and active-route
resolution, an accessible form-field renderer, and interaction primitives
(modal, toast, dropdown, combobox, tabs, disclosure) wrapped behind stable
Django components.

**This is not a Django-admin skin.** Its value is the professional baseline:
WCAG 2.2 AA as a *tested* guarantee (axe-core in CI, not a claim), RTL via
logical properties, a real themeable dark-mode system, and four composable
theme axes (brand x theme x density x direction). Applications provide data,
permissions and business behaviour; the substrate provides structure,
presentation and interaction conventions.

> Status: **0.16.0, graduating to public PyPI.** The five semver-governed
> public-API contracts (token, template, navigation, interaction, JavaScript)
> are live, and every component passes two hard gates: is it accessible
> (axe-core WCAG 2.2 AA in CI) and is it beautiful by default. The surface is
> complete: the application shell and nav, the beautiful-by-default token system
> (elevation, state overlays, type roles, motion, borders, with fine colours
> derived live from a small load-bearing brand set via `color-mix()`), the
> interaction set (modal, toast, dropdown, combobox, tabs, disclosure, tooltip,
> slide-over), forms with the whole-form renderer and the HTMX 422 loop, the
> data table with sortable and selectable modes, the feedback and input-chrome
> primitives, the wizard/stepper, and a machine-readable token contract with a
> per-tenant brand-CSS emitter. The design of record is the spec and brief in
> the icvoss/oss umbrella:
> - Spec: `docs/specs/django-brickwork/` (the five versioned public-API contracts).
> - Design + branding + integration: `docs/DESIGN.md`, `docs/BRANDING.md`,
>   `docs/INTEGRATION.md`, `docs/ADOPTION.md`.
> - Changelog: `CHANGELOG.md` (0.1.0 through 0.16.0).

## Documentation

- [docs/DESIGN.md](docs/DESIGN.md): the canonical token reference; every
  `--bw-*` name, default value, and derivation rule.
- [docs/BRANDING.md](docs/BRANDING.md): how a consuming app brands brickwork
  (the load-bearing token minimum, dark mode, the four axes, the fg-on-accent
  contrast trap, and dynamic per-tenant / per-user theming recipes).
- [docs/INTEGRATION.md](docs/INTEGRATION.md): the greenfield integration
  cookbook, the seams a consuming app wires end to end (settings and static, nav
  config, context processor, a worked HTMX 422 form, the chrome/body boundary).
- [docs/ADOPTION.md](docs/ADOPTION.md): the strangle guide for migrating an
  existing app onto brickwork cluster by cluster (multi-host, asset coexistence,
  the htmx floor).
- [frontend/README.md](frontend/README.md): the in-repo build that compiles
  the shipped static assets.

## Install

```
pip install django-brickwork        # from pypi.icvoss.com (private index)
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

### htmx floor: htmx >= 2.0

brickwork's interaction contracts (the HTMX 422 form-swap loop, toast delivery
via `hx-swap-oob`, modal dismissal via the `HX-Trigger: bw:modal:close` response
header, combobox server filtering) are built and CI-gated on **htmx >= 2.0**
only. htmx 1.9 is out of contract (BR-BW-HTMX-010): htmx 2 changed default
response handling in ways the 422 loop relies on, and the interaction suites only
ever exercise htmx 2. A brownfield app on htmx 1.9 should upgrade htmx to 2.x as a
prerequisite before adopting brickwork's interaction primitives; see
[docs/ADOPTION.md](docs/ADOPTION.md).

## Contracts

brickwork's public API is five versioned contracts (see the spec): **token**,
**template**, **navigation**, **interaction (HTMX)**, and **JavaScript
(Alpine)**. Template block names, HTMX target IDs, Alpine component names,
event names and token names are semver-governed.

## Usage

### Tags vs includes

Some components are consumed as **template tags**, others via `{% include %}`.
This is deliberate: a component that carries logic (variant validation, a11y
enforcement, icon resolution) ships as a tag so that logic is not duplicated at
every call site; a purely structural component is an include the consumer fills
with context.

- **Tags** (load the library first): `{% bw_icon %}`, `{% bw_button %}`,
  `{% bw_badge %}`, `{% bw_alert %}`, `{% bw_nav %}`, `{% bw_field_widget %}`.

  ```django
  {% load brickwork_components brickwork_icons brickwork_nav %}
  {% bw_button label="Save" variant="primary" %}
  {% bw_badge label="New" variant="info" %}
  ```

  The `_button.html` / `_badge.html` / `_alert.html` template files exist but are
  the tags' own render targets, **not** a consumer-facing `{% include %}` API.
  Call the tag, not the partial.

- **Includes** (structure you fill with context): `_page_header.html`,
  `_data_table.html`, `_pagination.html`, `_empty_state.html`,
  `_filter_bar.html`, `_spinner.html`, and the form partials `forms/_field.html`
  / `forms/_form_errors.html`.

  ```django
  {% include "brickwork/components/_data_table.html" with table_id="gadgets" columns=columns rows=rows %}
  ```

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
