# brickwork design tokens: the complete reference

**Status:** canonical token reference for brickwork 0.11.0 (ADR-054 Phase a,
tier re-grammar per ADR-054 section 7).
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

Phase (a) kept the shipped flat naming (`--bw-color-*`, `--bw-size-*`,
`--bw-density-*`, `--bw-font-*`) through 0.10.0; the tier re-grammar
(`--bw-space-*`, `--bw-radius-*`, `--bw-component-*`) landed in 0.11.0 per
ADR-054 §7, inside the 0.x window before 1.0 freezes the names. Every
renamed token keeps its old name as a courtesy alias (see section 11).

---

## 1. The three-layer model (summary)

- **Substrate**: the token names and their meanings. Semver-public.
- **base-theme**: the beautiful default values for every token, light and
  authored dark. The root every brand inherits from. This file documents
  base-theme's values.
- **brand themes**: a delta of ~7-14 load-bearing tokens; everything else
  derives.

**`--bw-primitive-*` is build-time input only, as of 0.11.0.** The raw
colour/scale ramps behind the DTCG source are consumed by the build to
compute the semantic and component tokens documented in this file; they are
no longer emitted to `tokens.css` or available on `:root` (they were,
through 0.10.0). A consumer never references `--bw-primitive-*` directly;
every documented token in this file is the correct name to use.

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

**The load-bearing set is machine-readable** (brickwork#39): the DTCG source
carries `$extensions.bw.loadBearing` plus constraint metadata (contrast
pairs, allowed ranges) alongside each load-bearing token, and the build
emits `dist/token-manifest.json`, which holds the load-bearing set with its
constraints and the full overridable `--bw-*` vocabulary. The Python
accessor is `services/token_manifest.py`: `load_bearing()`,
`overridable_names()`, and `is_overridable()`. This file remains the
narrative reference; the manifest is the machine-checkable source of truth
for tooling (validation, the brand-CSS emitter in section 3a, brand
scaffolding).

## 3. Derivation mechanism

Derived tokens are live CSS expressions over the load-bearing set, so a brand
(or runtime tenant override) that sets `--bw-color-accent` recolours the whole
derived family in-browser with no rebuild.

- **`color-mix(in oklab, ...)` is the primary mechanism** (color-mix is
  Baseline Widely Available since Nov 2025; shipped with no fallback). Every
  tint, shade, and mix below uses it. The mix space is OKLAB, not oklch,
  deliberately: browsers give `oklch(1 0 0)` an explicit hue of 0 rather than
  a powerless one, so an oklch-space mix interpolates the hue ANGLE toward 0
  and rotates every tint (amber 58 renders at hue 4, i.e. pink). Oklab is
  rectangular: an achromatic partner (black, white, transparent, a chroma-0
  surface) scales chroma and preserves the source hue exactly, and for
  black/white shades the result is identical to the ideal oklch shade.
  Authored token VALUES stay oklch throughout (BR-BW-TOK-003 is about
  authoring notation, not the mix space).
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
  default-value edits). Hue is included: an achromatic mix partner (black,
  white, transparent, or a chroma-0 surface) is hue-powerless per CSS Color
  4, so the resolved hue equals the source token's hue, and every `$value`
  baseline carries that true resolved hue (asserted within 4 degrees
  wherever the computed chroma is perceptible, >= 0.02). Where a ramp step's
  hue drifts from the resolved hue, the baseline is a literal, not the ramp
  alias.
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

0.7.0 craft round: the components gained drawn form controls (select
indicator, checkbox/radio), solid-button borders in their own hue, input
focus halo under the a11y outline, light-theme surface top-light,
selection wash and thin scrollbars; all colour maths measured in the CSS
comments, per the owner directive that token identity alone still read
mechanical next to Radix-grade control drawing.

0.4.0 polish round: the sunken depth, muted ink, dark surface ladder, dark
intent and accent tint volumes, heading-xl weight, content measure, and dark
low-level elevation defaults were retuned per the synthesised four-critic
design review under the owner directive "brickwork is the building blocks to
build beautiful interfaces; our defaults should be beautiful"; every retuned
constant re-baselined its $value per the paragraph above.

## 3a. The brand-CSS emitter

**[NEW 0.11.0]** (brickwork#40). `render_brand_css(light, dark=None, *,
validate=True) -> str` in `services/brand_css.py` (re-exported from
`services/tokens`) takes a brand's override values (light, and optionally
dark) and emits the `:root` / `[data-theme="dark"]` override blocks a
consumer includes after `tokens.css`. With `validate=True` (the default) it
checks every supplied name against the token manifest (section 2:
overridable and not build-time-only) and enforces the fg-on-accent contrast
constraint, raising rather than emitting CSS that would ship an invalid
name or fail AA. This is the supported primitive behind BRANDING.md's
per-tenant runtime-branding recipe; this section is a pointer only, the
worked recipe (multi-tenant lookup, caching, template wiring) lives in
[BRANDING.md](BRANDING.md).

## 4. Colour

### 4.1 Surfaces

| Token | LB/D | Light derivation | Dark derivation |
|---|---|---|---|
| `--bw-color-surface` | LB | authored | authored |
| `--bw-color-surface-sunken` | D | `color-mix(in oklab, var(--bw-color-surface) 96.5%, black)` (0.4.0: deepened from 98.5%, which was indistinguishable from white; lands on gray.100) | `color-mix(in oklab, var(--bw-color-surface) 76%, black)` (dark sunken is darker than surface) |
| `--bw-color-surface-raised` | D | `var(--bw-color-surface)` (light differentiates via shadow) | `color-mix(in oklab, var(--bw-color-surface) 93%, white)` (dark differentiates via lightness) |
| `--bw-color-surface-inverse` | D | `var(--bw-color-fg)` | `var(--bw-color-fg)` |
| `--bw-color-surface-overlay` **[NEW]** | D (light) / authored (dark) | `color-mix(in oklab, var(--bw-color-surface-inverse) 50%, transparent)` | authored `oklch(0 0 0 / 0.6)`: a scrim is dark-over-content in both themes, and dark surface-inverse (`:= fg`) is near-white, so the derivation would yield a light wash |
| `--bw-color-surface-marketing-tint` **[NEW 1.2.0]** | D | `color-mix(in oklab, var(--bw-color-accent) 8%, var(--bw-color-surface))` | AUTHORED per BR-BW-TOK-002 (not mechanically derived from light): `color-mix(in oklab, var(--bw-color-accent) 12%, var(--bw-color-surface))`, mirroring the light shape (mix toward surface, not toward black like accent-subtle) since a mix-toward-black at a low percentage on an already-near-black dark surface would barely tint |

Rule: any component at elevation 2+ uses `background:
var(--bw-color-surface-raised)`, both themes.

### 4.2 Foregrounds

| Token | LB/D | Light | Dark |
|---|---|---|---|
| `--bw-color-fg` | LB | authored | authored |
| `--bw-color-fg-muted` | D | `color-mix(in oklab, var(--bw-color-fg) 62%, var(--bw-color-surface))` (0.4.0: raised from 56%; measures 5.82:1 on surface, 5.26:1 on the sunken canvas) | same shape, 72% (0.4.0: raised from 67% to companion the dimmed dark fg; 7.58:1 on surface, 6.68:1 on raised) |
| `--bw-color-fg-subtle` **[NEW]** | D | `color-mix(in oklab, var(--bw-color-fg) 37%, var(--bw-color-surface))` | same shape, 49% |
| `--bw-color-fg-on-accent` | authored | contrast pick, stays a literal; the one derived-looking token every brand must verify at 4.5:1 | authored |
| `--bw-color-fg-on-inverse` | D | `var(--bw-color-surface)` | `var(--bw-color-surface)` |
| `--bw-color-icon-muted` | D | `var(--bw-color-fg-subtle)` | `var(--bw-color-fg-subtle)` |

Contrast note: `fg-muted` text must not sit inside hover-overlaid containers.
The 4 percent hover wash (4.6) sinks muted text below AA; muted copy inside a
hoverable row or item either steps up to `fg` on hover or lives outside the
overlaid element.

### 4.3 Borders

| Token | LB/D | Light | Dark |
|---|---|---|---|
| `--bw-color-border` | LB | authored | authored |
| `--bw-color-border-strong` | D | `color-mix(in oklab, var(--bw-color-border) 94%, black)` | **direction flips**: `color-mix(in oklab, var(--bw-color-border) 86%, white)` (a dark theme's emphasis border must get lighter) |
| `--bw-color-border-control` **[NEW]** | D | `color-mix(in oklab, var(--bw-color-fg) 44%, var(--bw-color-surface))` (measured 3.23:1 on the default surface) | `color-mix(in oklab, var(--bw-color-fg) 45%, var(--bw-color-surface))` (measured 3.38:1 on the 0.4.0 graphite surface) |

`border-control` exists because the divider border token stays deliberately
light for calm chrome, while an input or control boundary is a visual cue
WCAG 1.4.11 requires at 3:1 against the adjacent surface. Inputs, selects,
and similar controls take `border-control`; dividers and card outlines keep
`border`.

### 4.4 Accent

| Token | LB/D | Light | Dark |
|---|---|---|---|
| `--bw-color-accent` | LB | authored | authored |
| `--bw-color-accent-hover` | D | `color-mix(in oklab, var(--bw-color-accent) 89%, black)` | `color-mix(in oklab, var(--bw-color-accent) 88%, black)` |
| `--bw-color-accent-subtle` | D | `color-mix(in oklab, var(--bw-color-accent) 7%, var(--bw-color-surface))` | `color-mix(in oklab, var(--bw-color-accent) 30%, black)` (0.4.0: lowered from 40% so selection recedes behind content) |
| `--bw-color-focus-ring` | D | `color-mix(in oklab, var(--bw-color-accent) 95%, black)` | `color-mix(in oklab, var(--bw-color-accent) 82%, black)` |

`accent-hover` is retained as the flat-colour fallback; transient hover
feedback on non-accent surfaces uses the state overlays (4.6), which is why a
brand whose hover is "a brightness shift" authors zero hover tokens.

### 4.5 Intents (danger / success / warning / info)

Six tiers per intent so an alert, badge, or toast never invents a value.
`X` ranges over `danger`, `success`, `warning`, `info`.

| Token | Tier | LB/D | Light | Dark |
|---|---|---|---|---|
| `--bw-color-X` | base | LB (info: authored cyan default, `:= accent` is the documented 3-role collapse) | authored | authored |
| `--bw-color-X-subtle` | tinted bg | D | `color-mix(in oklab, var(--bw-color-X) 7%, var(--bw-color-surface))` | `color-mix(in oklab, var(--bw-color-X) P%, black)` (danger 26%, success 23%, warning 22%, info 26%; 0.4.0: lowered from 41/37/36/42 so the dark tints whisper like light; X-fg measures 7.22 to 10.77 on them) |
| `--bw-color-X-border` **[NEW]** | tinted border | D | `color-mix(in oklab, var(--bw-color-X) 30%, var(--bw-color-surface))` (the badge/alert border, replacing invented inline mixes) | `color-mix(in oklab, var(--bw-color-X) 55%, black)` (clears the black-mixed subtle tint by delta-L >= 0.08, verified 0.184-0.254) |
| `--bw-color-X-strong` **[NEW]** | border/emphasis | D | `color-mix(in oklab, var(--bw-color-X) 88%, black)` | **flips**: `color-mix(in oklab, var(--bw-color-X) 96%, white)` |
| `--bw-color-X-fg` **[NEW]** | text on `X-subtle` | D | `color-mix(in oklab, var(--bw-color-X) P%, black)` (danger 88%, success 84%, warning 83%, info 85%), landing on the 700 ramp depth: the base itself fails AA on the subtle tint, the mix measures 5.84 / 4.70 / 4.67 / 5.17 | `color-mix(in oklab, var(--bw-color-X) 78%, white)` (lightness boost for AA on the dark tint) |
| `--bw-color-X-on-fg` **[NEW]** | text on solid `X` | authored | `oklch(1 0 0)` for danger only (4.83, passes); near-black ink for warning, success, and info (white fails AA on the solid amber, green, and cyan bases: 3.19, 3.32, 3.83) | authored per hue, same rule (all four take near-black ink: the dark bases sit on the lighter 400/500 ramp steps, where white fails AA) |

The dark `subtle` tier (accent included) mixes toward **black**, not the
surface, a correction from the draft: the authored 950-ramp tints carry far
more chroma than a mix with the near-achromatic dark surface can reach
(ΔC ≈ 0.04 at any lightness-correct constant), and because the dark surface
is not chroma-free its 265 hue would dominate the interpolated hue, dragging
a danger tint toward violet. Mixing toward black preserves the intent hue
(black's hue is powerless) and reaches the authored depth.

**Branding note:** the account-menu's destructive item renders `danger-fg`
text on `surface-raised` in dark. The default pair passes AA comfortably,
but a brand whose dark `danger` is darker than about L 0.62 pushes the
derived `danger-fg` (78% toward white) below AA on the raised surface; such
a brand must re-verify the account-menu danger-on-raised pair and, if
needed, author `--bw-color-danger-fg` directly.

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
background resolved). Disabled: opacity remains the mechanism
(`opacity: var(--bw-component-disabled-opacity)`, was
`--bw-disabled-opacity` through 0.10.0, kept as a courtesy alias), with the
nav item as the one documented exception, re-coloured via
`--bw-component-nav-item-disabled-text`
instead (no opacity stacking).

**Contrast note:** `fg-muted` text must not sit inside hover-overlaid
containers; the 4 percent wash sinks it below AA (see 4.2).

### 4.7 Component roles (flat names in 0.3.0; component tier in 0.11.0)

The nav, breadcrumb, and skeleton per-component colour roles re-tier from
`--bw-color-*` to `--bw-component-*` in 0.11.0 (each row's "was" name is
kept as a courtesy alias). They remain theme-variant: the derivation
mechanism, load-bearing status, and computed values below are unchanged,
only the names move.

| Token | LB/D | Light | Dark |
|---|---|---|---|
| `--bw-component-nav-item-active-bg` (was `--bw-color-nav-item-active-bg` through 0.10.0; kept as a courtesy alias) | D | `var(--bw-color-accent-subtle)` | same |
| `--bw-component-nav-item-active-text` (was `--bw-color-nav-item-active-text` through 0.10.0; kept as a courtesy alias) | D | `var(--bw-color-accent-hover)` | **branches**: `color-mix(in oklab, var(--bw-color-accent) 25%, white)` (a high-lightness accent step; the light-mode borrow of accent-hover fails contrast on the dark tint) |
| `--bw-component-nav-item-active-border` (was `--bw-color-nav-item-active-border` through 0.10.0; kept as a courtesy alias) | D | `var(--bw-color-accent)` | same |
| `--bw-component-nav-item-disabled-text` **[NEW]** (was `--bw-color-nav-item-disabled-text` through 0.10.0; kept as a courtesy alias) | D | `var(--bw-color-fg-subtle)` | same |
| `--bw-component-nav-section-text` **[NEW]** (was `--bw-color-nav-section-text` through 0.10.0; kept as a courtesy alias) | D | `var(--bw-color-fg-muted)` | same |
| `--bw-component-breadcrumb-current` **[NEW]** (was `--bw-color-breadcrumb-current` through 0.10.0; kept as a courtesy alias) | D | `var(--bw-color-fg)` | same |
| `--bw-component-breadcrumb-separator` **[NEW]** (was `--bw-color-breadcrumb-separator` through 0.10.0; kept as a courtesy alias) | D | `var(--bw-color-fg-subtle)` | same |
| `--bw-component-skeleton-bg` (was `--bw-color-skeleton-bg` through 0.10.0; kept as a courtesy alias) | D | `color-mix(in oklab, var(--bw-color-surface-sunken) 96%, black)` (0.4.0: constant retuned 94% to 96% to hold the gray.200 landing, one step deeper than the deepened 96.5% sunken) | **direction flips**: `color-mix(in oklab, var(--bw-color-surface-sunken) 82%, white)` |
| `--bw-component-skeleton-shimmer` (was `--bw-color-skeleton-shimmer` through 0.10.0; kept as a courtesy alias) | D | `color-mix(in oklab, var(--bw-component-skeleton-bg) 96%, black)` | **direction flips**: `color-mix(in oklab, var(--bw-component-skeleton-bg) 86%, white)` |

## 5. Elevation

Six levels, values adopted from Tailwind 4's `--shadow-*` ramp (industry
consensus geometry), colours expressed in oklch, dark variants authored
(shadows vanish on dark surfaces: higher alpha, plus a faint inset top
highlight at every level from 1 to fake ambient light; 0.4.0 extended the
highlight from levels 3+ down to 1 and 2 at fainter alphas, so dark cards
get depth instead of outlines only). Theme-variant: light values on `:root`,
dark under `[data-theme="dark"]`.

| Token | Light | Dark |
|---|---|---|
| `--bw-elevation-0` | `none` | `none` |
| `--bw-elevation-1` | `0 1px 2px 0 oklch(0 0 0 / 0.05)` | `0 1px 2px 0 oklch(0 0 0 / 0.3), inset 0 1px 0 0 oklch(1 0 0 / 0.03)` |
| `--bw-elevation-2` | `0 1px 3px 0 oklch(0 0 0 / 0.1), 0 1px 2px -1px oklch(0 0 0 / 0.1)` | `0 1px 3px 0 oklch(0 0 0 / 0.36), 0 1px 2px -1px oklch(0 0 0 / 0.3), inset 0 1px 0 0 oklch(1 0 0 / 0.04)` |
| `--bw-elevation-3` | `0 4px 6px -1px oklch(0 0 0 / 0.1), 0 2px 4px -2px oklch(0 0 0 / 0.1)` | `0 4px 6px -1px oklch(0 0 0 / 0.4), 0 2px 4px -2px oklch(0 0 0 / 0.3), inset 0 1px 0 0 oklch(1 0 0 / 0.04)` |
| `--bw-elevation-4` | `0 10px 15px -3px oklch(0 0 0 / 0.1), 0 4px 6px -4px oklch(0 0 0 / 0.1)` | `0 10px 15px -3px oklch(0 0 0 / 0.45), 0 4px 6px -4px oklch(0 0 0 / 0.35), inset 0 1px 0 0 oklch(1 0 0 / 0.05)` |
| `--bw-elevation-5` | `0 20px 25px -5px oklch(0 0 0 / 0.1), 0 8px 10px -6px oklch(0 0 0 / 0.1)` | `0 20px 25px -5px oklch(0 0 0 / 0.5), 0 8px 10px -6px oklch(0 0 0 / 0.4), inset 0 1px 0 0 oklch(1 0 0 / 0.06)` |

**Component map:** card / auth panel / centred panel / data-table wrap
resting = 1 (auth and centred panels: 2, they sit alone on a sunken page);
interactive card hover = 2; dropdown, popover, account-menu panel = 3 (the
fix for the hardcoded `0 4px 12px` literal); mobile drawer panel and modal
= 4; toast = 5; topbar = border-only by default (a brand may add 2). The
modal, toast, and popover entries are forward-looking (each row lands
with its component); the card row shipped in 0.5.0 (_card.html).

## 6. Spacing, radius, borders, z-index, sizing

### 6.1 Spacing (`--bw-space-*`; values are Tailwind `--spacing` multiples)

Was `--bw-size-space-*` through 0.10.0; kept as a courtesy alias. Values
unchanged.

Shipped: `0, 1 (0.25rem), 2 (0.5), 3 (0.75), 4 (1), 5 (1.25), 6 (1.5),
8 (2), 10 (2.5), 12 (3)`.
New: `px (1px)`, `0-5 (0.125rem)`, `1-5 (0.375rem)`, `7 (1.75rem)`,
`9 (2.25rem)`, `11 (2.75rem)`, `16 (4rem)`, `20 (5rem)`, `24 (6rem)`.

`-0-5` (not `-px`) replaces the hardcoded `2px` gaps/paddings so they scale
with root font size; `-px` exists for true hairline spacing that must not
scale. `-11` deliberately equals the touch-target minimum. No negative ramp
(use `calc(var(--bw-space-N) * -1)` at the point of use).

### 6.2 Radius (`--bw-radius-*`)

Was `--bw-size-radius-*` through 0.10.0; kept as a courtesy alias. Values
unchanged.

Shipped: `sm 0.25rem, md 0.375rem, lg 0.5rem, full 9999px`.
New: `none 0`, `xl 0.75rem`, `2xl 1rem` (Tailwind-aligned values).

**Component map:** skeleton sm; button, input, nav link, form-errors,
badge-square md; card, auth/centred panel, filter bar, alert, dropdown,
account-menu panel lg (0.4.0: alert up from md to join the stacked card
family; dropdown and account-menu panel down from xl so the panel radius
is concentric with its item radius); popover, toast, modal xl; badge,
avatar, pill full. The
card, modal, toast, popover, avatar, pill, and badge-square entries are
forward-looking (each lands with its component); the card row shipped in
0.5.0.

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
| `--bw-color-focus-ring` | derived default; tenant accents receive an explicit `render_brand_css()` value verified at ≥3:1 against every relevant surface in the theme (WCAG 1.4.11) |

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

The icon-size scale is `--bw-component-icon-size-*` (was, through 0.10.0,
two duplicate names for the same values, `--bw-icon-size-*` and
`--bw-size-icon-*`; both are kept as courtesy aliases, and 0.11.0 dedups
them to the single component-tier name). This is the scale itself (`-sm`
through `-2xl`); it is distinct from the inline instance property
`--bw-icon-size` (no step suffix, set per-icon by `{% bw_icon %}`), which is
unchanged and is not a scale token.

The un-infixed component tokens below (button radius, icon stroke width,
content max-width, topbar position, disabled opacity, menu min-width,
select indicator, checkbox glyph, stat-tile value size, drawer width, toast
max-width, htmx indicator opacity) move to the `--bw-component-*` grammar in
0.11.0; each row below carries its "was" name as a courtesy alias.

| Token | Value | Notes |
|---|---|---|
| `--bw-component-icon-size-2xl` **[NEW]** | `2.5rem` | empty-state hero icons; was `--bw-icon-size-2xl` / `--bw-size-icon-2xl` through 0.10.0, kept as courtesy aliases |
| `--bw-size-control-height-sm` **[NEW]** | `2rem` | fixed, not density-scaled (sm × compact would break touch targets) |
| `--bw-size-control-height-md` **[NEW]** | `var(--bw-density-control-height)` | alias of the density token |
| `--bw-size-control-height-lg` **[NEW]** | `3rem` | fixed |
| `--bw-size-touch-target-min` **[NEW]** | `2.75rem` | WCAG 2.5.5 floor; never density-scaled |
| `--bw-size-max-width-prose` **[NEW]** | `65ch` | long-form measure |
| `--bw-size-max-width-form` **[NEW]** | `32rem` | formalises the empty-state body literal |
| `--bw-size-max-width-modal-sm` **[NEW]** | `28rem` | matches the auth panel |
| `--bw-size-max-width-modal-md` **[NEW]** | `32rem` | |
| `--bw-size-max-width-modal-lg` **[NEW]** | `48rem` | |
| `--bw-component-drawer-width` **[NEW]** | `min(20rem, 80vw)` | formalises the drawer literal; was `--bw-drawer-width` through 0.10.0, kept as a courtesy alias |
| `--bw-component-menu-min-width` **[NEW]** | `12rem` | minimum width for dropdown-shaped panels; the account-menu literal becomes its consumer; was `--bw-menu-min-width` through 0.10.0, kept as a courtesy alias |
| `--bw-component-toast-max-width` **[NEW 0.9.0]** | `24rem` | toast readable measure; the ramp has no step between modal-sm (28rem) and the drawer width, and a toast wants a narrower glanceable line; was `--bw-toast-max-width` through 0.10.0, kept as a courtesy alias |
| `--bw-component-stat-tile-value-size` **[NEW 0.5.0]** | `var(--bw-font-size-3xl)` | stat tile numeral size (VIZ-001); a live reference so the font scale cascades, and the `size` modifiers re-point it per tile; was `--bw-stat-tile-value-size` through 0.10.0, kept as a courtesy alias |
| `--bw-component-select-indicator` **[NEW 0.7.0]** | chevron SVG data URI | select dropdown indicator, drawn at a mid-grey that reads as decorative on both themes; was `--bw-select-indicator` through 0.10.0, kept as a courtesy alias |
| `--bw-component-checkbox-glyph` **[NEW 0.7.0]** | tick SVG data URI (alpha mask) | consumed via mask-image and painted with `fg-on-accent`, so the glyph stays AA in both themes; was `--bw-checkbox-glyph` through 0.10.0, kept as a courtesy alias |
| `--bw-component-icon-stroke-width` | `2` | shipped, previously undocumented; the stroke width for the icon set; was `--bw-icon-stroke-width` through 0.10.0, kept as a courtesy alias |
| `--bw-component-content-max-width` | `72rem` | 0.4.0: was `none`; a default measure cap so bands stop degrading into full-bleed wires on wide monitors (invisible at 1280px); a consumer overrides it, including back to `none`. Token itself was `--bw-content-max-width` through 0.10.0, kept as a courtesy alias |
| `--bw-component-content-max-width-marketing` **[NEW 1.2.0]** | `80rem` | ADR-055 marketing tokens: a wider content cap than the app shell's content-max-width (72rem), since a marketing canvas wants a wider column than a console. Used by `shell/marketing.html`'s content wrapper. Was `--bw-content-max-width-marketing` at the raw name before the `bw-component-*` rename applied at build time; the raw name is not kept as an alias (introduced post-0.10.0, so no prior consumer depends on it) |
| `--bw-component-section-gap-marketing` **[NEW 1.2.0]** | `4rem` | ADR-055 marketing tokens: the vertical rhythm between stacked marketing sections (hero, feature grid, pricing, CTA), larger than the app's `--bw-density-section-gap` (2rem comfortable) since marketing pages read as fewer, more generous blocks. Density-agnostic (not itself part of the density axis) |
| `--bw-component-logo-height` **[NEW, unreleased]** | `2rem` | brickwork#83 (ADR-054 beautiful-by-default): the default cap the marketing shell applies to an `img`/`svg` dropped into `brand_logo` or `brand_wordmark` (block-size capped, width follows the intrinsic ratio), so an unconstrained mark/lockup renders at a sensible header size out of the box instead of a full-height banner. 2rem is the 32px end of the conventional 28-32px header-logo range. Applied through the brickwork-owned `.bw-marketing-header__brand-mark` / `__brand-wordmark` wrappers at zero specificity (`:where`), so a one-class consumer rule overrides it; or override the token itself to resize. Raw `--bw-logo-height` ships as a build alias of the canonical name |
| `--bw-component-topbar-position` | `sticky` | shipped, previously undocumented; a consumer sets `static` to unstick the topbar; was `--bw-topbar-position` through 0.10.0, kept as a courtesy alias |

The `--bw-size-icon-*` / `--bw-icon-size-*` duplication (0.3.0 added `2xl`
under both names for parity, deferring the dedup) resolves in 0.11.0: both
collapse to the single `--bw-component-icon-size-*` name, per the tier
re-grammar in section 4.7.

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
| `heading-display` **[NEW 1.2.0]** | display | 5xl | tight | bold | tight |
| `heading-2xl` | display | 2xl | tight | bold | tight |
| `heading-xl` | display | xl | tight | semibold (0.4.0: was bold; 600 at 24px is the product-chrome cut, 2xl keeps bold for true display use) | tight |
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
title heading-md; table th overline voice: xs semibold wide-tracked
uppercase fg-muted (0.4.0: was label; the header band now reads as column
apparatus, not a first data row; td body-sm; definition-mode label column
body-sm + fg-subtle); field label label, help and errors caption; button
label label; badge caption size at medium weight, tabular-nums; marketing hero
heading heading-display, marketing section heading heading-xl (1.2.0,
ADR-055 marketing tokens, `brickwork.marketing`); nav link
body-sm (0.4.0: was body-md; chrome sits a step below content), nav
section-label overline (uppercase at the component); breadcrumbs body-sm +
fg-muted, current crumb breadcrumb-current; account-menu item body-sm
(0.4.0: was body-md, completing the 14px chrome scale), secondary line
caption; pagination status caption + fg-muted; dialog/modal title
heading-sm. The dialog/modal entry is forward-looking (it lands with the
component); the card-title row shipped in 0.5.0 (_card.html, heading-md).

## 8. Motion

### 8.1 Durations (`--bw-duration-*`) **[NEW]**

`instant 1ms` (fires transitionend, unlike 0), `fast 100ms`, `normal 200ms`,
`moderate 250ms`, `slow 400ms`, plus loop timings `shimmer 1500ms`,
`spin 700ms` (formalising the two hardcoded loops).

0.9.0 interaction-set additions (MINOR, section 11):

| Token | Value | Use |
|---|---|---|
| `--bw-duration-toast-short` **[NEW 0.9.0]** | `4000ms` | toast auto-dismiss, `duration="short"` (CBH-009); read by `bwToast` via getComputedStyle, never a transition timing |
| `--bw-duration-toast-normal` **[NEW 0.9.0]** | `6000ms` | toast auto-dismiss, the `"normal"` default |
| `--bw-duration-toast-long` **[NEW 0.9.0]** | `10000ms` | toast auto-dismiss, `duration="long"` |
| `--bw-debounce-search` **[NEW 0.9.0]** | `300ms` | the combobox server-filter debounce window (CBH-019 path); JS-consumed, retunable in the token layer without touching templates |

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
| `--bw-component-disabled-opacity` | `0.5` | existing value unchanged; was `--bw-disabled-opacity` through 0.10.0, kept as a courtesy alias |
| `--bw-opacity-muted` **[NEW]** | `0.7` | de-emphasis that is not disabled; conservative floor, re-verify contrast per use |
| `--bw-opacity-sort-idle` **[NEW]** | `0.4` | names the shipped sort-caret literal (decorative only) |
| `--bw-component-htmx-indicator-opacity` **[NEW 0.9.0]** | `0.6` | STA-006 in-flight dimming of an htmx swap target via the `htmx-request` class convention; between disabled (0.5) and muted (0.7) so in-flight never reads as disabled; was `--bw-htmx-indicator-opacity` through 0.10.0, kept as a courtesy alias |

## 10. Reserved names (documented, deliberately not shipped)

`--bw-avatar-size-{sm,md,lg,xl}`, `--bw-aspect-ratio-avatar`,
`--bw-aspect-ratio-media`, `--bw-motion-scale`, `--bw-backdrop-blur`,
`--bw-focus-ring-offset-color`, `--bw-opacity-backdrop` (superseded by
`--bw-color-surface-overlay`), `--bw-font-size-scale-multiplier`. Each ships
only when a real consumer names the need (YAGNI; ADR-054 §6).

**Marketing tokens (v1.2.0, shipped).** ADR-055 §6 named the likely-new design
surface for the opt-in `brickwork.marketing` sub-app, and the four tokens it
anticipated have landed as MINOR additions (ADR-054 §8), entered into their
matching sections above rather than kept as one-off marketing-scoped classes:
`--bw-text-heading-display-*` (a `heading-display` type role, §7.4),
`--bw-component-content-max-width-marketing` and
`--bw-component-section-gap-marketing` (§6.6), and
`--bw-color-surface-marketing-tint` (§4.1). Marketing-scoped CSS classes are
used only where a token would be the wrong shape (a layout construct, not a
themeable value, e.g. `.bw-hero`, `.bw-pricing-tier`). See ADR-055 in the
umbrella (`oss/docs/adrs/ADR-055-brickwork-marketing-kit-opt-in-subapp.md`)
and the wider trajectory this opens
(`oss/docs/plans/brickwork-templates-catalogue-direction.md`).

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

**0.11.0 tier re-grammar:** the space, radius, icon-size, and component
tiers were renamed as a batch (`--bw-space-*`, `--bw-radius-*`,
`--bw-component-icon-size-*`, `--bw-component-*`), each old name kept as a
courtesy alias per ADR-054 section 7, exercising the "relaxed to direct
minors inside 0.x" allowance above while the grammar is still free to move
before 1.0 freezes the names.

## 12. Tailwind projection (`tailwind-theme.css`) **[NEW 0.10.0]**

**Authority:** ADR-054 section 4 (the hybrid: brickwork owns `--bw-*`,
projects into `@theme`), amended into the umbrella spec
(`04-interfaces.md`, 0.10.0) and verified by AC-BW-095. Through 0.9.0 the
shipped `tailwind-theme.css` was a placeholder (self-referential `--bw-*`
identity mappings, which sit in no Tailwind utility namespace and generate
no utilities); from 0.10.0 it is the real projection.

The fragment is a single `@theme inline` block mapping the semantic
`--bw-*` contract into Tailwind 4's utility namespaces, so a consumer's
own utilities (`bg-accent`, `rounded-md`, `shadow-3`, `text-heading-lg`,
`p-4`) inherit the brand. Every mapped value is a `var(--bw-*)` reference,
never a literal, and `inline` means Tailwind bakes those references
straight into the generated utilities: switching `data-theme` or
`data-bw-brand` recolours consumer utilities live, with no rebuild.

### 12.1 Consumption

Import the fragment in the consumer's entry CSS AFTER the line that pulls
in Tailwind itself, alongside `tokens.css` (which supplies the `--bw-*`
values the projection references):

```css
@import "tailwindcss";
@import "<static path>/brickwork/dist/tokens.css";
@import "<static path>/brickwork/dist/tailwind-theme.css";
```

### 12.2 Namespace coverage

| Tailwind namespace | Mapped from | Count | Example utility |
|---|---|---|---|
| `--color-<name>` | every semantic `--bw-color-<name>` | 51 | `bg-accent`, `text-fg-muted`, `border-danger-border` |
| `--radius-<step>` | every `--bw-radius-<step>` (was `--bw-size-radius-<step>` through 0.10.0) | 7 | `rounded-md`, `rounded-full` |
| `--shadow-<level>` | the elevation ladder `--bw-elevation-<level>` | 6 | `shadow-3` |
| `--text-<role>` + `--text-<role>--line-height` | the type roles `--bw-text-<role>-size` / `-line-height` | 12 roles (24 keys) | `text-heading-lg`, `text-body-md` |
| `--font-<name>` | the font stacks `--bw-font-family-<name>` | 3 | `font-sans`, `font-display`, `font-mono` |
| `--spacing` | the dynamic base `--bw-space-1` (was `--bw-size-space-1` through 0.10.0) | 1 | `p-4`, `gap-2`, `mt-8` |
| `--default-font-family`, `--default-mono-font-family` | `--bw-font-family-sans` / `-mono` | 2 | preflight body and code text |

94 declarations in total, regenerated by `npm run build:tokens` from the
same token data as `tokens.css`, never hand-listed.

Collision posture: the semantic colour names ADD to Tailwind's palette
rather than replacing it (`bg-accent` joins `bg-blue-500`; a consumer may
still want a raw palette colour for one-off content). `--font-sans` and
`--font-mono` override Tailwind's same-named defaults deliberately, so the
brand stacks win; `--radius-*` steps land on Tailwind's own step names
with brickwork's values. The one global override is `--spacing` (12.3).

### 12.3 The `--spacing` base trick

The space scale is authored as Tailwind `--spacing` multiples of `0.25rem`
(section 6.1), which is deliberate: projecting the SINGLE dynamic base
(`--spacing: var(--bw-space-1)`, was `--bw-size-space-1` through 0.10.0,
kept as a courtesy alias) makes every numeric spacing utility compute
through the brand token (`p-4` becomes `calc(var(--bw-space-1) * 4)` under
`@theme inline`). Defaults are byte-for-byte Tailwind's rhythm (`p-4` is
still `1rem`), yet a brand or density override of `--bw-space-1` rescales
the whole utility grid live. The raw `--bw-space-<n>` steps are NOT
projected individually: the dynamic base covers the entire numeric scale.

### 12.4 Exclusions (deliberate)

The projection is the semantic visual contract only, per the tier rule.
NOT projected: component-tier tokens (a consumer styles components through
the components, not by borrowing their internals as utilities), state
overlays, z-index (brickwork's layer ladder is not a consumer utility
scale), opacity, motion (durations, easings, composite transitions), the
focus ring geometry tokens `--bw-focus-*` (accessibility floors are never
restyled through utilities; the focus ring COLOUR is a semantic colour and
projects with that family as `--color-focus-ring`), density tokens (they
flow through the semantic tokens they feed), border
widths, icon sizes, and the raw primitive ramps and raw font scales (the
type roles and font stacks are the consumer surface). The `--bw-*` names
remain the authored contract; a Tailwind namespace change is a
projection-layer change, not a contract break (ADR-054 section 4).
