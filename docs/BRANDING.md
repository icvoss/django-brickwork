# Branding brickwork: theming a consuming app token-first

brickwork's whole point is that you rebrand it by overriding `--bw-*` tokens, not
by reaching into its component classes. This guide covers how to bridge a real
brand onto the token layer: colour, typography, and the four axes (theme,
density, direction). It answers the friction a lean brand hits when its palette
is smaller than brickwork's vocabulary.

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

## Typography (the `--bw-font-*` tokens)

The shell and components consume `--bw-font-family-sans` (body) and
`--bw-font-family-display` (headings), plus a size/weight/line-height scale
(`--bw-font-size-*`, `--bw-font-weight-*`, `--bw-font-line-height-*`). Override
the family tokens to give brickwork your typeface without touching `.bw-body` or
`.bw-page-header__title`. The default is a neutral system-font stack so an
unbranded install still looks intentional.

## Colour: bridging a lean palette onto the full vocabulary

brickwork's semantic vocabulary is intentionally richer than a minimal brand
(it has a four-step surface scale and dedicated status hues). If your brand is
leaner, collapse deliberately:

| brickwork token | if your brand has no equivalent |
|---|---|
| `--bw-color-surface` / `-sunken` / `-raised` | map `surface` to your paper; set `sunken` a touch darker and `raised` a touch lighter (even 2-3% L in oklch reads as depth). Collapsing all three to one flat value is legible but loses the elevation cues the components rely on. |
| `--bw-color-surface-inverse` | your ink/darkest, used for inverted chips/badges. |
| `--bw-color-warning` / `-info` | if you have only one "attention" hue, point both at it, but prefer distinct hues: warning and info carry different meaning and colour is the fastest signal. |
| `--bw-color-danger` / `-success` | almost every brand has a red and a green intent even if not in the logo palette; author them rather than reusing the brand accent, so destructive/positive actions read correctly. |

Rule of thumb: it is fine to collapse tokens that are shades of the same idea
(the surface scale); avoid collapsing tokens that carry distinct *meaning* (the
status hues), because the components use them as semantic signals, not decoration.

## The four axes

- **Theme (`data-theme="light|dark"`)** is the required dark-mode mechanism, and
  it is deliberate. brickwork's dark values are *authored, not derived*
  (BR-BW-TOK-002): every semantic colour has an explicit dark value, so dark mode
  is a designed surface, not an inverted one. That authored-per-brand model, and
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

## Where the values live

Author your overrides in your own stylesheet or, if you run a build, in a DTCG
override file merged into brickwork's token source. Either way you target
brickwork's own token names, never Radix/Open Props scale numbers (BR-BW-TOK-006).
