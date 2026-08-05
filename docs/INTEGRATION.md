# Integrating brickwork into a consuming project

A seam-by-seam cookbook for wiring a real Django app onto brickwork, in the
order you hit each seam. [BRANDING.md](BRANDING.md) covers *theming* (overriding
tokens); [DESIGN.md](DESIGN.md) is the authoritative token reference; this guide
covers *plumbing*: the settings, the nav config, the context processor, a
worked HTMX 422 form, the "brickwork owns the chrome, you own the body"
boundary for JS-bearing pages, and the auth-aware marketing header. It is the greenfield companion to
[ADOPTION.md](ADOPTION.md) (strangling an existing kit onto brickwork).

Every code snippet here is a real seam a consuming app must wire; each maps to a
finding from a pilot integration, so this is the walkthrough that would have
saved those pilots their discovery time.

## 1. Settings and static

### INSTALLED_APPS and templates

brickwork is a plain Django app on `APP_DIRS` template resolution. Add it, and
the context processor that wires the shell (see section 3):

```python
INSTALLED_APPS = [
    # ...
    "brickwork",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                # ... Django's defaults ...
                "brickwork.context_processors.theme",
            ],
        },
    },
]
```

### Static files and where your override stylesheet loads

brickwork ships its compiled `brickwork.css` (tokens plus component classes) as
a static asset. Run `collectstatic` as usual; the shell references the stylesheet
for you. Your brand override stylesheet must load **after** `brickwork.css` so
your `--bw-*` overrides win the cascade (BRANDING.md). The shell exposes a
`head_extra` block for exactly this:

```django
{% extends "brickwork/shell/app.html" %}

{% block head_extra %}
  {{ block.super }}
  <link rel="stylesheet" href="{% static 'yourapp/brand.css' %}">
{% endblock %}
```

That single `<link>`, holding your ~7-14 token brand delta, is the whole visual
rebrand. Do not fork brickwork's stylesheet or reach into its component classes;
override tokens only.

### What `brickwork.css` provides, and what it does not (brickwork#64)

`brickwork.css` styles the **substrate**: the `bw-*` component and shell classes
(`.bw-card`, `.bw-data-table`, `.bw-page-header`, the shell layout) and the token
definitions they consume. It does **not** ship a general Tailwind utility layer:
it contains no `.grid`, `.gap-4`, `.px-3`, `.sm:grid-cols-2` and the like.

This matters for your **page content** (everything inside `{% block content %}`).
brickwork gives you the chrome and the components; the layout and spacing of your
own content is yours to author, and if you write it in Tailwind utilities you must
generate those utilities yourself. Two supported paths:

1. **Import brickwork's projection into your own Tailwind build** (recommended):
   import `dist/tailwind-theme.css` after your `tailwindcss` import, and your
   utilities (`bg-accent`, `p-4`, `rounded-md`, `text-heading-lg`) inherit
   brickwork's defaults and any active brand automatically (DESIGN.md section 12).
   Your Tailwind build then emits the utility classes your content uses.
2. **Link your own CSS bundle** on every brickwork-shell page (via `head_extra`),
   carrying whatever utility or component classes your content needs.

Either way, `brickwork.css` alone will not style content authored in plain
Tailwind utilities. (Through 0.9.0 an app-facing utility layer happened to ship
inside `brickwork.css`; 0.10.0 moved utility generation out to the projection, so
a consumer implicitly relying on it must adopt path 1 or 2. See the 0.10.0
migration note in the CHANGELOG.)

### Static include-linters: allowlist the `brickwork/` namespace (brickwork#34)

brickwork ships its shell, component, and form templates **inside the installed
package**, resolved at runtime via `APP_DIRS`. If your project runs a static
template-include linter (a guard that checks every `{% include %}` / `{% extends %}`
target resolves under a known template root), it will fail on every brickwork
reference, because the package templates are not in your project tree.

Allowlist the `brickwork/` namespace in that linter. If the guard runs in more
than one place (a local Makefile target and a separate CI invocation are the
classic pair), update **every** invocation; a guard that passes locally and
fails only in CI is almost always a second copy you missed. This is a heads-up,
not a brickwork bug: the templates genuinely live in the package, by design.

## 2. The nav config

Navigation is a declarative `NavItem` tree, validated once at import, resolved
against the active route per request. The shell renders it via `{% bw_nav %}`.

```python
# yourapp/nav.py
from brickwork.models import NavItem
from brickwork.services.navigation import validate_nav_config

NAV = [
    NavItem(label="Dashboard", url_name="dashboard"),
    NavItem(
        label="Projects",
        url_name="project-list",
        # a section that stays "active" across several detail views:
        active_url_names=("project-list", "project-detail", "project-edit"),
        children=[
            NavItem(label="All projects", url_name="project-list"),
            NavItem(label="Archived", url_name="project-list-archived"),
        ],
    ),
]

# Fail fast at import, not at first render:
validate_nav_config(NAV)
```

Read `visible_items(nav, request)` / `resolve_active_item(nav, request)` in your
view or a context processor to get the gated, active-resolved tree the shell
renders. Gating is per item via `visibility_policy` / permission callables;
`active_url_names` is how a section stays highlighted across the several views
that belong to it (multi-view active).

### Route parameters: `kwarg_name` and the resolver-match hook (brickwork#19)

Nav items that reverse a parameterised route (a project-scoped sidebar) pull the
parameter from the **active route's** kwargs. Two ergonomics tiers:

- **The common case, one renamed kwarg.** When a route names the shared
  parameter differently from your nav's default (your nested routes use
  `project_slug` but the detail route captures it as `slug`), set
  `kwarg_name` on the item rather than writing a callable:

  ```python
  NavItem(label="Documents", url_name="project-documents", kwarg_name="project_slug")
  ```

  `kwarg_name` also accepts a `(reverse_name, capture_name)` tuple for the
  "this one route calls it something else" mapping, so a single item set resolves
  on both a nested route and a differently-named detail route.

- **The complex case.** For anything `kwarg_name` cannot express, set
  `url_kwargs_from_request(resolver_match) -> dict`. Its signature is
  **resolver-match-only**: it receives `request.resolver_match`, reads
  `.kwargs` / `.url_name`, and returns the kwargs to reverse with. When both are
  set, `url_kwargs_from_request` wins.

  ```python
  def project_kwargs(resolver_match):
      slug = resolver_match.kwargs.get("project_slug") or resolver_match.kwargs.get("slug")
      return {"project_slug": slug} if slug else {}

  NavItem(label="Documents", url_name="project-documents",
          url_kwargs_from_request=project_kwargs)
  ```

## 3. The context processor (the sharp edge, brickwork#22)

The shell reads its `<html>` axis attributes from the context variables
`bw_theme` / `bw_density` / `bw_dir` / `bw_lang` / `bw_brand` / `bw_page_title`.
The theme service, `resolve_theme_attributes`, returns a dict keyed
`{theme, density, dir, brand, logo}` which **does not** match those `bw_*` names
and carries no language. Dropping the service output straight into context gives
you a silently unstyled shell.

Do not hand-map it. Add the shipped processor and the mapping is done for you:

```python
"context_processors": [
    # ...
    "brickwork.context_processors.theme",
],
```

It sets `bw_theme` / `bw_density` / `bw_dir` (from `resolve_theme_attributes`,
honouring `BRICKWORK_THEME_RESOLVER` if set), `bw_lang` (from Django's active
language, so `<html lang>` follows `LocaleMiddleware` / `i18n_patterns` with no
extra wiring), plus `bw_logo` / `bw_brand` when the resolver supplies them. It
does **not** set `bw_page_title`; that stays view-owned (set it per view).

To drive theme / density / direction / brand per user or per tenant, point
`BRICKWORK_THEME_RESOLVER` at a dotted path to a
`Callable[[HttpRequest], ThemeAttributes]`; the processor imports and applies it.
Per-request density and RTL, and per-tenant runtime brand-token injection, are
worked recipes in [BRANDING.md](BRANDING.md#dynamic-theming) (brickwork#36).

## 4. A worked HTMX 422 form, end to end (brickwork#24)

brickwork ships the field renderer (`forms/_field.html`), the per-field error
container (`id="{{ field.auto_id }}_errors"`, `role="alert"`), and the
`is_htmx_validation_request(request)` helper. It does **not** ship the swap
wiring: the form-level `hx-post` / `hx-target` / `hx-swap`, the stable
swappable-region id, and the partial re-rendered on 422 are yours to own. Here is
the whole loop so you do not reverse-engineer it. The no-JS full-page POST is the
floor and must keep working (BR-BW-HTMX-001).

**Factor the form region into a shared partial** so the full-page render and the
422 re-render reuse identical markup (no duplication):

```django
{# yourapp/partials/_project_form_region.html #}
<form id="project-form" method="post"
      hx-post="{{ request.path }}"
      hx-target="this"
      hx-swap="outerHTML">
  {% csrf_token %}
  {% for field in form %}
    {% include "brickwork/forms/_field.html" with field=field %}
  {% endfor %}
  {% bw_button label="Save" type="submit" variant="primary" %}
</form>
```

**The full page includes that partial:**

```django
{# yourapp/project_form.html #}
{% extends "brickwork/shell/app.html" %}
{% block content %}
  <h1 class="bw-page-header__title">Edit project</h1>
  {% include "yourapp/partials/_project_form_region.html" %}
{% endblock %}
```

**The view branches in `form_invalid`** on `is_htmx_validation_request`: 422 +
the partial for an htmx submission (the targeted `outerHTML` swap re-renders just
the form region with its errors), a normal 200 full page otherwise (the no-JS
floor). Valid submissions redirect (302) as always:

```python
from brickwork.services.forms import is_htmx_validation_request

class ProjectUpdateView(UpdateView):
    template_name = "yourapp/project_form.html"

    def form_invalid(self, form):
        if is_htmx_validation_request(self.request):
            return render(
                self.request,
                "yourapp/partials/_project_form_region.html",
                {"form": form},
                status=422,
            )
        return super().form_invalid(form)  # 200, full page
```

That is the complete contract: htmx invalid returns 422 and swaps the region,
non-htmx invalid returns a working 200 full page, valid returns 302.
`is_htmx_validation_request` currently delegates to `is_htmx_request` (the
`HX-Request` header, or a duck-typed `request.htmx` when you run django-htmx);
what stays yours is everything above: the shared partial, the `hx-*` attributes,
the region id, and the branch. See section 6 for the htmx version floor.

## 5. A JS-bearing page: the chrome/body boundary and asset coexistence (brickwork#33)

For any page that mounts a chart, a rich editor, or other app-owned JavaScript,
the boundary is simple and firm: **brickwork owns the chrome (shell, nav, topbar,
footer); you own everything inside `{% block content %}`.** brickwork does not
mount data-viz; charts are a declared non-goal. Mount your component inside the
content block against a plain element you control:

```django
{% extends "brickwork/shell/app.html" %}
{% block content %}
  <div class="bw-card">
    <div id="revenue-chart" data-series="{{ series_json }}"></div>
  </div>
{% endblock %}
{% block body_js %}
  {{ block.super }}
  <script type="module" src="{% static 'yourapp/charts.js' %}"></script>
{% endblock %}
```

**Asset-pipeline coexistence.** brickwork ships its own assets through plain
`{% static %}`. Your app can run a separate bundler (django-vite with hashed
bundles, an esbuild step, whatever) alongside it with no conflict: brickwork
never touches your pipeline and does not expect to be inside it. Load your
bundle from the shell's `body_js` block (or `head_extra` for stylesheets) and the two
coexist. This works but is not obvious, so: expect it to work, and do not try to
route brickwork's static through your bundler.

If you run Alpine yourself (host-owned `Alpine.start()`), brickwork's interaction
components register against your Alpine instance; do not start Alpine twice.

## 6. The htmx version floor (brickwork#48)

brickwork's interaction contracts (the 422 form swap, toast delivery via
`hx-swap-oob`, modal dismissal via the `HX-Trigger: bw:modal:close` response
header, combobox server filtering) are built and CI-gated on **htmx >= 2.0**
only. That is the declared floor (BR-BW-HTMX-010): htmx 1.9 is out of contract.
htmx 2 changed default response handling in ways the 422 loop relies on; on 1.x
a consumer would have to wire `htmx:beforeSwap` by hand, and brickwork does not
test that path.

A brownfield app on htmx 1.9 should treat the htmx 1 -> 2 upgrade as a
prerequisite workstream before the brickwork cutover, not something to reconcile
mid-migration. See [ADOPTION.md](ADOPTION.md) for sequencing.

## 7. Icons: bulk-registering a project set (brickwork#49)

`{% bw_icon %}` renders from a name registry seeded with canonical Lucide names.
To vendor your own project set (your app carries more glyphs than the seed, or
its own names), register them in bulk at app-ready time with `register_icons`:

```python
# yourapp/apps.py
from django.apps import AppConfig

class YourAppConfig(AppConfig):
    name = "yourapp"

    def ready(self):
        from brickwork.icons.registry import register_icons
        register_icons(
            {
                "invoice": '<svg viewBox="0 0 24 24">...</svg>',
                "shipment": '<svg viewBox="0 0 24 24">...</svg>',
            },
            # names whose glyph should mirror under dir="rtl":
            directional=("shipment",),
        )
```

`register_icons(mapping, *, directional=())` takes a `{name: svg_markup}` dict
and merges it into the registry; `directional` lists names that should flip under
RTL. Registering once at `ready()` makes every name available to `{% bw_icon %}`
across your templates.

Every `{% bw_icon %}` call must pass exactly one of `decorative=True` (the glyph
is purely decorative, hidden from assistive tech) or `label="..."` (a
non-decorative glyph, given an accessible name). Omitting both, or passing both,
raises `TemplateSyntaxError` by design (WCAG enforcement). `bw_button` / `bw_nav`
handle this internally; you only supply it when reaching for `{% bw_icon %}`
directly in a page template.

## 8. The marketing header: auth-aware actions (brickwork#85)

A real marketing site's header changes with auth state: anonymous visitors
see "Sign in / Get started", logged-in users see "Dashboard / Log out". The
marketing shell (`brickwork_marketing/shell/marketing.html`, opt-in via the
`brickwork.marketing` sub-app) deliberately ships no logged-in default:
brickwork never reads auth state itself (state is host-injected, the same
responsibility model as the app nav's `visible_items` gating), so the
supported pattern is your page branching the `marketing_actions` block on
`request.user.is_authenticated`.

Prerequisite: `django.template.context_processors.request` in your
`TEMPLATES` options (a Django default; section 1 keeps it), so `request` is
in template context.

```django
{% extends "brickwork_marketing/shell/marketing.html" %}
{% load brickwork_components %}

{% block marketing_nav %}
  <a href="{% url 'features' %}">Features</a>
  <a href="{% url 'pricing' %}">Pricing</a>
  <a href="{% url 'about' %}">About</a>
{% endblock %}

{% block marketing_actions %}
  {% if request.user.is_authenticated %}
    <a href="{% url 'dashboard' %}">Dashboard</a>
    <form method="post" action="{% url 'logout' %}">
      {% csrf_token %}
      {% bw_button "Log out" type="submit" variant="secondary" %}
    </form>
  {% else %}
    <a href="{% url 'login' %}">Sign in</a>
    {% bw_button "Get started" variant="primary" href="/signup/" %}
  {% endif %}
{% endblock %}
```

Notes on the shape:

- **Log out is a POST form**, not a link: Django's `LogoutView` rejects GET
  (since Django 5.0), so the authed branch carries a one-button form with
  `{% csrf_token %}`, styled through `{% bw_button type="submit" %}`.
- **A bare `<a>` in either slot is styled for you** (label voice, muted ink
  with a hover transition, never UA default blue), so plain links clear the
  marketing kit's contrast gate in both themes; reach for `{% bw_button %}`
  only where you want CTA weight.
- **Put this branch in your own base marketing page** (the one your
  landing/pricing/about pages extend), so the header is auth-aware
  everywhere without repeating the block.
- brickwork's *app* nav has a richer mechanism for the same need
  (`NavItem` with `required_permissions` / `visibility_policy`, filtered by
  `visible_items`); the marketing header is a small fixed set of links, so
  the plain template branch above is the supported marketing-shell shape.

## Contribute back

If a seam here was thin for your integration, or you hit a paper-cut this guide
did not cover, that is a docs issue worth filing on `icvoss/django-brickwork`.
The pilots that produced this guide filed exactly those findings, which is why
the walkthrough exists.
