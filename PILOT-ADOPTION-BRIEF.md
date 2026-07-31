# Pilot adoption brief: django-brickwork 0.3.0

Hand this to a Claude Code session working **inside the agentpm or consentics
repo** (not the brickwork repo). It is the same brief for both; a per-app section
at the end says what differs. The goal of this round is **adopt + test**: install
brickwork, render one real screen through its shell/nav/components, prove it works
in your app, and report what fits and what does not. This is a proving run that
feeds brickwork toward 1.0, not a full migration.

## What brickwork is (one paragraph)

`django-brickwork` is a brand-agnostic, app-facing UI substrate for
server-rendered Django (Tailwind 4 CSS-first, Alpine 3, HTMX 2, Django 6.0). It
ships an application shell (sidebar/topbar/workspace), a navigation system with a
`resolver_match`-based active-route resolver, an accessible form-field renderer
with a 422 HTMX validation contract, a component set (button/badge/alert/
data_table/page_header/empty_state/pagination/breadcrumbs/account_menu), a
name-referenced icon registry (`{% bw_icon %}`), and a `--bw-*` design-token
layer with authored dark mode, density, and RTL. Accessibility is a tested
guarantee (axe-core WCAG 2.2 AA in its CI). It is NOT a Django-admin skin; it is
for your hand-built views.

## Prerequisite (confirm before starting)

Your app must be on **Django 6.0** (brickwork's floor; it uses core
`{% partialdef %}` with no compat shim). Both pilots have upgraded; confirm your
`pyproject.toml` / requirements pin Django `>=6.0` before installing.

## Step 1 - install by name from the private index

brickwork is published to `pypi.icvoss.com` (private index, netrc auth). Add it to
your requirements the same way you install other `icv-*`/private packages:

```
django-brickwork==0.3.0
django-htmx>=1.28      # only if you want the optional [htmx] helper surface;
                       # brickwork's core inlines the HX-Request check without it
```

Install (uv or pip, from the private index as your repo already configures it),
then confirm: `python -c "import brickwork; print(brickwork.__version__)"` -> `0.3.0`.

## Step 2 - wire it in

```python
# settings
INSTALLED_APPS = [
    # ...
    "django_htmx",   # only if you added the extra
    "brickwork",     # for template + static-asset discovery
]
MIDDLEWARE = [ ... "django_htmx.middleware.HtmxMiddleware", ... ]  # if using htmx
```

- Ensure `django.contrib.staticfiles` is installed and `collectstatic` runs in
  your build: brickwork ships stable-named artefacts in
  `static/brickwork/dist/` (`brickwork.css`, `tokens.css`, `brickwork.js`,
  `tailwind-theme.css`, `tokens.js`), referenced via plain `{% static %}` (no
  django-vite needed). The shell links `brickwork.css` itself.
- Settings you can set (all optional, sensible defaults): `BRICKWORK_DEFAULT_THEME`
  (`"light"`), `BRICKWORK_DEFAULT_DENSITY` (`"comfortable"`),
  `BRICKWORK_DEFAULT_DIR` (`"ltr"`), `BRICKWORK_NAV_FALLBACK` (`"omit"`),
  `BRICKWORK_THEME_RESOLVER` (dotted path, for per-user/tenant theming).

Read the spec before wiring anything non-obvious:
`~/Projects/oss/docs/specs/django-brickwork/` (README = the five public-API
contracts; 04-interfaces.md = settings + Python API + template hierarchy;
02-business-rules.md = the BR-BW-* rules; the-wall.md = every flexibility answer).

## Step 3 - context processors: theme is shipped, nav is yours

Theme wiring is ready-made since 0.2.4: add brickwork's own processor and the
shell gets `bw_theme` / `bw_density` / `bw_dir` / `bw_lang` with no hand
mapping. Do NOT write your own theme mapping; that path produced a silently
unstyled shell (brickwork#22).

```python
# settings: TEMPLATES[...]["OPTIONS"]["context_processors"]
"context_processors": [
    # ...
    "brickwork.context_processors.theme",   # shipped: bw_theme/bw_density/bw_dir/bw_lang
    "apps.core.nav.nav",                    # yours: the nav processor below
],
```

For per-user or per-tenant theming, set `BRICKWORK_THEME_RESOLVER` to a dotted
path to a `Callable[[HttpRequest], ThemeAttributes]`; the shipped processor
imports and applies it.

Navigation stays consuming-project shape (your app owns the config and the
permission/feature checkers):

```python
# your app, e.g. apps/core/nav.py  (NOT shipped by brickwork)
from brickwork.models import NavContext, NavItem
from brickwork.services.navigation import (
    resolve_active_item,
    validate_nav_config,
    visible_items,
)

MAIN_NAV = (
    NavItem(key="dashboard", label=_("Dashboard"), url_name="dashboard", icon="home"),
    NavItem(key="things", label=_("Things"), url_name="things:list", icon="folder",
            required_permissions=("things.view_thing",)),
    NavItem(key="admin", label=_("Admin"), section_header=True, children=(
        NavItem(key="settings", label=_("Settings"), url_name="settings:index", icon="settings"),
    )),
)
validate_nav_config(MAIN_NAV)   # raises at import on a duplicate key

def nav(request):
    ctx = NavContext(
        request=request,
        permission_checker=request.user.has_perm,          # host-injected, never assumed
        feature_checker=lambda flag: flag in getattr(request, "features", set()),
    )
    items = visible_items(MAIN_NAV, ctx)
    return {
        "bw_nav_items": items,
        "bw_active_nav_item": resolve_active_item(items, request.resolver_match),
    }
```

## Step 4 - one real screen through the shell

Pick **one existing list-or-detail screen** in your app and re-render it through
the shell. Do not migrate everything; one screen is the proving unit.

```django
{% extends "brickwork/shell/app.html" %}
{% load brickwork_nav brickwork_components %}
{% block page_title %}Things{% endblock %}
{% block sidebar %}{% bw_nav items=bw_nav_items active=bw_active_nav_item %}{% endblock %}
{% block mobile_nav %}{% bw_nav items=bw_nav_items active=bw_active_nav_item %}{% endblock %}
{% block page_header %}{% include "brickwork/components/_page_header.html" with title="Things" %}{% endblock %}
{% block page_actions %}{% bw_button "New" href="/things/new/" icon="plus" variant="primary" %}{% endblock %}
{% block content %}
  {# your existing table, or brickwork's _data_table.html with columns/rows dicts #}
{% endblock %}
```

For a create/edit form, use `brickwork/forms/_field.html` per field and the 422
contract: form section as `hx-target="this" hx-swap="outerHTML"`, and in the view
`if is_htmx_validation_request(request): response.status_code = 422`. A non-HTMX
POST must still work as a full-page redisplay (this is the load-bearing test).

## What to test and report back

1. **It renders and works.** The shell renders, nav shows the right items with the
   correct active state, your screen is usable.
2. **Accessibility didn't regress.** Tab order sane, skip link present, focus
   visible. If you have axe/pa11y, run it on the brickwork'd screen.
3. **Token/brand fit.** Do the default `--bw-*` tokens look acceptable, or do you
   need brand overrides? Note which semantic tokens you'd want to override.
4. **Gaps and friction.** Anything the shell/nav/components could NOT express for
   your screen. Be specific: "I needed X and there was no block/arg/token for it."
   These are the most valuable output; they shape brickwork before 1.0.

**File findings as GitHub issues on `icvoss/django-brickwork`** (the package repo),
not on your app repo, cross-linked. A gap that blocks you is a brickwork issue;
an integration binding you own stays in your app.

## Per-app focus (this is where the two pilots differ)

- **consentics (JS-enabled lead):** you exercise the full contract surface,
  including the HTMX 422 form swap and (as they land) the interaction primitives.
  You are the real distinct brand, so pay special attention to the token/brand fit
  (point 3): try authoring brand overrides against the `--bw-color-*` semantic
  names and report the authoring experience. You are strangling a `c-` component
  kit and a `shell/base_app.html`; pick one screen off that shell first.

- **agentpm (no-JS floor):** you run **zero JavaScript** (Alpine present but never
  loaded; htmx a Python dep with no frontend use; every mutation a full-page
  POST -> redirect). Your job is to prove the **no-JS floor**: the shell must
  render and function with neither Alpine nor htmx loaded, the native `<details>`
  sidebar/drawer must work, forms must submit and redisplay errors on a full-page
  POST. Do NOT add JS to make something work; if it needs JS, that is a finding.

## Boundary reminder

You are working in your own app repo. Do not edit the brickwork package from your
session; if brickwork needs to change, that is a `icvoss/django-brickwork` issue.
Your app owns its data, permissions, business logic, and brand token values;
brickwork owns structure, presentation, and the interaction contracts.
