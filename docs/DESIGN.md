# brickwork design tokens: the complete reference

**Status:** canonical token reference for brickwork 0.3.0 (ADR-054 Phase a).
**Authority:** ADR-054 in the umbrella
(`oss/docs/adrs/ADR-054-brickwork-token-system-and-theme-layers.md`) governs
the decisions; the umbrella spec (`oss/docs/specs/django-brickwork/`) governs
the contract rules; this file is the per-token reference (names, default
values, derivation rules). Where this file and ADR-054 differ, ADR-054 wins,
except for the fallback-emission correction recorded in section 3, which
supersedes the ADR's stated mechanism for the reason given there.
**Companion:** [BRANDING.md](BRANDING.md) explains how a brand overrides these
tokens; this file defines what they are.

The founding statement this vocabulary serves: **brickwork is the building
blocks a user needs to build beautiful interfaces; our defaults should be
beautiful.** Every component has two hard gates: is it accessible, and is it
beautiful by default.

Phase (a) keeps the shipped flat naming (`--bw-color-*`, `--bw-size-*`,
`--bw-density-*`, `--bw-font-*`); the tier re-grammar (`--bw-space-*`,
`--bw-component-*`) lands in 0.4.0 per ADR-054 §7. Nothing in this release
renames or removes a shipped token.

---

## 1. The three-layer model (summary)

- **Substrate**: the token names and their meanings. Semver-public.
- **base-theme**: the beautiful default values for every token, light and
  authored dark. The root every brand inherits from. This file documents
  base-theme's values.
- **brand themes**: a delta of ~7-14 load-bearing tokens; everything else
  derives.

## 2. The load-bearing minimum

A brand authors these; base-theme derives the rest.

| # | Token | Why not derivable |
|---|---|---|
| 1 | `--bw-color-surface` | the paper colour |
| 2 | `--bw-color-fg` | the ink colour |
| 3 | `--bw-color-border` | grey or brand-tinted, a judgement call |
| 4 | `--bw-color-accent` | the brand colour |
| 5 | `--bw-color-danger` | distinct destructive meaning |
| 6 | `--bw-color-success` | distinct positive meaning |
| 7 | `--bw-color-warning` | distinct attention meaning |
| 8* | `--bw-color-surface-inverse` | only when ink is not the inverse surface (defaults to `:= fg`) |

Also brand-authorable but rarely: `--bw-color-info` (base-theme ships a
distinct cyan; a 3-role brand sets `--bw-color-info: var(--bw-color-accent)`
in one line), `--bw-color-fg-on-accent` (contrast pick; verify at 4.5:1),
the font families (`--bw-font-family-sans/-display/-mono`). Dark mode doubles
the authored set (dark values are authored, never computed from light,
BR-BW-TOK-002). Full brand light+dark: ~14-16 values.

## 3. Derivation mechanism

Derived tokens are live CSS expressions over the load-bearing set, so a brand
(or runtime tenant override) that sets `--bw-color-accent` recolours the whole
derived family in-browser with no rebuild.

- **`color-mix(in oklch, ...)` is the primary mechanism** (Baseline Widely
  Available since Nov 2025; shipped with no fallback). Every tint, shade, and
  mix below uses it.
- **Relative colour `oklch(from ...)` is avoided in 0.3.0.** ADR-054 §3
  proposed dual declarations (literal fallback, then live expression, last
  valid wins). That mechanism does not work for custom properties: any token
  stream is a valid custom-property declaration, so the live expression always
  wins at declaration time and an unsupporting engine only fails later, at the
  use site, falling back to `unset` rather than to the literal. Since every
  needed derivation is expressible in `color-mix()`, 0.3.0 ships color-mix
  only and no relative-colour syntax; this correction supersedes the ADR's
  fallback-emission mechanism and is recorded here deliberately.
- **Source encoding:** in the DTCG source a derived token keeps its shipped
  literal/alias as `$value` (documentation of the resolved default and the
  regression baseline) and carries the expression in
  `$extensions.bw.derived`. The build emits the expression as the token's
  value in `tokens.css`. A verification test recomputes each `color-mix()`
  linearly in oklch and asserts the result stays within a small tolerance of
  the `$value` baseline (guarding both the formula constants and future
  default-value edits).
- **Every derived token remains individually overridable.** Derivation is
  base-theme's default, never a lock: a brand may set any derived name to a
  flat value and the cascade wins.
- The same derivation graph applies in dark, with dark-specific constants
  (and, for three tokens, a flipped direction, noted inline below). Dark
  load-bearing values remain authored (BR-BW-TOK-002 is untouched: the
  *load-bearing* set is authored per theme; only within-theme fine tokens
  compute).

Percentage constants below are tuned so the computed result reproduces the
shipped 0.2.4 literal for the default palette (verified tolerance ΔL ≤ 0.015,
ΔC ≤ 0.02, Δalpha ≤ 0.01); the implementation verifies each constant against
the authored source values and adjusts within that tolerance where the source
literal differs from the figures used here. Where no constant can reach the
authored literal within tolerance, the token's $value baseline is updated to
the literal the expression computes (a permitted MINOR default-value change,
section 11), so $value always documents the value the live expression
resolves to.

## 4. Colour

### 4.1 Surfaces

| Token | LB/D | Light derivation | Dark derivation |
|---|---|---|---|
| `--bw-color-surface` | LB | authored | authored |
| `--bw-color-surface-sunken` | D | `color-mix(in oklch, var(--bw-color-surface) 98.5%, black)` | `color-mix(in oklch, var(--bw-color-surface) 76%, black)` (dark sunken is darker than surface) |
| `--bw-color-surface-raised` | D | `var(--bw-color-surface)` (light differentiates via shadow) | `color-mix(in oklch, var(--bw-color-surface) 93%, white)` (dark differentiates via lightness) |
| `--bw-color-surface-inverse` | D | `var(--bw-color-fg)` | `var(--bw-color-fg)` |
| `--bw-color-surface-overlay` **[NEW]** | D (light) / authored (dark) | `color-mix(in oklch, var(--bw-color-surface-inverse) 50%, transparent)` | authored `oklch(0 0 0 / 0.6)`: a scrim is dark-over-content in both themes, and dark surface-inverse (`:= fg`) is near-white, so the derivation would yield a light wash |

Rule: any component at elevation 2+ uses `background:
var(--bw-color-surface-raised)`, both themes.

### 4.2 Foregrounds

| Token | LB/D | Light | Dark |
|---|---|---|---|
| `--bw-color-fg` | LB | authored | authored |
| `--bw-color-fg-muted` | D | `color-mix(in oklch, var(--bw-color-fg) 56%, var(--bw-color-surface))` | same shape, 67% |
| `--bw-color-fg-subtle` **[NEW]** | D | `color-mix(in oklch, var(--bw-color-fg) 37%, var(--bw-color-surface))` | same shape, 49% |
| `--bw-color-fg-on-accent` | authored | contrast pick, stays a literal; the one derived-looking token every brand must verify at 4.5:1 | authored |
| `--bw-color-fg-on-inverse` | D | `var(--bw-color-surface)` | `var(--bw-color-surface)` |
| `--bw-color-icon-muted` | D | `var(--bw-color-fg-subtle)` | `var(--bw-color-fg-subtle)` |

### 4.3 Borders

| Token | LB/D | Light | Dark |
|---|---|---|---|
| `--bw-color-border` | LB | authored | authored |
| `--bw-color-border-strong` | D | `color-mix(in oklch, var(--bw-color-border) 94%, black)` | **direction flips**: `color-mix(in oklch, var(--bw-color-border) 86%, white)` (a dark theme's emphasis border must get lighter) |

### 4.4 Accent

| Token | LB/D | Light | Dark |
|---|---|---|---|
| `--bw-color-accent` | LB | authored | authored |
| `--bw-color-accent-hover` | D | `color-mix(in oklch, var(--bw-color-accent) 89%, black)` | `color-mix(in oklch, var(--bw-color-accent) 88%, black)` |
| `--bw-color-accent-subtle` | D | `color-mix(in oklch, var(--bw-color-accent) 7%, var(--bw-color-surface))` | `color-mix(in oklch, var(--bw-color-accent) 40%, black)` |
| `--bw-color-focus-ring` | D | `var(--bw-color-accent)` | `var(--bw-color-accent)` |

`accent-hover` is retained as the flat-colour fallback; transient hover
feedback on non-accent surfaces uses the state overlays (4.6), which is why a
brand whose hover is "a brightness shift" authors zero hover tokens.

### 4.5 Intents (danger / success / warning / info)

Five tiers per intent so an alert, badge, or toast never invents a value.
`X` ranges over `danger`, `success`, `warning`, `info`.

| Token | Tier | LB/D | Light | Dark |
|---|---|---|---|---|
| `--bw-color-X` | base | LB (info: authored cyan default, `:= accent` is the documented 3-role collapse) | authored | authored |
| `--bw-color-X-subtle` | tinted bg | D | `color-mix(in oklch, var(--bw-color-X) 7%, var(--bw-color-surface))` | `color-mix(in oklch, var(--bw-color-X) P%, black)` (danger 41%, success 37%, warning 36%, info 42%) |
| `--bw-color-X-strong` **[NEW]** | border/emphasis | D | `color-mix(in oklch, var(--bw-color-X) 88%, black)` | **flips**: `color-mix(in oklch, var(--bw-color-X) 96%, white)` |
| `--bw-color-X-fg` **[NEW]** | text on `X-subtle` | D | `var(--bw-color-X)` | `color-mix(in oklch, var(--bw-color-X) 78%, white)` (lightness boost for AA on the dark tint) |
| `--bw-color-X-on-fg` **[NEW]** | text on solid `X` | authored | `oklch(1 0 0)` for danger/success/info; near-black ink for warning (white on amber fails AA) | authored per hue, same rule (all four take near-black ink: the dark bases sit on the lighter 400/500 ramp steps, where white fails AA) |

The dark `subtle` tier (accent included) mixes toward **black**, not the
surface, a correction from the draft: the authored 950-ramp tints carry far
more chroma than a mix with the near-achromatic dark surface can reach
(ΔC ≈ 0.04 at any lightness-correct constant), and because the dark surface
is not chroma-free its 265 hue would dominate the interpolated hue, dragging
a danger tint toward violet. Mixing toward black preserves the intent hue
(black's hue is powerless) and reaches the authored depth.

### 4.6 Interactive state

Hybrid model: **transient feedback is a translucent overlay** applied over
whatever surface is beneath; **persistent state is a dedicated token**.

| Token | LB/D | Light | Dark |
|---|---|---|---|
| `--bw-state-hover-overlay` **[NEW]** | authored | `oklch(0 0 0 / 0.04)` | `oklch(1 0 0 / 0.06)` |
| `--bw-state-active-overlay` **[NEW]** | authored | `oklch(0 0 0 / 0.08)` | `oklch(1 0 0 / 0.12)` |
| `--bw-state-selected-bg` **[NEW]** | D | `var(--bw-color-accent-subtle)` | same |

Application mechanism: for elements with a transparent resting background
(nav links, ghost buttons, table rows, menu items) hover sets
`background-color: var(--bw-state-hover-overlay)` directly. For elements that
already carry a background (active nav item, selected row, primary button)
the overlay layers on top via
`background-image: linear-gradient(var(--bw-state-hover-overlay), var(--bw-state-hover-overlay))`,
so hover composes with, rather than replaces, the underlying state.

**Stacking order (normative for data_table and lists):** zebra stripe
(`surface-sunken` on odd rows) → selected (`--bw-state-selected-bg` replaces
the stripe) → hover overlay (always layers last, on top of whichever
background resolved). Disabled remains `opacity: var(--bw-disabled-opacity)`,
never a colour token.

### 4.7 Component roles (flat names in 0.3.0; component tier in 0.4.0)

| Token | LB/D | Light | Dark |
|---|---|---|---|
| `--bw-color-nav-item-active-bg` | D | `var(--bw-color-accent-subtle)` | same |
| `--bw-color-nav-item-active-text` | D | `var(--bw-color-accent-hover)` | **branches**: `color-mix(in oklch, var(--bw-color-accent) 25%, white)` (a high-lightness accent step; the light-mode borrow of accent-hover fails contrast on the dark tint) |
| `--bw-color-nav-item-active-border` | D | `var(--bw-color-accent)` | same |
| `--bw-color-nav-item-disabled-text` **[NEW]** | D | `var(--bw-color-fg-subtle)` | same |
| `--bw-color-nav-section-text` **[NEW]** | D | `var(--bw-color-fg-muted)` | same |
| `--bw-color-breadcrumb-current` **[NEW]** | D | `var(--bw-color-fg)` | same |
| `--bw-color-breadcrumb-separator` **[NEW]** | D | `var(--bw-color-fg-subtle)` | same |
| `--bw-color-skeleton-bg` | D | `color-mix(in oklch, var(--bw-color-surface-sunken) 98.2%, black)` | **direction flips**: `color-mix(in oklch, var(--bw-color-surface-sunken) 82%, white)` |
| `--bw-color-skeleton-shimmer` | D | `color-mix(in oklch, var(--bw-color-skeleton-bg) 96%, black)` | **direction flips**: `color-mix(in oklch, var(--bw-color-skeleton-bg) 86%, white)` |

## 5. Elevation

Six levels, values adopted from Tailwind 4's `--shadow-*` ramp (industry
consensus geometry), colours expressed in oklch, dark variants authored
(shadows vanish on dark surfaces: higher alpha, plus a faint inset top
highlight from level 3 to fake ambient light). Theme-variant: light values on
`:root`, dark under `[data-theme="dark"]`.

| Token | Light | Dark |
|---|---|---|
| `--bw-elevation-0` | `none` | `none` |
| `--bw-elevation-1` | `0 1px 2px 0 oklch(0 0 0 / 0.05)` | `0 1px 2px 0 oklch(0 0 0 / 0.3)` |
| `--bw-elevation-2` | `0 1px 3px 0 oklch(0 0 0 / 0.1), 0 1px 2px -1px oklch(0 0 0 / 0.1)` | `0 1px 3px 0 oklch(0 0 0 / 0.36), 0 1px 2px -1px oklch(0 0 0 / 0.3)` |
| `--bw-elevation-3` | `0 4px 6px -1px oklch(0 0 0 / 0.1), 0 2px 4px -2px oklch(0 0 0 / 0.1)` | `0 4px 6px -1px oklch(0 0 0 / 0.4), 0 2px 4px -2px oklch(0 0 0 / 0.3), inset 0 1px 0 0 oklch(1 0 0 / 0.04)` |
| `--bw-elevation-4` | `0 10px 15px -3px oklch(0 0 0 / 0.1), 0 4px 6px -4px oklch(0 0 0 / 0.1)` | `0 10px 15px -3px oklch(0 0 0 / 0.45), 0 4px 6px -4px oklch(0 0 0 / 0.35), inset 0 1px 0 0 oklch(1 0 0 / 0.05)` |
| `--bw-elevation-5` | `0 20px 25px -5px oklch(0 0 0 / 0.1), 0 8px 10px -6px oklch(0 0 0 / 0.1)` | `0 20px 25px -5px oklch(0 0 0 / 0.5), 0 8px 10px -6px oklch(0 0 0 / 0.4), inset 0 1px 0 0 oklch(1 0 0 / 0.06)` |

**Component map:** card / auth panel / centred panel / data-table wrap
resting = 1 (auth and centred panels: 2, they sit alone on a sunken page);
interactive card hover = 2; dropdown, popover, account-menu panel = 3 (the
fix for the hardcoded `0 4px 12px` literal); mobile drawer panel and modal
= 4; toast = 5; topbar = border-only by default (a brand may add 2).

## 6. Spacing, radius, borders, z-index, sizing

### 6.1 Spacing (`--bw-size-space-*`; values are Tailwind `--spacing` multiples)

Shipped: `0, 1 (0.25rem), 2 (0.5), 3 (0.75), 4 (1), 5 (1.25), 6 (1.5),
8 (2), 10 (2.5), 12 (3)`.
New: `px (1px)`, `0-5 (0.125rem)`, `1-5 (0.375rem)`, `7 (1.75rem)`,
`9 (2.25rem)`, `11 (2.75rem)`, `16 (4rem)`, `20 (5rem)`, `24 (6rem)`.

`-0-5` (not `-px`) replaces the hardcoded `2px` gaps/paddings so they scale
with root font size; `-px` exists for true hairline spacing that must not
scale. `-11` deliberately equals the touch-target minimum. No negative ramp
(use `calc(var(--bw-size-space-N) * -1)` at the point of use).

### 6.2 Radius (`--bw-size-radius-*`)

Shipped: `sm 0.25rem, md 0.375rem, lg 0.5rem, full 9999px`.
New: `none 0`, `xl 0.75rem`, `2xl 1rem` (Tailwind-aligned values).

**Component map:** skeleton sm; button, input, nav link, alert, form-errors,
badge-square md; card, auth/centred panel, filter bar lg; dropdown,
account-menu panel, popover, toast, modal xl; badge, avatar, pill full.

### 6.3 Border widths

| Token | Value | Use |
|---|---|---|
| `--bw-size-border-hairline` **[NEW]** | `1px` | every default border/divider |
| `--bw-size-border-thick` **[NEW]** | `2px` | emphasis borders |
| `--bw-size-border-nav-marker` **[NEW]** | `3px` | the nav active marker |

### 6.4 Focus ring (a11y floor: not brand-tunable except colour)

| Token | Value |
|---|---|
| `--bw-focus-ring-width` **[NEW]** | `2px` |
| `--bw-focus-ring-offset` **[NEW]** | `2px` |
| `--bw-focus-ring-style` **[NEW]** | `solid` |
| `--bw-color-focus-ring` | existing, `:= accent` (brand-overridable; must keep ≥3:1 against surface in both themes, WCAG 1.4.11) |

Composed global rule:
`outline: var(--bw-focus-ring-width) var(--bw-focus-ring-style) var(--bw-color-focus-ring); outline-offset: var(--bw-focus-ring-offset);`

### 6.5 Z-index scale (`--bw-z-*`) **[NEW]**

`base 0, dropdown 10, sticky 20, drawer 30, overlay 40, modal 50,
skip-link 60, toast 70, tooltip 80.`

Replaces the bare `10` (topbar → sticky 20), `20` (drawer panel → drawer 30),
`100` (skip link → 60), and the account-menu panel's `20` (→ dropdown 10).
Note the deliberate renumbering: dropdown content that opens inside the
sticky topbar must not fight it, and sticky chrome sits below overlay
surfaces.

### 6.6 Sizing

| Token | Value | Notes |
|---|---|---|
| `--bw-icon-size-2xl` **[NEW]** | `2.5rem` | empty-state hero icons |
| `--bw-size-control-height-sm` **[NEW]** | `2rem` | fixed, not density-scaled (sm × compact would break touch targets) |
| `--bw-size-control-height-md` **[NEW]** | `var(--bw-density-control-height)` | alias of the density token |
| `--bw-size-control-height-lg` **[NEW]** | `3rem` | fixed |
| `--bw-size-touch-target-min` **[NEW]** | `2.75rem` | WCAG 2.5.5 floor; never density-scaled |
| `--bw-size-max-width-prose` **[NEW]** | `65ch` | long-form measure |
| `--bw-size-max-width-form` **[NEW]** | `32rem` | formalises the empty-state body literal |
| `--bw-size-max-width-modal-sm` **[NEW]** | `28rem` | matches the auth panel |
| `--bw-size-max-width-modal-md` **[NEW]** | `32rem` | |
| `--bw-size-max-width-modal-lg` **[NEW]** | `48rem` | |
| `--bw-drawer-width` **[NEW]** | `min(20rem, 80vw)` | formalises the drawer literal |

The `--bw-size-icon-*` / `--bw-icon-size-*` duplication resolves in 0.4.0
(keep `--bw-icon-size-*`); 0.3.0 adds `2xl` under both names for parity.

### 6.7 Density (all three modes; compact / comfortable / spacious)

Shipped seven unchanged. New:

| Token | Compact | Comfortable | Spacious |
|---|---|---|---|
| `--bw-density-topbar-height` **[NEW]** | 3rem | 3.5rem | 4rem |
| `--bw-density-section-gap` **[NEW]** | 1.5rem | 2rem | 3rem |
| `--bw-density-card-padding` **[NEW]** | 0.75rem | 1rem | 1.5rem |
| `--bw-density-page-gutter-inline` **[NEW]** | 1rem | 1.5rem | 2rem |

`section-gap` is the gap BETWEEN page sections; `stack-gap` stays the gap
WITHIN a stack. `page-gutter-inline` frees `row-padding-inline` to mean only
in-row padding. Never density-variant: font sizes and line heights (WCAG
1.4.4 in spirit), radius, elevation, border widths, touch-target minimum,
the spacing ramp itself.

## 7. Typography

### 7.1 Families (the brand's dial)

```
--bw-font-family-sans:    system-ui, -apple-system, "Segoe UI", Roboto,
                          "Helvetica Neue", Arial, "Noto Sans", sans-serif,
                          "Apple Color Emoji", "Segoe UI Emoji";
--bw-font-family-display: var(--bw-font-family-sans);
--bw-font-family-mono:    ui-monospace, SFMono-Regular, "SF Mono", Menlo,
                          Consolas, "Liberation Mono", "Courier New", monospace;
```

(Additive completions of the shipped stacks: Noto Sans + emoji fallbacks,
Courier New.)

### 7.2 Size scale (`--bw-font-size-*`; every shipped value preserved)

| Token | rem | px | Use |
|---|---|---|---|
| `3xs` **[NEW]** | 0.625 | 10 | bottom rung, no direct consumer |
| `2xs` **[NEW]** | 0.6875 | 11 | overlines, micro-labels; the floor for chrome text, never sentences |
| `xs` | 0.75 | 12 | captions, help, errors, timestamps |
| `sm` | 0.875 | 14 | dense UI text, table cells |
| `md` | 1 | 16 | body, inputs, buttons |
| `lg` | 1.125 | 18 | emphasised body, card titles |
| `xl` | 1.5 | 24 | page/dialog titles |
| `2xl` | 2 | 32 | section/display headings |
| `3xl` **[NEW]** | 2.5 | 40 | large page titles, h2-equivalent |
| `4xl` **[NEW]** | 3 | 48 | hero headings (auth/centred shells) |
| `5xl` **[NEW]** | 3.75 | 60 | display numerals (error pages) |

### 7.3 Line heights, weights, tracking

- `--bw-font-line-height-*`: `none 1` **[NEW]**, `tight 1.25`,
  `snug 1.375` **[NEW]**, `normal 1.5`, `relaxed 1.625` **[NEW]**,
  `loose 2` **[NEW]** (Tailwind names/values).
- `--bw-font-weight-*`: `normal 400, medium 500, semibold 600, bold 700`
  (unchanged; 300/800 excluded because the fallback stacks cannot honour
  them).
- `--bw-font-tracking-*` **[NEW]**: `tight -0.025em, normal 0em,
  wide 0.025em, wider 0.05em` (Tailwind names/values; `wider` pairs with
  uppercase overlines, which read tighter than mixed case).

### 7.4 Type roles (`--bw-text-<role>-*`) **[NEW]**

Each role is a bundle of five properties
(`-family`, `-size`, `-line-height`, `-weight`, `-tracking`), every value a
`var()` reference into the scales above so overrides cascade. Components
consume roles, never raw scale steps, so nothing drifts out of rhythm.

| Role | Family | Size | Leading | Weight | Tracking |
|---|---|---|---|---|---|
| `heading-2xl` | display | 2xl | tight | bold | tight |
| `heading-xl` | display | xl | tight | bold | tight |
| `heading-lg` | sans | lg | snug | semibold | normal |
| `heading-md` | sans | md | snug | semibold | normal |
| `heading-sm` | sans | sm | snug | semibold | normal |
| `body-lg` | sans | lg | relaxed | normal | normal |
| `body-md` | sans | md | normal | normal | normal |
| `body-sm` | sans | sm | normal | normal | normal |
| `label` | sans | sm | none | medium | normal |
| `caption` | sans | xs | normal | normal | normal |
| `overline` | sans | 2xs | none | semibold | wider |
| `code` | mono | sm | normal | normal | normal |

**Component map:** page-header title heading-xl (description body-md +
fg-muted); empty-state heading heading-lg, body body-md + fg-muted +
max-width-form; alert title heading-sm; form-errors title heading-sm; card
title heading-md; table th label (td body-sm; definition-mode label column
body-sm + fg-subtle); field label label, help and errors caption; button
label label; badge caption size at medium weight, tabular-nums; nav link
body-md, nav section-label overline (uppercase at the component); breadcrumbs
body-sm + fg-muted, current crumb breadcrumb-current; account-menu item
body-md, secondary line caption; pagination status caption + fg-muted;
dialog/modal title heading-sm.

## 8. Motion

### 8.1 Durations (`--bw-duration-*`) **[NEW]**

`instant 1ms` (fires transitionend, unlike 0), `fast 100ms`, `normal 200ms`,
`moderate 250ms`, `slow 400ms`, plus loop timings `shimmer 1500ms`,
`spin 700ms` (formalising the two hardcoded loops).

### 8.2 Easings (`--bw-ease-*`) **[NEW]**

`linear`, `standard cubic-bezier(0.4, 0, 0.2, 1)`,
`in cubic-bezier(0.4, 0, 1, 1)` (exits),
`out cubic-bezier(0, 0, 0.2, 1)` (entrances),
`in-out cubic-bezier(0.4, 0, 0.2, 1)` (moves),
`emphasised cubic-bezier(0.2, 0, 0, 1)` (energetic entrances).

### 8.3 Composite transitions (`--bw-transition-*`) **[NEW]**

| Token | Value |
|---|---|
| `colors` | `color var(--bw-duration-fast) var(--bw-ease-standard), background-color var(--bw-duration-fast) var(--bw-ease-standard), border-color var(--bw-duration-fast) var(--bw-ease-standard)` |
| `opacity` | `opacity var(--bw-duration-fast) var(--bw-ease-standard)` |
| `transform` | `transform var(--bw-duration-normal) var(--bw-ease-in-out)` |
| `shadow` | `box-shadow var(--bw-duration-fast) var(--bw-ease-standard)` |

Usage: `transition: var(--bw-transition-colors);`. Never `transition: all`.
Interaction map: hover colour shifts fast/standard; pressed and focus-ring
instant; disclosure and caret rotate normal; spinner spin/linear; shimmer
shimmer/linear; skip-link reveal fast.

### 8.4 Keyframes and reduced motion

`@keyframes bw-fade-in-up` (opacity 0→1, translateY(-4px)→0) joins
`bw-spin`/`bw-shimmer` as the entrance treatment for dropdown-shaped panels
(`animation: bw-fade-in-up var(--bw-duration-normal) var(--bw-ease-out)`).
The global `prefers-reduced-motion` floor is unchanged, `!important`,
non-tokenised infrastructure; `.bw-spinner` and the account-menu caret gain
explicit `animation: none` / no-transition overrides under it (a frozen
mid-state reads as broken). `--bw-motion-scale` remains a documented,
unshipped extension point.

## 9. Opacity

| Token | Value | Role |
|---|---|---|
| `--bw-disabled-opacity` | `0.5` | existing, unchanged (name migrates in 0.4.0) |
| `--bw-opacity-muted` **[NEW]** | `0.7` | de-emphasis that is not disabled; conservative floor, re-verify contrast per use |
| `--bw-opacity-sort-idle` **[NEW]** | `0.4` | names the shipped sort-caret literal (decorative only) |

## 10. Reserved names (documented, deliberately not shipped)

`--bw-avatar-size-{sm,md,lg,xl}`, `--bw-aspect-ratio-avatar`,
`--bw-aspect-ratio-media`, `--bw-motion-scale`, `--bw-backdrop-blur`,
`--bw-focus-ring-offset-color`, `--bw-opacity-backdrop` (superseded by
`--bw-color-surface-overlay`), `--bw-font-size-scale-multiplier`. Each ships
only when a real consumer names the need (YAGNI; ADR-054 §6).

## 11. Semver

Adding a token is MINOR. Renaming or removing a semantic/component token is
MAJOR (relaxed to direct minors inside 0.x with courtesy aliases). **A
base-theme default-value change is MINOR** (names and meanings are the
contract, values are brand-overridable) with two guardrails: a default change
that breaks WCAG AA contrast is a defect, gated by the axe contrast run in
light and dark; and changing a token's meaning while keeping its name is a
rename in disguise (MAJOR). Accessibility floors (`--bw-focus-ring-width`,
`--bw-size-touch-target-min`, the reduced-motion block) are never
brand-configurable.
