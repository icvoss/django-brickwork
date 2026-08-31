# Adoption quickstart

A short "start here" for a Django developer bringing brickwork into an app.
It orients you and then routes you to the guide that actually has the
detail: [docs/INTEGRATION.md](INTEGRATION.md) for wiring plumbing, or
[docs/ADOPTION.md](ADOPTION.md) for migrating an existing UI onto it.
This page is deliberately thin; do not look here for the wiring steps
themselves.

## What brickwork is

**Beautiful defaults, proved by the examples.** brickwork is a brand-agnostic
interface foundation for server-rendered Django. It owns reusable design across
public sites, product applications, data-heavy operations, documentation,
editorial publishing and transactional journeys, on Tailwind 4 (CSS-first),
Alpine 3 and HTMX 2. Django is its only hard runtime dependency. It is not a
Django-admin skin: it is for your hand-built interfaces.

Rebranding is token-first: every visual value is a `--bw-*` custom property,
so you rebrand by overriding tokens, never by touching component classes
([docs/BRANDING.md](BRANDING.md)).

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
    # ...
]
```

The optional `[htmx]` extra (`django-htmx>=1.28`) is not required: brickwork
inlines the `HX-Request` header check itself and only uses the richer
`request.htmx` surface when you already run django-htmx. Add the extra only
if you want that.

## Where to go next

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
  50 examples (23 pages, 27 sections) built entirely from shipped tokens and
  components. See [Example pages](../README.md#example-pages) in the README for
  how to use one.
- **Token reference:** [docs/DESIGN.md](DESIGN.md) is the authoritative
  list of every `--bw-*` token, its default, and its derivation rule.
- **Theming a brand:** [docs/BRANDING.md](BRANDING.md) covers the
  load-bearing token minimum, dark mode, the four theme axes, and dynamic
  per-tenant or per-user theming.

## Accessibility

Accessibility is tested, not asserted by design: CI blocks every push on an
axe-core WCAG 2.2 AA scan across 112 documents (56 fixtures, light and dark
themes), plus a no-JS floor suite, keyboard suites, mobile-overflow checks,
and pixel-level composited contrast measurement. See [README.md](../README.md)
for detail, including why the automated gate has a known ceiling and what
closes the gap.
