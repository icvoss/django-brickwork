# Design system: Northline-material (fictional L3 torture)

> Category: exaggerated material language on the northline colour voice.
> Status: skeleton only. Copy when you need an L3 PROFILE example.
> Not kiln. Not a recommended look. Values are invented for the contract demo.

Demonstrates [THEME.md](../../../THEME.md) **L3** on the consumer brand-pack
contract in [docs/brand-pack.md](../../brand-pack.md). Every numeric claim
cites [tokens.css](tokens.css) or is marked deferred.

## 1. Visual theme and atmosphere

Same cool-paper northline ink and teal, but chrome softens (large radius) and
lifts (raised surface + heavier shadows). Intentionally loud so an author can
see L3 without DevTools archaeology.

## 2. Colour roles

### Light

| Role | oklch | Maps to |
|------|-------|---------|
| Surface | oklch(0.985 0.004 240) | `--bw-color-surface` |
| Surface raised | oklch(1 0.002 240) | `--bw-color-surface-raised` |
| Foreground | oklch(0.26 0.02 250) | `--bw-color-fg` |
| Border | oklch(0.90 0.01 240) | `--bw-color-border` |
| Accent | oklch(0.52 0.11 200) | `--bw-color-accent` |
| Danger | oklch(0.55 0.18 25) | `--bw-color-danger` |
| Success | oklch(0.56 0.13 155) | `--bw-color-success` |
| Warning | oklch(0.70 0.14 75) | `--bw-color-warning` |
| fg-on-accent | oklch(0.99 0 0) | `--bw-color-fg-on-accent` |

### Dark

| Role | oklch | Maps to |
|------|-------|---------|
| Surface | oklch(0.23 0.02 250) | `--bw-color-surface` |
| Surface raised | oklch(0.28 0.02 250) | `--bw-color-surface-raised` |
| Foreground | oklch(0.93 0.01 90) | `--bw-color-fg` |
| Border | oklch(0.36 0.015 250) | `--bw-color-border` |
| Accent | oklch(0.70 0.10 200) | `--bw-color-accent` |
| Danger | oklch(0.65 0.16 25) | `--bw-color-danger` |
| Success | oklch(0.66 0.12 155) | `--bw-color-success` |
| Warning | oklch(0.74 0.12 80) | `--bw-color-warning` |
| fg-on-accent | oklch(0.22 0.02 250) | `--bw-color-fg-on-accent` |

Further surface ladder (sunken / overlay / marketing-tint): **deferred**.

## 3. Typography

### Font families (sourced in tokens.css)

- Sans: `"Source Sans 3", system-ui, sans-serif` -> `--bw-font-family-sans`
- Display: `"Source Serif 4", Georgia, serif` -> `--bw-font-family-display`
- Mono: `"IBM Plex Mono", ui-monospace, monospace` -> `--bw-font-family-mono`

Size, weight, line-height, tracking, and `--bw-text-*` roles: **deferred**.

## 4. Component signal

Brand accent on primary CTAs and active nav only. Do not restyle `.bw-*`.
Radius and elevation changes must flow through tokens into kit chrome.

## 5. Layout intent

### Radius (authored)

| Token | Value |
|-------|-------|
| `--bw-radius-sm` | `0.5rem` |
| `--bw-radius-md` | `0.875rem` |
| `--bw-radius-lg` | `1.25rem` |

Spacing scale: **deferred** (see northline-dense for L4).

## 6. Depth and elevation

### Light / dark elevations (authored in tokens.css)

`--bw-elevation-1`, `--bw-elevation-2`, `--bw-elevation-3` use heavier,
slightly tinted shadows than base-theme so cards and modals visibly lift.

## 7. Do and do not

Do:

- Keep fg-on-accent ≥ 4.5:1 in both themes.
- Preview shell, card, form, and one marketing band for L3.
- Cite THEME.md when claiming L3.

Do not:

- Claim L3 with colours alone.
- Restyle `.bw-*` or invent non-`--bw-*` tokens.
- Treat this soft-radius look as a recommended product default.

## 8. Responsive behaviour

**Deferred to base-theme** and package shells (`--bw-breakpoint-*`).

## 9. Agent brief

Read [THEME.md](../../../THEME.md). This pack claims **L3** (material:
radius + elevation + surface-raised on an L2 voice). Override only documented
`--bw-*` names on `[data-bw-brand="northline-material"]` after brickwork
tokens. Verify fg-on-accent at 4.5:1 in both themes. Preview kit chrome, not
only swatches. Do not fork components. For rhythm (L4) copy
`northline-dense` instead of inventing spacing ad hoc.
