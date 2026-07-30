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

> Status: **pre-alpha scaffold.** The design of record is the spec and brief in
> the icvoss/oss umbrella:
> - Spec: `docs/specs/django-brickwork/` (the five versioned public-API contracts).
> - Brief: `docs/plans/django-brickwork-request.md`.
> - Audit evidence: `docs/reviews/django-brickwork-baseline-audit-2026-07-29/`.

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
imposed on consumers. Consumers provide their own Alpine 3 + `@alpinejs/ui` +
`@alpinejs/focus` (and optionally htmx 2) via their own frontend build; brickwork
registers behaviour onto the host Alpine instance and never calls
`Alpine.start()`.

## Contracts

brickwork's public API is five versioned contracts (see the spec): **token**,
**template**, **navigation**, **interaction (HTMX)**, and **JavaScript
(Alpine)**. Template block names, HTMX target IDs, Alpine component names,
event names and token names are semver-governed.

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
