# Design system: Folio (fictional brand-pack skeleton)

> Category: fictional editorial console on django-brickwork.
> Status: skeleton only. Copy into a consuming project and rename.
> Not kiln. Not a product identity. Values are invented for the contract demo.

This pack demonstrates the consumer brand-pack contract in
[docs/brand-pack.md](../../brand-pack.md). Every numeric claim either cites a
`--bw-*` override in [tokens.css](tokens.css) or is marked deferred to
base-theme.

## 1. Visual theme and atmosphere

Cool paper, forest ink, one restrained green accent for primary actions, and a
distinct coral for danger. Editorial quiet: type first, no decorative brand
noise.

## 2. Colour roles

### Light (`:root` / `[data-bw-brand="folio"]`)

| Role | oklch | Maps to |
|------|-------|---------|
| Surface | oklch(0.978 0.006 120) | `--bw-color-surface` |
| Foreground | oklch(0.25 0.025 150) | `--bw-color-fg` |
| Border | oklch(0.89 0.012 140) | `--bw-color-border` |
| Accent | oklch(0.42 0.09 155) | `--bw-color-accent` |
| Danger | oklch(0.54 0.18 20) | `--bw-color-danger` |
| Success | oklch(0.52 0.11 160) | `--bw-color-success` |
| Warning | oklch(0.68 0.12 80) | `--bw-color-warning` |
| fg-on-accent | oklch(0.98 0.005 120) | `--bw-color-fg-on-accent` (verify >= 4.5:1) |

### Dark (`[data-theme="dark"]` / compound folio dark)

| Role | oklch | Maps to |
|------|-------|---------|
| Surface | oklch(0.22 0.02 150) | `--bw-color-surface` |
| Foreground | oklch(0.93 0.012 120) | `--bw-color-fg` |
| Border | oklch(0.35 0.02 150) | `--bw-color-border` |
| Accent | oklch(0.72 0.08 155) | `--bw-color-accent` |
| Danger | oklch(0.66 0.15 20) | `--bw-color-danger` |
| Success | oklch(0.68 0.10 160) | `--bw-color-success` |
| Warning | oklch(0.74 0.11 80) | `--bw-color-warning` |
| fg-on-accent | oklch(0.20 0.02 150) | `--bw-color-fg-on-accent` (dark ink on lifted accent) |

Derived surface and status tiers: deferred to base-theme.

## 3. Typography

### Font families (sourced in tokens.css)

- Sans: `"Libre Franklin", system-ui, sans-serif` -> `--bw-font-family-sans`
- Display: `"Newsreader", Georgia, serif` -> `--bw-font-family-display`
- Mono: `"Source Code Pro", ui-monospace, monospace` -> `--bw-font-family-mono`

### Hierarchy

Size, weight, line-height, tracking, and `--bw-text-*` roles: **deferred to
base-theme**. Do not invent a parallel px table.

## 4. Component signal

Brand accent appears on primary CTAs and active nav only. Do not restyle
`.bw-*` classes. Button padding, radius, and ghost treatments stay on package
tokens.

## 5. Layout intent

Use `--bw-space-*` and `--bw-radius-*` from package DESIGN.md. **Deferred to
base-theme**: no brand-authored spacing or radius overrides in tokens.css.

## 6. Depth and elevation

Use `--bw-elevation-*` from package DESIGN.md section 5. **Deferred to
base-theme**: this skeleton does not override elevation.

## 7. Do and do not

Do:

- Author `--bw-color-fg-on-accent` per theme and verify 4.5:1.
- Keep danger distinct from accent.
- Load [tokens.css](tokens.css) after package `tokens.css` / `brickwork.css`.

Do not:

- Invent spacing, shadow, or type scales outside `--bw-space-*`,
  `--bw-elevation-*`, and `--bw-font-*` / `--bw-text-*`.
- Restyle `.bw-*` classes or add a components kit.
- Copy trademark-inspired catalogue content into this pack.

## 8. Responsive behaviour

**Deferred to base-theme** and package shells (`--bw-breakpoint-*`). No
folio-specific collapse table.

## 9. Agent brief

Read [THEME.md](../../../THEME.md) first and declare the claimed level in
`PROFILE.md`. This pack is **L2** (recolour + font families). Override only
documented `--bw-*` names on `[data-bw-brand="folio"]` after brickwork
tokens. Never invent token names. Verify fg-on-accent at 4.5:1 in both
themes. Compose pages from brickwork sections; do not fork components. Mark
any undecided metric deferred to base-theme rather than inventing values.
