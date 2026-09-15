# Design system: Northline (fictional brand-pack skeleton)

> Category: fictional B2B operations console on django-brickwork.
> Status: skeleton only. Copy into a consuming project and rename.
> Not kiln. Not a product identity. Values are invented for the contract demo.

This pack demonstrates the consumer brand-pack contract in
[docs/brand-pack.md](../../brand-pack.md). Every numeric claim either cites a
`--bw-*` override in [tokens.css](tokens.css) or is marked deferred to
base-theme.

## 1. Visual theme and atmosphere

Cool paper, near-black ink, one restrained teal accent for primary actions,
and a distinct coral for danger. Quiet console density: structure first, no
decorative brand noise.

## 2. Colour roles

### Light (`:root` / `[data-bw-brand="northline"]`)

| Role | oklch | Maps to |
|------|-------|---------|
| Surface | oklch(0.985 0.004 240) | `--bw-color-surface` |
| Foreground | oklch(0.26 0.02 250) | `--bw-color-fg` |
| Border | oklch(0.90 0.01 240) | `--bw-color-border` |
| Accent | oklch(0.52 0.11 200) | `--bw-color-accent` |
| Danger | oklch(0.55 0.18 25) | `--bw-color-danger` |
| Success | oklch(0.56 0.13 155) | `--bw-color-success` |
| Warning | oklch(0.70 0.14 75) | `--bw-color-warning` |
| fg-on-accent | oklch(0.99 0 0) | `--bw-color-fg-on-accent` (verify >= 4.5:1) |

### Dark (`[data-theme="dark"]` / compound northline dark)

| Role | oklch | Maps to |
|------|-------|---------|
| Surface | oklch(0.23 0.02 250) | `--bw-color-surface` |
| Foreground | oklch(0.93 0.01 90) | `--bw-color-fg` |
| Border | oklch(0.36 0.015 250) | `--bw-color-border` |
| Accent | oklch(0.70 0.10 200) | `--bw-color-accent` |
| Danger | oklch(0.65 0.16 25) | `--bw-color-danger` |
| Success | oklch(0.66 0.12 155) | `--bw-color-success` |
| Warning | oklch(0.74 0.12 80) | `--bw-color-warning` |
| fg-on-accent | oklch(0.22 0.02 250) | `--bw-color-fg-on-accent` (dark ink on lifted accent) |

Derived surface and status tiers: deferred to base-theme.

## 3. Typography

### Font families (sourced in tokens.css)

- Sans: `"Source Sans 3", system-ui, sans-serif` -> `--bw-font-family-sans`
- Display: `"Source Serif 4", Georgia, serif` -> `--bw-font-family-display`
- Mono: `"IBM Plex Mono", ui-monospace, monospace` -> `--bw-font-family-mono`

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
northline-specific collapse table.

## 9. Agent brief

Read [THEME.md](../../../THEME.md) first and declare the claimed level in
`PROFILE.md`. This pack is **L2** (recolour + font families). Override only
documented `--bw-*` names on `[data-bw-brand="northline"]` after brickwork
tokens. Never invent token names. Verify fg-on-accent at 4.5:1 in both
themes. Compose pages from brickwork sections; do not fork components. Mark
any undecided metric deferred to base-theme rather than inventing values.
Do not claim L3/L4 without the axes in THEME.md; copy
`northline-material` or `northline-dense` when you need those levels.
