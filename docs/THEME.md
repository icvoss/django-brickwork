# Brickwork Theme

**Status:** normative consumer product contract (ADR-110).  
**Audience:** consumers authoring a brand; package maintainers; agents.  
**Companions:** [brand-pack.md](brand-pack.md) (directory unit), [BRANDING.md](BRANDING.md) (override mechanism), [DESIGN.md](DESIGN.md) (token vocabulary), [INTEGRATION.md](INTEGRATION.md) (Tailwind projection path).

## What this is

**Brickwork Theme** is how a consumer builds a visual profile on the substrate:
values on published `--bw-*` tokens (and an optional density default), loaded
after package CSS, so the owned kit (`.bw-*`) and any consumer Tailwind
utilities that import `tailwind-theme.css` follow the brand.

It is the same *kind* of job as authoring a Tailwind `@theme`: constrained
dials, not rewriting components. It is **not** shipping a general Tailwind
utility layer inside `brickwork.css`, and **not** licence to restyle `.bw-*`
in brand CSS.

## Three owners

| Owner | Decides | Does not decide |
|---|---|---|
| Substrate | Token names, derivation, a11y floors, axes | Your look |
| Theme profile (this doc) | Values on overridable axes | Component markup, ARIA, HTMX |
| Page | Composition, content, Tailwind layout | Chrome recipes, token schema |

## Depth ladder

| Level | Name | What you author | Claim you may make |
|---|---|---|---|
| **L0** | Base | Nothing | Package defaults |
| **L1** | Recolour | Load-bearing colours + `fg-on-accent` (light and dark) | Recolour in ~16 lines |
| **L2** | Voice | L1 + `--bw-font-family-sans` / `-display` / `-mono` (optional type roles) | Recognisable type voice |
| **L3** | Material | L2 + radius and/or elevation and/or surface ladder beyond L1 | Material language |
| **L4** | Rhythm | L3 + `--bw-space-1` and/or density default / density tokens | Product pacing |

A pack **must** declare the highest level it claims in `PROFILE.md` (see
[brand-pack.md](brand-pack.md)). Claiming L3 while only shipping L1 colours is
a documentation defect.

### L1 required tokens (per theme)

- `--bw-color-surface`
- `--bw-color-fg`
- `--bw-color-border`
- `--bw-color-accent`
- `--bw-color-danger`
- `--bw-color-success`
- `--bw-color-warning`
- `--bw-color-fg-on-accent` (verify ≥ 4.5:1 on accent)

Optional at L1: `--bw-color-info` (or collapse to accent), `--bw-color-surface-inverse`, `--bw-color-focus-ring`.

### L2 required tokens

All L1 required, plus:

- `--bw-font-family-sans`
- `--bw-font-family-display`
- `--bw-font-family-mono`

Optional: `--bw-text-<role>-*` size/weight/line-height/tracking where the brand
changes defaults. Prefer roles over raw `--bw-font-size-*` ladders.

### L3 requirements

All L2 required, plus a coherent authored set in **at least one** of:

1. **Surfaces:** e.g. `--bw-color-surface-raised` (and optionally sunken / overlay / marketing-tint / border-strong)
2. **Radius:** at minimum `--bw-radius-sm`, `--bw-radius-md`, `--bw-radius-lg`
3. **Elevation:** at minimum `--bw-elevation-1`, `--bw-elevation-2`, `--bw-elevation-3` (light and dark)

Document which material axes are deferred.

### L4 requirements

All L3 requirements for the claimed material axes, plus **either**:

- author `--bw-space-1` (spacing base), and/or
- set a brand default density (`data-density`) and/or author `--bw-density-*` for the shipped mode(s)

Page margins and one-off layout gaps remain **page-owned** (consumer Tailwind).
Theme owns system rhythm, not every page inset.

## Kit-owned (not theme dials)

Do not present these as ordinary theme axes:

| Family | Examples | Why |
|---|---|---|
| Focus geometry | `--bw-focus-ring-width`, `-offset`, `-style` | A11y floor (colour may be L1 optional) |
| Z-index | `--bw-z-*` | Layer contract |
| Motion | `--bw-duration-*`, `--bw-ease-*`, `--bw-transition-*` | Kit interaction map |
| Breakpoints | `--bw-breakpoint-*` | Shared layout; consumer Tailwind build-time only if overridden |
| Touch floor | `--bw-size-touch-target-min` | A11y |
| Most `--bw-component-*` | Icons, toast width, toggle geometry | Kit chrome |
| Opacity roles | `--bw-opacity-muted`, disabled / HTMX opacities | Sparse semantics, not a scale |

**Opacity when composing:** disabled/in-flight via component APIs; rare global
muted via token; one-off quieter blocks via a **consumer wrapper** (e.g.
Tailwind `opacity-*`). There is no general `opacity=` on kit tags.

## Defaults you already inherit

Base-theme ships full scales (radius, spacing, elevation, type roles, border
widths, density modes). L0/L1 consumers get them automatically. Higher levels
**replace** selected values; they do not invent parallel scales.

## Tailwind relationship

| Layer | Role |
|---|---|
| `--bw-*` | Source of truth |
| `.bw-*` kit | Reads tokens; no Tailwind `@apply` in component CSS |
| `tailwind-theme.css` | Optional projection so consumer utilities inherit the theme |
| Consumer Tailwind build | Page layout utilities (`grid`, `gap-4`, …) |

Import order for a themed Tailwind consumer:

```css
@import "tailwindcss";
@import "<path>/brickwork/dist/tokens.css"; /* or rely on brickwork.css link */
@import "<path>/brickwork/dist/tailwind-theme.css";
/* then your brand tokens.css */
```

`brickwork.css` alone does not emit a general utility layer.

## Honesty rules

1. Never claim "rebrand the whole system in 16 lines" as a full brand.
2. L1 = recolour. L3/L4 = theme depth, only when axes are authored.
3. Never invent token names outside `token-manifest.json` / DESIGN.md.
4. Never restyle `.bw-*` in a theme pack.
5. Kit craft (beauty of defaults) is a separate bar ([VISUAL-BAR.md](VISUAL-BAR.md)); a theme cannot rescue flat kit chrome.

## Worked artefacts

| Artefact | Role |
|---|---|
| [examples/brand-pack/northline/](examples/brand-pack/northline/) | Fictional **L2** skeleton (`PROFILE.md`) |
| [examples/brand-pack/northline-material/](examples/brand-pack/northline-material/) | Fictional **L3** torture (radius + elevation + raised surface) |
| [examples/brand-pack/northline-dense/](examples/brand-pack/northline-dense/) | Fictional **L4** torture (material + space-1 + compact density) |
| `harbour/`, `folio/` | Additional fictional **L2** voices |
| `render_brand_css()` | Emitter for validated overrides (colours + L2 to L4 overridable values) |
| `infer_theme_level` / `check_theme_level` | Pure level inference and claimed-vs-evidenced check (`brickwork.services.theme_profile`, re-exported from `brickwork.services.tokens`) |
| `recommended_tokens_for_level` | Checklist-driven recommended token names per level |
| `{% bw_token_specimen %}` | Live preview when wired (#268) |

### Level check (Phase C)

```python
from brickwork.services.tokens import check_theme_level, render_brand_css

report = check_theme_level("L3", light.keys())
assert report.ok, report.message  # colours-only claiming L3 fails
css = render_brand_css(light, dark)  # unknown names still raise BrandValidationError
```

Kit-owned tokens (focus geometry, z-index, motion, breakpoints, touch floor,
most `--bw-component-*`, opacity roles) may still emit via `render_brand_css`
when overridable, but **never evidence** a theme level (`kit_owned_present` /
`ThemeLevelReport.kit_owned`).

## Related programmes

Theme profiles dress the kit. Raising zero-kwargs kit craft remains
beat / beautiful-defaults work. Do not substitute one for the other.
