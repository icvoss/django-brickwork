# Design system: Northline-dense (fictional L4 torture)

> Category: northline-material plus compressed system rhythm.
> Status: skeleton only. Copy when you need an L4 PROFILE example.
> Not kiln. Not a recommended look. Values are invented for the contract demo.

Demonstrates [THEME.md](../../../THEME.md) **L4** on the consumer brand-pack
contract in [docs/brand-pack.md](../../brand-pack.md). Every numeric claim
cites [tokens.css](tokens.css) or is marked deferred.

## 1. Visual theme and atmosphere

Same soft-radius northline material as `northline-material`, then pace the
product denser: smaller `--bw-space-1` and a compact density default so
controls, cards, and stacks sit closer. Intentionally tight for level demos.

## 2. Colour roles

Same authored roles as [northline-material/DESIGN.md](../northline-material/DESIGN.md)
(surface, surface-raised, fg, border, accent, danger, success, warning,
fg-on-accent) in light and dark. Values live in this pack's tokens.css so the
directory is self-contained.

Further surface ladder: **deferred**.

## 3. Typography

### Font families (sourced in tokens.css)

- Sans: `"Source Sans 3", system-ui, sans-serif` -> `--bw-font-family-sans`
- Display: `"Source Serif 4", Georgia, serif` -> `--bw-font-family-display`
- Mono: `"IBM Plex Mono", ui-monospace, monospace` -> `--bw-font-family-mono`

Size, weight, line-height, tracking, and `--bw-text-*` roles: **deferred**.

## 4. Component signal

Brand accent on primary CTAs and active nav only. Do not restyle `.bw-*`.
Density and spacing changes must flow through tokens into kit chrome.

## 5. Layout intent

### Radius (authored)

| Token | Value |
|-------|-------|
| `--bw-radius-sm` | `0.5rem` |
| `--bw-radius-md` | `0.875rem` |
| `--bw-radius-lg` | `1.25rem` |

### Spacing base (authored, L4)

| Token | Value |
|-------|-------|
| `--bw-space-1` | `0.1875rem` (base-theme default is `0.25rem`) |

Page margins and one-off layout gaps remain page-owned (consumer Tailwind).

## 6. Depth and elevation

`--bw-elevation-1` / `-2` / `-3` authored as in northline-material (heavier
than base-theme). See tokens.css.

## 7. Do and do not

Do:

- Set `data-density="compact"` on the shell when previewing this pack.
- Keep fg-on-accent ≥ 4.5:1 in both themes.
- Preview shell, card, form, and one marketing band.
- Cite THEME.md when claiming L4.

Do not:

- Claim L4 with colours alone.
- Override page layout utilities instead of `--bw-space-1` / density tokens.
- Restyle `.bw-*` or invent non-`--bw-*` tokens.

## 8. Responsive behaviour

**Deferred to base-theme** and package shells (`--bw-breakpoint-*`).

## 9. Agent brief

Read [THEME.md](../../../THEME.md). This pack claims **L4** (L3 material plus
`--bw-space-1` and compact density). Override only documented `--bw-*` names
on `[data-bw-brand="northline-dense"]` after brickwork tokens. Put
`data-density="compact"` on the shell. Verify fg-on-accent at 4.5:1 in both
themes. Preview kit chrome under the denser rhythm. Do not fork components.
