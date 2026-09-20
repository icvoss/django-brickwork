# Appearance grammar: closed options for beautiful defaults

**Status:** active (beautiful-defaults suite Phases 0 to 5 complete;
icvoss/django-brickwork#533 / #540). Phase 4 P1 and Phase 6 P2 leftovers stay
deferred under INTERFACE-SYSTEM / ROADMAP with explicit N/A below.  
**Governs:** closed appearance axes on brickwork components.  
**Companions:** [DESIGN.md](DESIGN.md) (tokens), [VISUAL-BAR.md](VISUAL-BAR.md)
(craft bar), ADR-057 §1a (section arrangement axes), ADR-060 (one name per
concept), ADR-056 (pages stay consumer-owned).

## Goal

A consumer composes finished interfaces from brickwork alone: every component
is beautiful at its default, and where chrome must vary they pick **closed
options**, never hand-written layout CSS or one-off HTML wrappers.

Site composition remains ADR-056 page assembly (which sections, order, copy,
brand tokens). Site composition does **not** invent component chrome.

## Two option classes

| Class | Examples | Mechanism |
|---|---|---|
| **CSS-only** | `surface`, `elevation`, `size`, `radius`, `band`, `width` | Root modifier classes only (ADR-057). No markup forks. |
| **Region recipes** | `header_recipe`, `footer_recipe`, `media_recipe` | Package may emit region chrome for the common flat case. Root also carries a modifier so consumer-owned `.bw-*__header` / `__footer` / `__media` wrappers share the same look. `{% extends %}` blocks still win for rich content. |

Brand colour stays in tokens. `surface="inverse"` uses
`--bw-color-surface-inverse` / `--bw-color-fg-on-inverse`, never a hex string.
Open colour strings and arbitrary CSS class dumps are refused.

## Shared axes

Components adopt only the axes that apply. Silence in a template header means
unsupported, never ignored.

| Axis | Closed values | Meaning |
|---|---|---|
| `surface` | `default` \| `raised` \| `tint` \| `inverse` \| `muted` | Fill family from `--bw-color-surface*` / marketing tint / inverse |
| `elevation` | `0` \| `1` \| `2` \| `3` | Shadow ladder (`--bw-elevation-*`). Default per component stays authored |
| `size` | `sm` \| `md` \| `lg` (+ component extras e.g. modal `full`) | Scale; already common |
| `radius` | `default` \| `sm` \| `lg` \| `xl` \| `none` | Corner scale via `--bw-card-radius` (card). `default` / `lg` omit the modifier |
| `header_recipe` | `none` \| `plain` \| `bordered` \| `muted` \| `inverse` \| `accent` | Header region recipe (not the `header` **block**) |
| `footer_recipe` | `none` \| `plain` \| `muted` \| `actions` | Footer region recipe (not the `footer` **block**) |
| `media_recipe` | `none` \| `bleed` \| `inset` \| `icon` | Media region recipe (not the `media` **block**) |
| `band` | `tint` \| `plain` | Marketing band background (ADR-057) |
| `width` | `contained` \| `bleed` | Marketing measure vs full bleed (ADR-057) |
| `tone` | `muted` \| `strong` | Divider hairline weight (Beat Phase B) |
| `spacing` | `sm` \| `md` \| `lg` | Divider vertical rhythm (Beat Phase B) |
| `shape` | `circle` \| `square` | Avatar corner treatment (Beat Phase B) |
| `density` | `comfortable` \| `compact` | Table / list row density (Beat Phase C) |
| `variant` | per-component | Status / behavioural treatment; validated when `component=` names a registered set (chip, callout, button_group) |
| `align` / `placement` / `media_placement` | existing | Layout axes unchanged (ADR-060) |

**Naming.** Region **blocks** stay `media`, `header`, `footer`, `title`,
`actions`, `body` (ADR-077). Region **recipes** use the `_recipe` suffix so one
word never means both "content slot" and "appearance treatment" (ADR-060).

## Validation

Include-consumed components cannot raise from plain HTML. They call
`{% bw_options %}` (backed by `brickwork.appearance.validate_options`), which
raises `TemplateSyntaxError` on an unknown axis or value. Omitted options use
the component's authored default and stay silent.

Tag-backed components keep validating in their own Python signatures; shared
vocabularies live in `brickwork.appearance` so spellings do not drift.

## Composition contract (card, finished)

`_card.html` is complete for appearance. No further axes are planned on card.

1. **CSS-only axes** (`surface`, `elevation`, `size`, `radius`) always apply as
   root modifiers, including when a consumer uses an extend-and-include filler
   (kwargs pass through).
2. **Recipes** emit package-owned chrome for the common flat include case.
   Unfilled regions still emit no empty markup (AC-BW-070). Optional escaped
   `body` and `caption` strings cover the one-paragraph include path.
3. **Include-path header action:** `action_label` (+ optional `action_href`)
   emits a ghost sm button in the header. Suppressed when the whole card is an
   `href` link (no nested interactive content). On `header_recipe="inverse"`
   and `surface="inverse"`, that ghost uses `--bw-color-fg-on-inverse` so it
   keeps WCAG AA contrast against the inverse fill (ghost's default
   `fg-muted` does not).
4. **Include-path media:** `media_recipe` with `media_src` / `media_alt` (bleed
   or inset) or `media_icon` (icon). Rich media stays `{% block media %}`.
5. **`{% block %}` wins** for rich content. Root recipe modifiers still style
   consumer-owned `.bw-card__header` / `__footer` / `__media` when present.
6. **Rich body, forms, multi-action clusters** stay extends-only. Prefer
   `footer_recipe="muted"` (or `plain`) with `caption` for metadata; use
   `footer_recipe="actions"` with an extends filler that places real buttons
   in `{% block footer %}`.

## Defaults and VISUAL-BAR

Defaults must pass [VISUAL-BAR.md](VISUAL-BAR.md) on package-default theme (no
brand pack) for the surfaces each component appears on. Default craft changes
are consumer-visible: name them in CHANGELOG in consumer terms.

**Card resting craft.** The zero-kwargs card keeps hairline + radius-lg +
elevation-1. On light theme it also draws a soft ambient under the elevation
token and a slightly stronger edge (`color-mix` of fg into surface) so the
card reads on a white page canvas. Dark theme stays on the plain elevation
ramp. Recipes and elevation modifiers keep those axes; they do not require
kwargs for the everyday case.

## Adoption note

Card is the finished first adopter (icvoss/django-brickwork#535). Beat Phase B
(icvoss/django-brickwork#542) extends the grammar with `tone`, `spacing` and
`shape`, and registers per-component `variant` (and chip `size`) sets via
`COMPONENT_OPTIONS` in `brickwork.appearance`. Beat Phase C
(icvoss/django-brickwork#543) adds `density` and per-component surface /
header / footer recipe subsets on empty_state, page_header, data_table,
list_item and modal. Axes that do not apply stay explicitly N/A rather than
inventing a local spelling.

## Beat Phase C: variant depth (callable compositions)

Each winner family ships at least three package compositions. Examples may
demonstrate them; inventing layout that is not reachable by a package option
or first-class include does **not** count.

| Family | Compositions (callable) |
|---|---|
| Hero | `_hero.html` `media_placement="below"` (default), `"behind"`, `"beside"`, `"above"`; `eyebrow_tone` accent/sentence; `media_shape` default/circle (#672) |
| Features | `_feature_grid.html` (icon grid); `_feature_rows.html` (alternating); `_feature_list.html` (checklist) |
| Case / result list | `_case_list.html` (ruled figure | name + note rows; optional whole-row link) |
| Methods | `_methods.html` (quiet columns; underline text link, no card chrome) |
| Outcomes | `_outcomes.html` (quiet equal columns; optional section foot text link; no cards, no stages) |
| Directory | `_directory.html` (numbered index with optional mark, linked title, description and meta column) |
| CTA | `_cta.html` (centred band); `_cta_split.html` (mid-page split); `_cta_bleed.html` (inverse full-bleed). Orthogonal: `_cta.html` `width="bleed"` / `band` / `align` center (default) / start (#697) |
| Pricing | `_pricing_table.html` single tier; `_pricing_table.html` multi-tier; `_comparison_table.html` (marketing `_pricing_comparison.html` wrapper) |
| Stats | `_stat_band.html` `align` center (default) / start (#673); `chrome` card (default) / plain (#694). Pair start + plain for airy proof figures |
| Section shell | `.bw-section` / `__inner`; shared intro `.bw-section__overline` / `__heading` / `__lede` (#695); helper `_section_intro.html` |
| Person | `_portrait.html` (`align="start"` default / `"end"`, constrained 3:4 image + CTAs); `_bio.html` (compact strip, optional profile link). Not `_testimonial.html` and not the Editorial author archetype |
| Empty state | `variant="no_data"` framed (default); `variant="no_results"`; `surface="plain"` (unframed page scale). Nested: `size="sm"` |
| Page header | plain default; `surface="tint"`; breadcrumbs + actions via the public `breadcrumb` / `actions` blocks |
| Table / list | `_data_table.html` `variant="records"`; `variant="definition"`; `density="compact"`. List: `_list_item.html` (+ `density="compact"`) |
| Modal | size ladder `sm` / `md` / `lg` / `full`; `header_recipe` plain / muted / bordered; `footer_recipe` plain / muted / actions |
| Slide-over | size ladder `sm` / `md` / `lg`; `header_recipe` plain / muted / bordered; `footer_recipe` plain / muted / actions (same recipes as modal; Beat Phase E) |

## Phase 5: long-tail adoption (Should cleared or N/A)

Suite Phase 5 (beat Phase E long-tail) is done when every catalogue component
and shell either **adopts** the shared Should axes that apply, or records an
explicit **N/A** here. Default craft raised in Beat Phase A counts as clearing
a Should that asked for authored resting look without a new closed axis. Do
not invent local spellings; do not absorb craft into Brickwork Theme.

Status values:

| Status | Meaning |
|---|---|
| Adopted | Closed axis (or first-class composition) ships and is validated |
| N/A (defaults) | Should was resting craft; authored in Phase A/B without a new axis |
| N/A (keep lean) | Suite said keep lean; no shared axis |
| N/A (compose) | Satisfied by composing another component (usually card) |
| N/A (local) | Component-local `variant` / `size` / layout axis already covers the job |
| N/A (deferred) | Missing P1/P2 primitive; tracked outside this suite |

<!-- phase5-adoption:start -->

### Catalogue components

| Component | Status | Notes |
|---|---|---|
| account_menu | N/A (defaults) | Panel elevation/radius authored with dropdown in Phase A |
| alert | N/A (local) | `variant` already tints; denser padding authored Phase A; shared `surface` refused |
| article_meta | Adopted | First-class editorial byline composition; no shared axis (keep lean) |
| avatar | Adopted | `size`, `shape` via `{% bw_options %}` |
| avatar_group | N/A (local) | `size` / overlap craft; no extra shared axis |
| badge | N/A (local) | Intent via `variant`; soft/outline `tone` stays Could |
| bio | N/A (local) | Marketing person strip; Phase C depth family |
| breadcrumbs | N/A (defaults) | Current-page weight authored |
| bulk_actions_bar | N/A (defaults) | Matches filter_bar surface craft from Phase A |
| button | N/A (defaults) | Primary elevation/press authored; full-width `block` refused (consumer layout) |
| button_group | Adopted | `variant` segmented/attached; `size` |
| callout | Adopted | `variant` closed set |
| card | Adopted | Full grammar (Phase 1 pilot); locked |
| case_list | N/A (local) | Ruled figure / name / note rows (#674); optional whole-row link; not a feature-grid variant |
| chart_card | N/A (compose) | Extends `_card.html`; appearance axes stay on card |
| chart_data_table | N/A (defaults) | Header chrome shares data_table tokens |
| chip | Adopted | `variant`, `size` |
| code | N/A (defaults) | Muted/raised panel authored; line numbers stay Could |
| combobox | N/A (defaults) | Listbox panel matches dropdown craft |
| comparison_table | Adopted | `highlighted` (0-based index or plan name); emits `__col--highlighted` |
| cta | Adopted | `band`, `width` (ADR-057); `align` center (default) / start (#697) |
| cta_bleed | N/A (local) | First-class Phase C composition (inverse bleed) |
| cta_split | N/A (local) | First-class Phase C composition |
| data_table | Adopted | `density`; muted header + row hover authored Phase A/C |
| date_picker_chrome | Adopted | Field/panel chrome only; no date engine (BR-BW-INPUT-004) |
| disclosure | N/A (local) | `variant` bordered/divided; card framing refused |
| directory | N/A (local) | Marketing numbered index; list data, not shared surface |
| divider | Adopted | `tone`, `spacing` |
| dropdown | N/A (defaults) | Panel elevation/radius authored Phase A |
| dropzone | N/A (defaults) | Dashed/raised default authored Phase A |
| empty_state | Adopted | `surface` framed/plain; `variant`, `size` |
| faq | N/A (defaults) | Bordered disclosure defaults authored Phase A |
| feature_grid | N/A (local) | Finished card defaults Phase A; per-item `surface` refused (use card). Grid `variant` cards (default) / bordered (#646); item slots eyebrow / meta / badge / cta_label / pending (#641) |
| feature_list | N/A (local) | Phase C checklist composition |
| feature_rows | N/A (local) | Phase C alternating composition |
| filter_bar | N/A (defaults) | Raised surface + field rhythm authored Phase A |
| gauge | N/A (defaults) | Track/rail contrast authored |
| hero | N/A (local) | `align`, `media_placement`; optional `decoration` safe-HTML/block watermark (#645); optional `subheading` / `meta` / `meta_items`, `eyebrow_tone`, `media_shape` (#672); optional `band` refused (behind already inverse) |
| input_group | Adopted | Lean; prefix/suffix text and icons; no closed appearance axes |
| list_item | Adopted | `density` |
| logo_cloud | N/A (defaults) | Quieter spacing authored Phase A |
| marketing_footer_groups | N/A (local) | P0 shipped; groups/columns are data, not shared surface |
| methods | N/A (local) | Quiet columns band (#675); not a feature-grid variant; no shared surface |
| outcomes | N/A (local) | Quiet outcome columns (#696); section foot link; sibling of methods, not a variant |
| mobile_nav_toggle | N/A (keep lean) | Shell seam only |
| modal | Adopted | `size`, `header_recipe`, `footer_recipe` |
| page_header | Adopted | `surface` default/tint |
| pager | N/A (defaults) | Matches pagination craft |
| pagination | N/A (defaults) | Hit targets/spacing authored |
| portrait | N/A (local) | Phase C person composition; `align` |
| preview_frame | N/A (keep lean) | Surface-guarded specimen; fill locked to `--bw-color-surface` |
| pricing_comparison | N/A (compose) | Thin include of `_comparison_table.html` (#626) |
| pricing_table | N/A (local) | Tier count is data; highlighted recipe on tier |
| pricing_tier | N/A (local) | `highlighted` raises elevation; shared `surface`/`elevation` refused |
| progress | N/A (keep lean) | Single authored track; consumer drives `--bw-progress-value` |
| proof_collage | N/A (local) | Marketing proof section; band/width local |
| ranked_list | N/A (compose) | Empty path uses `_empty_state`; list itself stays unframed |
| scorecard | N/A (defaults) | Gap/padding tokens authored; `columns` stays consumer grid |
| search | N/A (defaults) | Field chrome in topbar authored |
| section | Adopted | Shared marketing shell/inner; `width` contained/bleed, `band` plain/tint (ADR-057 §1a, #667); shared intro classes (#695) |
| site_footer | Adopted | Shared site chrome (ADR-113); measure/band via `.bw-site-footer*` |
| site_header | Adopted | Shared site chrome (ADR-113); measure/band via `.bw-site-header*`; overlay stays marketing-shell-only |
| skeleton | N/A (local) | `variant` text/title/row/block is the preset set |
| slide_over | Adopted | Same recipes as modal (Beat Phase E) |
| sparkline | N/A (keep lean) | |
| spinner | N/A (compose) | Size follows host control icon token; not standalone |
| section_intro | N/A (compose) | Helper that emits `.bw-section__*` intro classes (#695) |
| stat | Adopted | `size`; `chrome` card (default) / plain (#694) |
| stat_band | N/A (defaults) | Tint band + tile elevation authored Phase A; `align` center (default) / start (#673); forwards `chrome` (#694) |
| stat_comparison | N/A (local) | Same size ladder as stat |
| stepper | N/A (defaults) | Current/complete states authored |
| tabs | N/A (local) | `variant` underline/pill; soft panel Could |
| tag_input | N/A (compose) | Chip look shared with `_chip` via tokens/CSS |
| testimonial | N/A (defaults) | Card framing authored Phase A |
| theme_switch | N/A (keep lean) | |
| toast | N/A (defaults) | Elevation/edge authored Phase A; optional `surface` refused |
| toast_region | N/A (local) | `placement` only |
| toc | Adopted | `{% bw_toc %}` / `_toc.html`; reuses `.bw-docs-toc` chrome; `items`, `active`, `heading` |
| toggle | N/A (keep lean) | |
| token_specimen | N/A (keep lean) | Theme specimen; not kit chrome variation |
| tooltip | N/A (keep lean) | |
| trend_indicator | N/A (keep lean) | |
| version_switch | N/A (local) | Docs version disclosure; not shared surface |

### Shells

| Shell | Status | Notes |
|---|---|---|
| base | N/A (defaults) | Focus/skip craft only |
| app | N/A (defaults) | Sidebar selected/hover + topbar elevation Phase A |
| auth | N/A (defaults) | Panel elevation/radius Phase A |
| centred | N/A (defaults) | Same panel craft as auth |
| docs | N/A (defaults) | Rail active + article measure Phase A; on-this-page via `{% bw_toc %}` (#627) |
| marketing | N/A (defaults) | Header/footer craft; footer groups component shipped |

### Phase 4 P1

Owner demand ruling 2026-09-17: former "demand-gated" scheduling language is
stale for the viable-primitives cut. `timeline` and `saved_views` stay
deferred under ADR-092. The other P1 rows shipped as Adopted in the
viable-primitives integration (`input_group`, `date_picker_chrome`,
`comparison_table`, `toc`, `article_meta`).

| Missing | Status | Notes |
|---|---|---|
| timeline | N/A (deferred) | ADR-092 / INTERFACE-SYSTEM |
| saved_views | N/A (deferred) | ADR-092 / INTERFACE-SYSTEM |
| input_group | Adopted | See catalogue row; ships this release |
| date_picker_chrome | Adopted | Chrome/panel only; engine stays consumer |
| comparison_table | Adopted | See catalogue row; ships this release |
| toc | Adopted | See catalogue row; ships this release |
| article_meta | Adopted | See catalogue row; ships this release |

### Phase 6 P2 (deferred; explicit N/A)

| Missing | Status | Notes |
|---|---|---|
| command_palette | N/A (deferred) | ROADMAP Wave 5 / #156 |
| notification_list | N/A (deferred) | ROADMAP Wave 5 |
| popover | N/A (deferred) | Refuse while dropdown covers most cases |
| newsletter_band | N/A (deferred) | Marketing demand |

<!-- phase5-adoption:end -->
