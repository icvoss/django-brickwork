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

## A first taste of re-skinning

Seven load-bearing colour tokens make a brand: base-theme derives the hover
shades, subtle tints, muted foregrounds, status tiers and component roles
from these values, live in the browser, with no rebuild.

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

These seven are the load-bearing minimum, not the whole story.
`--bw-color-fg-on-accent` is authored per theme, never derived, and must be
verified at 4.5:1 against its own accent: white is not a safe default, the
safe value flips with the accent's lightness, and a dark theme with a light
accent is the common case that inverts the intuition.
`--bw-color-surface-inverse` is conditional too, needed only when your ink is
not the inverse surface. See
[BRANDING.md's fg-on-accent section](BRANDING.md#the-fg-on-accent-trap-do-not-assume-white-brickwork35)
for the worked failure.

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
  51 examples (23 pages, 28 sections) built entirely from shipped tokens and
  components. See [Example pages](../README.md#example-pages) in the README for
  how to use one.
- **Token reference:** [docs/DESIGN.md](DESIGN.md) is the authoritative
  list of every `--bw-*` token, its default, and its derivation rule.
- **Re-skinning the whole site:** [docs/BRANDING.md](BRANDING.md) takes the
  seven tokens above further: dark mode, the four theme axes, and dynamic
  per-tenant or per-user theming.

## Accessibility

Accessibility is tested, not asserted by design: CI blocks every push on an
axe-core WCAG 2.2 AA scan across 176 documents (130 hand-maintained fixtures
plus 46 catalogue archetypes, each x light and dark themes), plus a no-JS
floor suite, keyboard suites, mobile-overflow checks, and pixel-level
composited contrast measurement. See [README.md](../README.md)
for detail, including why the automated gate has a known ceiling and what
closes the gap.
