# Branding brickwork: theming a consuming app token-first

brickwork's whole point is that you rebrand it by overriding `--bw-*` tokens, not
by reaching into its component classes. This guide covers how to bridge a real
brand onto the token layer: colour, typography, and the four axes (theme,
density, direction). Since 0.3.0, base-theme (the beautiful default values every
brand inherits from) derives its fine colour tokens live from a small
load-bearing set, so a brand is a handful of authored values, not a full
palette. [DESIGN.md](DESIGN.md) is the authoritative token reference (every
name, default value, and derivation rule); this guide covers the how.

## The mechanism: override tokens, don't touch classes

Put your brand's values on `:root` (or a scoped ancestor) in your own stylesheet,
loaded AFTER brickwork's `tokens.css`. Override only the semantic and component
tiers (`--bw-color-*`, `--bw-font-*`), never the primitives.

```css
/* your brand.css, loaded after brickwork's tokens.css */
:root {
  --bw-color-accent: oklch(0.55 0.2 265);   /* your brand blue */
  --bw-font-family-sans: "Inter", system-ui, sans-serif;
  --bw-font-family-display: "Poppins", var(--bw-font-family-sans);
  --bw-font-family-mono: "JetBrains Mono", ui-monospace, monospace;
}
```

Because the derived tokens are live `color-mix()` expressions over the
load-bearing set, overriding `--bw-color-accent` alone recolours the whole
accent family (hover, subtle tint, focus ring, nav active state) in the
browser, with no rebuild.

## The load-bearing minimum: seven tokens make a brand

base-theme derives everything else from seven load-bearing colour tokens per
theme (DESIGN.md section 2 is the authoritative list):

1. `--bw-color-surface` (the paper)
2. `--bw-color-fg` (the ink)
3. `--bw-color-border`
4. `--bw-color-accent`
5. `--bw-color-danger`
6. `--bw-color-success`
7. `--bw-color-warning`

Plus, conditionally, `--bw-color-surface-inverse` when your ink is not the
inverse surface (it defaults to `fg`). Two more are authored rather than
derived where a formula cannot make the call for you: `--bw-color-fg-on-accent`
(verify at 4.5:1) and, for a three-role brand,
`--bw-color-info: var(--bw-color-accent)` collapses info onto the accent in one
line (base-theme ships a distinct cyan by default).

A complete light plus dark brand is about fourteen lines:

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

That is the whole brand: base-theme derives the hover shades, subtle tints,
muted foregrounds, status tiers, and component roles from these values.

## The fg-on-accent trap: do not assume white (brickwork#35)

`--bw-color-fg-on-accent` is the text colour that sits **on** the accent (button
labels, active nav text, badges). It is authored per theme, not derived, because
base-theme cannot infer contrast for you. The trap: the safe text colour *flips*
depending on the accent's lightness, and a brand whose *dark*-theme accent is a
*light* colour is a common case that inverts the intuition. "White on accent" is
not a safe default.

Worked failure, from a real pilot: a brand ran a light theme with a deep
aubergine accent and a dark theme whose accent was a light pink. White
`fg-on-accent` in *both* was the reflex, and it was wrong in dark. For the
example oklch values below (ratios are what `render_brand_css`'s own contrast
check reports, so the doc and the emitter agree):

| theme | accent | white `fg-on-accent` | dark ink `fg-on-accent` | correct value |
|---|---|---|---|---|
| light | deep aubergine | 8.72:1 (pass) | 1.84:1 (fail) | **white** |
| dark | light pink | 1.52:1 (fail) | 10.55:1 (pass) | **dark ink** |

So the *same* token needs *opposite* values in the two themes. Author it per
theme and verify each at 4.5:1 against its own accent:

```css
:root {
  --bw-color-accent:        oklch(0.42 0.11 330);   /* deep aubergine */
  --bw-color-fg-on-accent:  oklch(0.99 0 0);        /* white: 8.72:1, passes */
}
[data-theme="dark"] {
  --bw-color-accent:        oklch(0.86 0.06 350);   /* light pink */
  --bw-color-fg-on-accent:  oklch(0.24 0.02 330);   /* dark ink: 10.55:1, passes
                                                        (white here is 1.52:1) */
}
```

This is the single most likely token for a distinct-brand consumer to ship
broken, precisely because it is the one the derivation cannot catch for you.
Measure both themes; never copy the light value into dark on reflex.

## Typography (the `--bw-font-*` tokens)

The shell and components consume `--bw-font-family-sans` (body) and
`--bw-font-family-display` (headings), plus a size/weight/line-height scale
(`--bw-font-size-*`, `--bw-font-weight-*`, `--bw-font-line-height-*`). Override
the family tokens to give brickwork your typeface without touching `.bw-body` or
`.bw-page-header__title`. The default is a neutral system-font stack so an
unbranded install still looks intentional.

## Colour: what base-theme now derives for you

brickwork's semantic vocabulary is intentionally richer than a minimal brand
(a surface scale, five tiers per status hue, state overlays). Before 0.3.0 a
lean brand had to hand-tune all of it; base-theme now derives it from the
load-bearing set:

| brickwork tokens | how base-theme derives them |
|---|---|
| the surface scale (`-sunken` / `-raised` / `-overlay`) | derived from `surface`: sunken mixes a touch darker, raised differentiates by shadow in light and by lightness in dark, overlay is a scrim over content. The depth cues the components rely on come for free. |
| `--bw-color-surface-inverse` | defaults to `var(--bw-color-fg)` (your ink), used for inverted chips/badges. Author it only when your ink is not the inverse surface. |
| the muted foregrounds (`-fg-muted`, `-fg-subtle`, `-icon-muted`) | mixed from `fg` toward `surface`, with theme-tuned constants. |
| `-accent-hover` and `-accent-subtle` | shaded and tinted from `accent`. |
| `--bw-color-focus-ring` | base theme derives a default from `accent`; `render_brand_css()` emits a separately verified OKLCH value for every tenant accent override. |
| the status tiers (`X-subtle`, `X-strong`, `X-fg` for danger/success/warning/info) | derived per intent hue, so an alert, badge, or toast never invents a value. |

Hand-tuning the derived families is the override path, not the primary path: a
flat value you set wins over the derivation through the CSS cascade. The focus
ring is the accessibility exception: do not override it through
`render_brand_css()`. Supply concrete `oklch()` values for an accent and any
surface it changes, and the service emits the verified ring value. The full
derivation table, with the exact `color-mix()` constants per theme, is
DESIGN.md section 4.

Rule of thumb: let tokens that are shades of the same idea derive (the surface
scale, the tint tiers); avoid collapsing tokens that carry distinct *meaning*
(the status hues), because the components use them as semantic signals, not
decoration. Almost every brand has a red and a green intent even if not in the
logo palette; author them rather than reusing the accent, so destructive and
positive actions read correctly.

## The four axes

- **Theme (`data-theme="light|dark"`)** is the required dark-mode mechanism, and
  it is deliberate. brickwork's *load-bearing* dark values are authored, not
  derived (BR-BW-TOK-002): dark is never computed from light, so dark mode is a
  designed surface, not an inverted one. Within a theme, the fine tokens derive
  from that theme's load-bearing set with dark-tuned constants, and a brand may
  override any of them, derived or authored. That authored-per-brand model, and
  the way theme composes independently with density and direction, needs an
  attribute the CSS can switch on; a `prefers-color-scheme`-only approach cannot
  express an authored dark palette that also composes with the other axes.

  **If your app drives dark mode with `prefers-color-scheme` or a Tailwind
  `dark:` class**, bridge it to `data-theme` with a few lines rather than
  fighting it:

  ```css
  /* follow the OS preference, still using brickwork's authored dark values */
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme]) { /* only when the app hasn't set an explicit theme */
      /* re-point the semantic colours at brickwork's dark block, or simply: */
    }
  }
  ```
  ```html
  <!-- or, the simplest bridge: set the attribute from your existing signal -->
  <html data-theme="{{ 'dark' if user_prefers_dark else 'light' }}">
  ```

  A one-line server-side or JS bridge from your existing dark signal to
  `data-theme` keeps brickwork's authored dark palette while honouring the user's
  preference. This is the recommended path; `data-theme` stays the contract.

- **Density (`data-density="compact|comfortable|spacious"`)** scales spacing only,
  never colour. Set it on `<html>` (or per-region) from a user preference.

- **Direction (`dir="ltr|rtl"`)** is handled by logical CSS properties
  throughout; set the `dir` attribute and the browser resolves the rest. No token
  or stylesheet swap.

<h2 id="dynamic-theming">Dynamic theming: per-request axes and per-tenant runtime brand (brickwork#36)</h2>

The four axes and the live oklab derivation are not just build-time knobs; both
can be driven per request. Three recipes unlock capabilities the token
architecture already supports.

### Recipe 1: per-user density / theme / direction toggle

Thread a per-user (or per-request) theme, density, and direction through a
`theme_resolver` and the shipped context processor maps them onto the `bw_*`
shell vars for you. Point `BRICKWORK_THEME_RESOLVER` at a dotted path:

```python
# yourapp/theming.py
def theme_resolver(request):
    """Return a partial ThemeAttributes dict; only the keys you set are applied."""
    prefs = getattr(request.user, "ui_prefs", None)
    if prefs is None:
        return {}
    return {
        "theme": prefs.theme,       # "light" | "dark"
        "density": prefs.density,   # "compact" | "comfortable" | "spacious"
        "dir": prefs.direction,     # "ltr" | "rtl"
    }
```

```python
# settings.py
BRICKWORK_THEME_RESOLVER = "yourapp.theming.theme_resolver"
```

A partial dict is fine: only the keys you return override the defaults. With
`brickwork.context_processors.theme` installed (see
[INTEGRATION.md](INTEGRATION.md) section 3), the resolved attributes land on the
shell's `<html>` element and the user's preference is live per request, with no
rebuild and no per-user stylesheet. Density scales spacing only; direction is
resolved by logical CSS properties; theme swaps to brickwork's authored dark
values.

### Recipe 2: per-tenant runtime brand-token injection (the multi-tenant prize)

Because the derived colour family is live `color-mix()` over the ~7 load-bearing
tokens, a multi-tenant SaaS can inject *one tenant's* load-bearing set per request
and the whole family recolours in-browser, no per-tenant build. The supported
primitive is the emitter service (brickwork#40, shipped 0.11.0):

```python
from brickwork.services.tokens import render_brand_css

def tenant_brand_style(request):
    tenant = request.tenant
    css = render_brand_css(
        light={
            "color-surface": tenant.surface,
            "color-fg": tenant.fg,
            "color-border": tenant.border,
            "color-accent": tenant.accent,
            "color-danger": tenant.danger,
            "color-success": tenant.success,
            "color-warning": tenant.warning,
            "color-fg-on-accent": tenant.fg_on_accent,
        },
        dark=tenant.dark_tokens or None,   # optional; omit for light-only brands
        validate=True,                     # reject unknown names, check fg-on-accent
    )
    return css  # a ready :root { ... } [data-theme="dark"] { ... } block
```

Emit that block in a per-request `<style>` in the shell head (after
`brickwork.css`), keyed by the current tenant:

```django
{% block head_extra %}
  {{ block.super }}
  <style>{{ tenant_brand_css }}</style>
{% endblock %}
```

`render_brand_css(light, dark=None, *, validate=True) -> str` takes override
values keyed by token name, rejects unknown names against the shipped vocabulary,
optionally runs the authored-value checks brickwork already states as rules
(fg-on-accent at 4.5:1; a warning when a status hue collapses onto the accent),
and emits the `:root` / `[data-theme="dark"]` blocks in the documented override
shape. It validates against the machine-readable load-bearing manifest
(brickwork#39), so you never hand-keep a second list of token names that semver
could move. Do not hand-build the CSS string yourself; this is the token contract
expressed as an API.

If you cannot yet adopt the emitter, the inline fallback is the same `<style>`
block hand-written against the load-bearing names in this document, but you then
own validation and drift against the token contract. Prefer the service.

### Recipe 3: per-role accent within one session (brickwork#76)

First, the contract, stated so it is a guarantee and not an accident:
**`BRICKWORK_THEME_RESOLVER` may derive its result from ANY request state.**
The resolver is a `Callable[[HttpRequest], ThemeAttributes]` and nothing in the
resolution path privileges tenant or host: session values, an active role a
middleware resolved onto the request, the user, the host, a tenant, all are
equally supported keys. A per-request, session-keyed resolution that flips
within one authenticated user's browsing (the user switches role mid-session)
is a supported path, exercised by the brickwork test suite.

The shape this recipe covers: a single-brand product whose application accent
changes by the user's **active role** (say player / coach / club / supplier),
switchable mid-session. The role accent is information architecture (it tells
the user which hat they are wearing), so it must flip per request with no
tenant or host involved.

When the N accents are known at build time, the lightest wiring is the brand
axis plus a static stylesheet; no per-request CSS emission at all. The resolver
keys the brand slug on the role:

```python
# yourapp/theming.py
def role_accent_resolver(request):
    role = getattr(request, "active_role", None)  # your middleware sets this from the session
    if role is None:
        return {}
    return {"brand": role}  # "player" | "coach" | "club" | "supplier"
```

```python
# settings.py
BRICKWORK_THEME_RESOLVER = "yourapp.theming.role_accent_resolver"
```

The slug renders as `data-bw-brand` on the shell root `<html>` (0.10.0 brand
hook), so your brand stylesheet scopes one accent block per role. The overrides
sit on the root element, which is where the derived `color-mix()` family
computes, so overriding `--bw-color-accent` alone recolours the whole accent
family (hover, subtle tint, focus ring, nav active state) for that role,
per request, with no rebuild:

```css
/* your brand.css, loaded after brickwork's tokens.css */
[data-bw-brand="player"] {
  --bw-color-accent:       oklch(0.55 0.17 255);
  --bw-color-fg-on-accent: oklch(0.99 0 0);      /* verified against THIS accent */
}
[data-bw-brand="player"][data-theme="dark"] {
  --bw-color-accent:       oklch(0.72 0.13 255);
  --bw-color-fg-on-accent: oklch(0.22 0.02 255); /* the flip trap, per role */
}
[data-bw-brand="coach"] {
  --bw-color-accent:       oklch(0.50 0.14 150);
  --bw-color-fg-on-accent: oklch(0.99 0 0);
}
[data-bw-brand="coach"][data-theme="dark"] {
  --bw-color-accent:       oklch(0.70 0.12 150);
  --bw-color-fg-on-accent: oklch(0.20 0.03 150);
}
/* ...club, supplier... */
```

Points to hold:

- **fg-on-accent is a per-accent decision.** Four roles times two themes is
  eight authored `--bw-color-fg-on-accent` values, each verified at 4.5:1
  against its own accent (the brickwork#35 trap applied per accent). Do not
  copy white across roles or from light into dark on reflex.
- **Dark composes per role.** `data-bw-brand` and `data-theme` are independent
  attributes on the same root element, so the compound
  `[data-bw-brand="coach"][data-theme="dark"]` block gives every role its own
  authored dark accent, and player-dark, coach-dark and so on all derive their
  families correctly. Author the compound block after the role's light block;
  its higher specificity is what keeps the role's light values out of dark.
- **Theme and density still compose.** The role only sets `brand`; the user's
  theme / density / direction preferences resolve exactly as in recipe 1, in
  the same resolver or a chained one (return the merged dict).

When the accents are data rather than code (roles configured per deployment,
say), swap the static stylesheet for the recipe 2 emitter keyed on the role
instead of the tenant: `render_brand_css` validates each role's
fg-on-accent pairing per theme, and the per-request `<style>` block carries
only that role's load-bearing values. Either way the derivation guarantee is
the same, and it is pinned by tests: the shipped stylesheet keeps the accent
family (`-accent-hover`, `-accent-subtle`) derived live over
`var(--bw-color-accent)` in every theme scope. `render_brand_css()` adds a
verified `-focus-ring` value for per-request accents, so focus visibility does
not depend on an unmeasured browser-side mix.

## A live, on-page axis switch (brickwork#117)

The four axes are runtime attributes on the shell root `<html>`, and the live
`color-mix()` derivation means switching any of them re-themes the page
instantly with no rebuild. `{% bw_theme_switch %}` is the shipped, tested
control that demonstrates that property, so you do not hand-roll the a11y
semantics (a fieldset of radios, not buttons; each axis in its own labelled
group; no focus trap) and get some of them wrong.

```django
{% load brickwork_theming %}
{% bw_theme_switch %}
```

Renders one `<fieldset>` per axis (default `axes="theme density dir"`;
`brand` is opt-in, see below), each a native, individually labelled radio
group, wired to `bwThemeSwitch` (`registerBrickworkComponents`, same as every
other interaction). Options (ADR-060 grammar):

- `axes` (str, default `"theme density dir"`): a space-separated,
  closed-vocabulary subset of `theme`/`density`/`dir`/`brand`. `brand` is
  never included by default: `data-bw-brand` only means something once you
  have authored a `[data-bw-brand="..."]` stylesheet block (Recipe 3 above),
  so offering it unconditionally would render a control that does nothing on
  most sites.
- `brands` (mapping, required when `"brand"` is in `axes`): `{slug: label}`
  for your own `data-bw-brand` values; brickwork ships no brand slugs of its
  own to offer. Every key is validated server-side against the same
  attribute-safe slug rule `BRICKWORK_DEFAULT_BRAND` and a resolver's own
  `brand` key already follow; a bad slug is a loud `TemplateSyntaxError`.
- `label` (str, optional): the control's own accessible name; defaults to a
  translated "Display settings".
- `locked_axes` (str, optional): which axes render as a disabled, read-only
  radio group. Defaults to `bw_theme_locked_axes` from the template context
  (set by `brickwork.context_processors.theme`) when omitted, so the bare
  `{% bw_theme_switch %}` call above is safe by default on a resolver-backed
  page; you do not pass this by hand in ordinary use. Pass a string
  explicitly (including `""`) to override the context value entirely rather
  than merging with it.
- `layout` (str, default `"inline"`): `"inline"` | `"compact"`
  (icvoss/django-brickwork#235). `"inline"` is the render shown above,
  unchanged. `"compact"` wraps the same fieldsets in a native
  `<details>/<summary>` disclosure, for a header actions cluster too narrow
  for the full inline control.
- `placement` (str, default `"end"`): `"start"` | `"end"`, only meaningful
  with `layout="compact"` (it anchors the compact panel to the trigger's
  start or end edge, the same vocabulary `bw_dropdown`/`bw_account_menu`
  already use). Passing it with `layout="inline"` raises
  `TemplateSyntaxError`: inline has no panel to anchor, and this package has
  no precedent for a silently-ignored, inapplicable option.

**`layout="compact"` for a header actions cluster:**

```django
{% load brickwork_theming %}
{% bw_theme_switch layout="compact" placement="end" %}
```

This is a native WAI-ARIA APG **Disclosure**, not a menu, deliberately with
**no ARIA menu roles anywhere** (the same doctrine `bw_account_menu`'s own
`<details>/<summary>` recipe uses): `role="menu"` mandates arrow-key
handling this control never provides, so a hand-authored `role="menu"`/
`aria-haspopup`/`aria-expanded` would promise behaviour that is not there.
Native `<details>/<summary>` already carries the correct semantics (Tab to
the summary, Enter/Space toggles) with nothing extra needed. Once
`bwThemeSwitch` has run, the panel gains three dismissal routes: the summary
toggle, Escape (focus returns to the trigger), and a click or tap outside
it. Selecting a radio never closes the panel: unlike a command menu, you may
want to flip more than one axis in a single visit. Every compact option
clears the 44px touch-target floor (`--bw-size-touch-target-min`, the same
label-extension route brickwork's other compact controls use); no other
markup or behaviour differs from the inline render, including validation,
persistence, and locking.

**The no-JS floor here is "render nothing", not "render a working control",
the one deliberate departure from this package's usual doctrine.** The
server-rendered page is already correctly themed, so a theme switch with no
JS is a control that visibly does nothing, worse than absent: the fieldset
ships with the `hidden` attribute and `bwThemeSwitch` removes it at init,
mirroring the reveal-at-init shape `bw_alert`'s dismiss button already uses.

**Persistence follows SHL-003** (the same rule
`frontend/src/js/sidebar_collapse.js` documents for the sidebar): localStorage
is the switch's own DEFAULT persistence, itself overridable by the host. Per
axis, not globally:

| Case | Behaviour |
|---|---|
| No `theme_resolver` configured, or it returns nothing for this axis | A free client toggle, persisted to `localStorage` |
| The resolver's own return value asserts this axis this request | The axis renders as a disabled, read-only radio group showing the current server-resolved value; a client default must never clobber a real preference |

The context processor computes this automatically: `bw_theme_locked_axes`
(from `brickwork.context_processors.theme`) is the space-separated set of
axes your `BRICKWORK_THEME_RESOLVER` itself asserted, and `{% bw_theme_switch %}`
reads it from the template context itself, so the bare
`{% bw_theme_switch %}` call above is safe by default on a resolver-backed
page: you never pass `locked_axes=` by hand in ordinary use. Locking is by
KEY PRESENCE, not truthiness: a resolver that returns `{"brand": ""}` to
deliberately clear the brand still locks the brand axis, so a stale
`localStorage` value can never resurface a brand the resolver just cleared.

Every value this control is about to apply or persist, whether restored
from `localStorage`, read from `<html>`'s own current attribute, or read
from a radio at change time, is checked against a closed set the SERVER
emits per instance (a `json_script` payload alongside the control, never
the rendered radios themselves, so a mistaken override template rendering a
wrong or extra `<input>` cannot widen what the client accepts); a value
that fails is discarded rather than applied, a bad stored entry is removed
rather than left to fail again on the next load, and an unrecognised
`<html>` attribute is treated as absent rather than adopted.

A locked axis resolves its OWN current value server-side too (from the same
context variables the shell itself reads to write `<html>`), never from
`<html>` at JS runtime: with more than one switch instance on a page
sharing an axis (an ordinary pattern, not a misuse), an earlier-initialising
unlocked sibling can already have changed `<html>` by the time a locked
instance's own init runs, and reading the live attribute at that point would
be order-dependent. A locked group still discards a genuinely INVALID
stored entry (the same closed-set check), but leaves a VALID one alone,
since it may legitimately belong to an unlocked sibling instance sharing
that axis.

**Two accepted trade-offs, stated rather than left silent:**

- **No cross-tab live sync.** Changing an axis in one open tab does not
  update a theme switch rendered in another open tab of the same site; the
  other tab's control still reflects whatever it read at its own init, and
  only catches up on its own next navigation. This matches
  `frontend/src/js/sidebar_collapse.js`'s existing persistence pattern,
  which makes the same choice, and no brickwork interaction currently
  synchronises live across tabs. If you need it, add your own
  `window.addEventListener("storage", ...)` bridge that re-reads the
  changed key and re-applies it to `<html>`.
- **A returning visitor with a stored preference sees one flash.** The
  server renders the page with its own resolved theme; `bwThemeSwitch`
  applies a stored preference that differs from it at Alpine `init()`, which
  runs after first paint, so the page can flip once, briefly, on load. A
  genuinely flash-free restore needs a synchronous script in `<head>`,
  before any CSS paints, which is a different mechanism to the switch itself
  (the control's own markup can render anywhere in `content`, not
  necessarily `<head>`) and carries its own CSP cost (an un-nonced inline
  script, the same trade-off the shell's DEBUG-only registration detector
  already documents in `shell/base.html`). brickwork does not ship that
  script, deliberately: most consumers land here via the server-resolved
  theme (SHL-003's whole point), so the flash is the rarer path (a returning
  visitor whose stored preference disagrees with the server default), not
  the common one. A consumer who needs a zero-flash restore adds a small
  synchronous script to the shell's `head_js` block, reading the same
  `localStorage` keys (`bw-theme-switch-<axis>`) this control writes and
  setting the `<html>` attribute before the stylesheet paints:

  ```django
  {% block head_js %}
    {{ block.super }}
    <script>
      (function () {
        try {
          {# A locked axis's value is the server's own, never a stale client one: #}
          {# skip it here exactly as bwThemeSwitch itself does, or a stored value #}
          {# from BEFORE this axis became locked would silently override a real #}
          {# resolver-asserted preference for the rest of the page's first paint. #}
          {% if "theme" not in bw_theme_locked_axes.split %}
          var theme = localStorage.getItem("bw-theme-switch-theme");
          if (theme === "light" || theme === "dark") {
            document.documentElement.setAttribute("data-theme", theme);
          }
          {% endif %}
        } catch (e) {}
      })();
    </script>
  {% endblock %}
  ```

  Validate against the closed vocabulary inline exactly as shown (never
  apply an unchecked stored value to `<html>`), and skip any axis your
  `bw_theme_locked_axes` names, or the recipe restores a stale client value
  OVER a resolver-locked one (server dark, stored light) and the lock then
  preserves the wrong value for the rest of the page: a documented recipe
  must not contradict the shipped component's own safety rule on the same
  page. Repeat the `{% if %}` guard per axis you want flash-free. Add your
  CSP nonce as the registration detector's own override already documents.

### The recipe, if you want your own control

The same shape `{% bw_theme_switch %}` renders, for a consumer who wants
different markup or copy: a `<fieldset>` of radios per axis (never buttons: a
control with more than two states that are not "on"/"off" is a radio group,
not a toggle), each axis announced by its own `<legend>`, the whole control
`hidden` until JS reveals it (the same no-JS floor rule above), and
persistence written directly onto `<html>`. **A documented recipe may not
contradict the shipped component's own safety rules**, so this one validates
and respects a lock exactly as `bwThemeSwitch` does, not a simplified,
unvalidated version of it. This recipe teaches the inline shape, not every
nuance, and does not cover `layout="compact"`'s disclosure wrapper (Escape/
click-outside dismissal, focus return): `frontend/src/js/theme_switch.js` is
the complete reference implementation for the edge cases it omits (per-axis
storage cleanup among them):

```django
{% if "theme" in bw_theme_locked_axes.split %}
<fieldset hidden data-my-theme-switch data-locked>
  <legend>Theme</legend>
  <label><input type="radio" name="theme" value="{{ bw_theme }}" data-theme-value checked disabled></label>
  <p>Set by your account preferences.</p>
</fieldset>
{% else %}
<fieldset hidden data-my-theme-switch>
  <legend>Theme</legend>
  <label><input type="radio" name="theme" value="light" data-theme-value> Light</label>
  <label><input type="radio" name="theme" value="dark" data-theme-value> Dark</label>
</fieldset>
{% endif %}
```

```js
const STORAGE_KEY = "my-theme";
const root = document.querySelector("[data-my-theme-switch]");
const radios = root.querySelectorAll("[data-theme-value]");
// The intended closed vocabulary, stated inline, never derived from the
// rendered inputs: a set queried from your own radios would make any
// typo'd option value "valid" by being rendered, which is circular. This
// is the same "validate against a server-known set" rule bwThemeSwitch
// follows via its server-emitted JSON payload; a hand-rolled control on a
// page without the component states its allowlist here instead. For a
// brand axis, list your own registered brand slugs the same way.
const validValues = new Set(["light", "dark"]);
const isValid = (value) => validValues.has(value);

if (root.hasAttribute("data-locked")) {
  // A real server preference exists for this axis: never read or write
  // localStorage for it (the SHL-003 precedence rule), and the radio is
  // already checked/disabled server-side, so there is nothing more to do.
} else {
  const currentRaw = document.documentElement.getAttribute("data-theme") || "";
  const current = currentRaw && isValid(currentRaw) ? currentRaw : "";
  const storedRaw = localStorage.getItem(STORAGE_KEY);
  const stored = storedRaw !== null && isValid(storedRaw) ? storedRaw : null;
  if (storedRaw !== null && stored === null) localStorage.removeItem(STORAGE_KEY); // invalid entry: discard, don't keep failing
  const initial = stored ?? current;
  if (initial) document.documentElement.setAttribute("data-theme", initial);
  for (const radio of radios) {
    if (radio.value === initial) radio.checked = true;
    radio.addEventListener("change", () => {
      if (!radio.checked || !isValid(radio.value)) return; // a tampered .value is never applied or persisted
      document.documentElement.setAttribute("data-theme", radio.value);
      localStorage.setItem(STORAGE_KEY, radio.value);
    });
  }
}
root.removeAttribute("hidden");
```

Respect a server-resolved preference exactly as `{% bw_theme_switch %}` does:
if your own resolver asserts an axis this request, do not read or write
`localStorage` for it, and render that axis's own current value server-side
(never resolved from `<html>` at JS runtime: with more than one control on a
page sharing an axis, an earlier-initialising unlocked one could already
have changed `<html>` before a locked one's own script runs).

## The marketing brand slot: logo sizing out of the box (brickwork#83)

The marketing shell's `brand_logo` / `brand_wordmark` blocks are wrapped in
brickwork-owned elements (`.bw-marketing-header__brand-mark` /
`.bw-marketing-header__brand-wordmark`), and any `img`/`svg` dropped into
either slot is capped at `--bw-component-logo-height` (default `2rem`) with
width following the intrinsic ratio. Drop your mark or lockup straight into the
block and it renders at a sensible header size; an unconstrained SVG can no
longer render full-height and push the nav off-screen. A text wordmark is
unaffected (the cap targets only `img`/`svg`).

To resize, override the token once:

```css
:root {
  --bw-component-logo-height: 1.75rem; /* the 28px end of the header range */
}
```

The shell rule is zero-specificity (`:where`), so any one-class rule of your
own also wins if a single logo needs bespoke treatment.

## Where the values live

Author your overrides in your own stylesheet or, if you run a build, in a DTCG
override file merged into brickwork's token source. Either way you target
brickwork's own token names, never Radix/Open Props scale numbers
(BR-BW-TOK-006). [DESIGN.md](DESIGN.md) is the authoritative list of those
names; do not enumerate from memory.
