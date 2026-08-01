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

> Status: **0.3.0, the beautiful-by-default release.** The five semver-governed
> public-API contracts (token, template, navigation, interaction, JavaScript)
> are live, and every component passes two hard gates: is it accessible
> (axe-core WCAG 2.2 AA in CI) and is it beautiful by default. 0.3.0 ships the
> complete token vocabulary (elevation, state overlays, type roles, motion,
> z-index, borders), with the fine colour tokens derived live from a small
> load-bearing brand set via `color-mix()` (ADR-054 Phase a, additive and
> non-breaking). The design of record is the spec and brief in the icvoss/oss
> umbrella:
> - Spec: `docs/specs/django-brickwork/` (the five versioned public-API contracts).
> - Brief: `docs/plans/django-brickwork-request.md`.
> - Audit evidence: `docs/reviews/django-brickwork-baseline-audit-2026-07-29/`.

## Documentation

- [docs/DESIGN.md](docs/DESIGN.md): the canonical token reference; every
  `--bw-*` name, default value, and derivation rule.
- [docs/BRANDING.md](docs/BRANDING.md): how a consuming app brands brickwork
  (the load-bearing token minimum, dark mode, the four axes).
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
