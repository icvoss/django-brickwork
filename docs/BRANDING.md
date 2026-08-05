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
| the accent family (`-accent-hover`, `-accent-subtle`, `-focus-ring`) | shaded and tinted from `accent`. |
| the status tiers (`X-subtle`, `X-strong`, `X-fg` for danger/success/warning/info) | derived per intent hue, so an alert, badge, or toast never invents a value. |

Hand-tuning any of these is now the override path, not the primary path: every
derived token remains individually overridable, and a flat value you set wins
over the derivation (it is plain CSS cascade). The full derivation table, with
the exact `color-mix()` constants per theme, is DESIGN.md section 4.

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
can be driven per request. Two recipes unlock capabilities the token
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
