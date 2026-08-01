# Changelog

All notable changes to brickwork are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
semantic versioning. Template block names, HTMX target IDs, Alpine component
names, event names and token names are treated as public API (see the spec's
versioning contract).

## [Unreleased]

## [0.6.0] - 2026-08-01

The topbar layout release: CSS for the shell's existing `layout` ARG
(the-wall SHL-001, CORE). Additive and CSS-only; nothing renamed or removed,
no template restructuring: both layouts share one DOM.

### Added

- **Topbar-primary layout styling** for `shell/app.html`'s existing
  `layout="topbar"` ARG (previously the attribute rendered with no styling
  behind it). Under `[data-layout="topbar"]` the app becomes a single column:
  the sidebar restyles into a full-width horizontal nav band directly under
  the sticky topbar (hairline below instead of at the inline end, background
  unchanged), the top-level nav list flows as a wrapping inline row, links
  keep their radius/hover/active treatment with the 3px active marker moved
  from the leading edge to the bottom edge (same token), section labels
  render inline as overline separators, and the switcher slot sits inline at
  the row start with its hairline rotated to the trailing edge. Nested nav
  lists stay vertically stacked inside their parent item (no dropdown JS on
  the no-JS floor; a documented limitation). Below the `md` breakpoint the
  band hides exactly as the sidebar column does and the mobile drawer takes
  over, unchanged, in either shape. Every new rule is scoped under the
  attribute, so the sidebar layout's defaults are untouched.
- a11y gate: `list-topbar-light`/`list-topbar-dark` fixtures render the real
  list page in the topbar layout, so the axe (WCAG 2.2 AA) suite covers the
  band, the bottom active marker, the inline section labels, and the inline
  switcher slot in both themes.
- testapp: a `?layout=` context passthrough (validated to
  `sidebar`/`topbar`) so every harness page can render either shell shape.

## [0.5.0] - 2026-07-31

The pages release: the blocks include the rooms, not just the bricks
(spec: umbrella docs/specs/django-brickwork, merged as PR #115). Additive;
nothing renamed or removed.

### Added

- **Card** (`components/_card.html`): five semver-public regions
  (`card_header`/`card_title`/`card_actions`/`card_body`/`card_footer`),
  elevation-1 resting, `interactive`/`href` variant raising to elevation-2 on
  the raised surface (no transform), `bordered` flat variant, density-aware
  padding with `padding="sm|md|lg"` modifiers. An unfilled region emits no
  markup.
- **Stat tile** (`components/_stat.html`): label (overline voice), value on
  the new `--bw-stat-tile-value-size` token with tabular numerals, optional
  `trend`/`trend_label`/`icon`/`href`/`loading`/`size`. A trend ALWAYS
  renders a directional glyph plus a visually-hidden text fallback, so
  direction never rides on colour alone, even past a direction-less
  `trend_label` (BR-BW-TPL-007).
- **Page patterns** (`patterns/list.html`, `detail.html`, `dashboard.html`):
  extend-only compositions of the existing components with minimal
  semver-public block contracts; each renders a complete page with only its
  required context (BR-BW-TPL-006). Internal `patterns/_table_card.html`
  glue provides the card-wrapped table defaults.
- **Nav slot** (#21): `sidebar_switcher` and `mobile_nav_switcher` blocks in
  `shell/app.html`, empty by default, seated in a styled
  `bw-sidebar__switcher` container; brickwork ships the slot, never the
  switcher (BR-BW-NAV-007).
- Pattern scaffolding CSS: `bw-stat-grid` (responsive stat row),
  `bw-section-stack`, and a `bw-visually-hidden` utility.
- A scoped test suite for AC-BW-070..078; the seams testapp list page now
  extends the list pattern, a new dashboard page extends the dashboard
  pattern, and the axe gate covers both composed pattern pages in light and
  dark.

## [0.4.0] - 2026-07-31

The polish round. Owner directive on 0.3.0: "a lot tighter, but I am sure we
can go much further." Four design lenses (chrome, typography, components,
gestalt) critiqued the real rendered screenshots; the synthesis ships as
value-only retunes: no token, class, or block renamed or removed, every
changed text/border pair numerically re-verified for WCAG 2.2 AA in both
themes, all 77 derivation baselines recomputed and green.

### Changed

- **Chrome**: the light shell is now a white frame on a perceptible sunken
  canvas (light `surface-sunken` deepens to the gray-100 step, light
  `fg-muted` rises to hold AA on it); the dark theme moves from a black void
  to a graphite ladder (`surface` anchor lifts to oklch(0.18), `fg` softens
  to 0.93, every dark derived baseline re-anchored, `border-control`
  re-verified at 3.38:1); dark intent tints and `accent-subtle` calm down;
  dark elevation 1 and 2 gain the inset top highlight; empty sidebar
  header/footer regions are suppressed and the first nav row shares the
  topbar centreline.
- **Typography**: nav links and the account menu drop to the body-sm chrome
  scale; `heading-xl` moves to semibold (heading-2xl stays bold); table
  headers take the uppercase, tracked overline voice (definition-table keys
  deliberately keep sentence case); a **content-typography floor** styles
  unclassed h1-h6, p, ul and ol inside `.bw-content` onto the type roles via
  zero-specificity `:where()` rules, so consumer-authored markup lands on
  the hierarchy out of the box (any consumer CSS still wins).
- **Components**: a scoped `box-sizing: border-box` reset for all `bw-`
  classes (fixes the clipped full-width input; the library is now correct
  without a consumer preflight); forms, fields and the error summary cap at
  the 32rem measure with a proper actions row; field errors and the
  required marker move to the text-duty `danger-fg` tier; the error summary
  joins the tinted-border family with a styled list; primary and danger
  buttons gain resting elevation and a pressed inset; ghost buttons recede
  to muted ink; the nav badge becomes a quiet bordered chip; tables gain
  tabular numerals, last-row border cleanup, hover-revealed sort carets and
  a prose-capped definition card; alerts and menu panels join the radius-lg
  card family; `--bw-content-max-width` defaults to 72rem with a centred
  content column.

### Deliberately declined

- Topbar backdrop blur (the `--bw-backdrop-blur` name stays reserved) and an
  accent-coloured nav badge; both recorded in the critique synthesis.

## [0.3.0] - 2026-07-31

Beautiful by default (ADR-054 Phase a). The founding statement made real: a
developer who installs brickwork and writes no theme gets a genuinely designed
dashboard, in light and dark. Additive and non-breaking: 168 tokens added,
zero renamed or removed; every 0.2.4 name, class, block, and context variable
keeps working. Default LOOK values change throughout (a MINOR under the
value-change rule, gated by the axe WCAG 2.2 AA run in both themes).

### Added

- **The complete token vocabulary** (`docs/DESIGN.md` is the canonical
  reference): a six-level elevation scale (`--bw-elevation-0..5`, light plus
  authored dark with inset ambient highlights), state overlays
  (`--bw-state-hover-overlay` / `-active-overlay` / `-selected-bg`), surface
  additions (`surface-overlay` scrim, `fg-subtle`), six-tier intents
  (`-border`, `-strong`, `-fg`, `-on-fg` join base and `-subtle` for
  danger/success/warning/info), `border-control` (WCAG 1.4.11-compliant input
  boundary), focus geometry (`--bw-focus-ring-width/-offset/-style`), a named
  z-index scale (`--bw-z-*`), motion (`--bw-duration-*`, `--bw-ease-*`,
  composite `--bw-transition-*`), twelve type roles
  (`--bw-text-<role>-{family,size,line-height,weight,tracking}`), font-scale
  extensions (2xs/3xs and 3xl/4xl/5xl, new line-heights and tracking), spacing
  infill (px, 0-5, 1-5, 7, 9, 11, 16, 20, 24), radius none/xl/2xl, border
  widths, control heights, touch-target minimum, max-widths, four density
  tokens (topbar-height, section-gap, card-padding, page-gutter-inline), nav
  and breadcrumb roles, and `--bw-menu-min-width`.
- **Live derivation**: derived colour tokens are emitted as `color-mix(in
  oklab, ...)` expressions over the load-bearing set, so a brand that authors
  ~7 tokens (surface, fg, border, accent, danger, success, warning) gets the
  whole family recoloured in-browser with no rebuild. Every derived token
  remains individually overridable; a derivation-verification test recomputes
  each expression against its `$value` baseline (L, C, alpha, and hue).
  Mixes run in oklab deliberately: browsers give `oklch(1 0 0)` an explicit
  hue of 0, so oklch-space mixing rotates tint hues toward 0.
- **Breadcrumbs** (#25): `components/_breadcrumbs.html` fills the reserved
  `breadcrumbs` block; last crumb always unlinked with `aria-current="page"`,
  separators carry empty accessible text, renders nothing without crumbs.
- **Account menu** (#25): `components/_account_menu.html` fills
  `topbar_account_menu`; a native details/summary disclosure (no JS, no ARIA
  menu roles by design), elevation-3 raised panel, fade-in-up entrance,
  optional `menu_open` initial-open flag, danger item at AA on the raised
  surface in both themes.
- **Multi-view active state** (#20): `NavItem.active_url_names` widens active
  matching to secondary view names (the link target stays `url_name`;
  placed last in the field list so 0.2.4 positional construction is safe).
  `validate_nav_config` rejects `active_url_names` without `url_name`.
- **Selected rows**: `rows[].selected` adds `bw-data-table__row--selected`
  consuming `--bw-state-selected-bg` (stacking: zebra, then selected, then
  hover overlay).

### Changed

- **Every component consumes the vocabulary**: tables become elevation-1
  cards with a sunken header band, zebra striping (even rows, records variant
  only) and hover overlays; buttons gain pressed states, per-variant hovers,
  and label-role typography; inputs gain the compliant boundary, hover/focus
  border treatment, and disabled styling; alerts and badges use the intent
  tier tokens (tinted borders, `-fg` text at AA on the tints); empty states,
  page headers, form errors, pagination, skeletons, the filter bar, the auth
  panels, the drawer, and the nav all adopt elevation, type roles, motion
  tokens, and state overlays. Every hardcoded 1px/2px/3px, z-index,
  box-shadow, duration, easing, font-size and weight literal is now a token.
- **z-index values renumbered** onto the named scale: topbar 10 to 20
  (sticky), drawer 20 to 30, skip link 100 to 60. A consumer who layered
  custom chrome against the old literals should re-check stacking against
  `--bw-z-*`.
- **Focus ring** reaches `summary` elements (account-menu and drawer
  triggers) and is fully tokenised; geometry is an accessibility floor, only
  its colour is brand-tunable (at 3:1 minimum).
- Font stacks completed additively (Noto Sans plus emoji fallbacks in sans,
  Courier New in mono).

### Fixed

- Nav specificity defect: hovering the active item no longer replaces the
  active tint (overlays now layer on top of it).
- Disabled nav rows align with enabled rows (transparent marker border) and
  no longer stack colour dimming with opacity.
- Skeleton visibility on the sunken workspace background.
- Reduced motion: the spinner freezes to `animation: none` and the
  account-menu caret stops transitioning under `prefers-reduced-motion`.

### Documentation

- `docs/DESIGN.md`: the complete token reference (values, derivations,
  component maps, semver rules). Records one deliberate correction to
  ADR-054 section 3: custom-property fallback emission does not work as
  described, so 0.3.0 ships color-mix only, no relative-colour syntax.
- README status, BRANDING.md (the seven-token brand contract with a worked
  light+dark example), frontend/README.md, tokens source README,
  CONTRIBUTING.md and SECURITY.md placeholder fills, pilot adoption brief.

## [0.2.4] - 2026-07-31

Pilot-driven ergonomics, correctness fixes, and a docs sweep, from the agentpm
and consentics breadth rounds plus the icvlocal demo. No breaking changes; all
additions are optional and the sort-key change is back-compatible.

### Fixed

- **Theme wiring: the shell is no longer silently unstyled** (#22). The shell
  reads `bw_theme` / `bw_density` / `bw_dir` / `bw_lang`, but
  `resolve_theme_attributes` returns `theme` / `density` / `dir` and no language,
  so a consumer dropping the service output straight into context got an
  unstyled shell with no error. Ships a ready-made context processor
  `brickwork.context_processors.theme` that maps the service output onto the
  `bw_*` names and adds `bw_lang` (from the active language); add it to
  `TEMPLATES[...]["OPTIONS"]["context_processors"]` and the shell is wired with
  no hand mapping. An optional `BRICKWORK_THEME_RESOLVER` setting (dotted path)
  supplies per-user/per-tenant theming.
- **`_data_table.html` sortable columns need only `sort_key` now** (#23). Sorting
  previously required the undocumented `sort_key_desc` and `next_sort` column
  keys; without them a header rendered but did not sort, silently. The template
  now derives the descending key (`-<sort_key>`) and the next-click toggle from
  `sort_key` plus the shared `current_sort`, so a consumer supplies only those
  two. Passing an explicit `sort_key_desc` / `next_sort` still overrides the
  convention (back-compatible).
- **`tokens/__init__.py` docstring named the Tailwind bridge `theme.css`** (#26);
  the shipped file is `tailwind-theme.css`. A consumer copying the path got a
  404. One-line docstring correction.

### Added

- **`_filter_bar.html` component** (#15). A structure-only inline bar of
  consumer-supplied filter fields above a list/table: each field renders
  through `forms/_field.html`, with a documented `hx-get`/`hx-target` swap
  contract for progressive enhancement and a no-JS `<form method="get">` floor.
  No new JavaScript.
- **`_data_table.html` definition-list mode** (#18). `variant="definition"`
  renders a key/value fact table for one entity (a detail screen's "facts about
  this thing", the `<dl>`-shaped case) from `rows=[{label, value}]`, with the
  label as a proper `<th scope="row">` and the same token styling as the
  columnar table. The default `variant="records"` is unchanged.
- **`_data_table.html` clickable rows** (#10). A record row with a `url` now
  renders its first cell as a link to that URL (the documented `rows[].url` key
  previously did nothing). A linked row gets the `bw-data-table__row--linked`
  class.
- **`NavItem.kwarg_name`** (#19). The declarative common case of
  `url_kwargs_from_request`: copy one route parameter from the active route into
  an item's reverse kwargs. `kwarg_name="slug"` copies same-named;
  `kwarg_name=("project_slug", "slug")` reads the source name the route uses and
  reverses under the target name the item's URL expects, so an app that names
  the same parameter differently across routes no longer hand-writes a fallback
  callable. `url_kwargs_from_request` stays for genuinely complex cases and wins
  when both are set.

### Documentation

- README gains a **Usage** section documenting the tag-vs-`{% include %}`
  distinction (which components are `{% bw_* %}` tags vs structural includes) and
  the `{% bw_icon %}` decorative/label requirement (#11).

## [0.2.2] - 2026-07-31

### Fixed
- `{% bw_icon %}` and the loading spinner are now actually sized by their size
  token (#16). Both put the `--bw-icon-size-*` token into the SVG's `width` and
  `height` **attributes**, but SVG geometry attributes do not accept CSS
  `var()`, so the value was invalid and dropped: every icon fell back to the
  300x150 SVG default and `size="sm|md|lg|xl"` (ICO-004) had no visible effect.
  The size is now applied as the `--bw-icon-size` CSS custom property (set inline
  on the SVG), which `.bw-icon` / `.bw-spinner` read for their `inline-size` /
  `block-size`. The size stays token-driven (density and brand aware) and RTL
  correct via logical properties. Tests assert the token is applied as the custom
  property and that no `width="var("` / `height="var("` attribute is emitted.

## [0.2.1] - 2026-07-31

### Fixed
- `--bw-color-info*` no longer resolves to the same value as `--bw-color-accent*`
  (#13). Both semantic roles mapped to the same blue primitive, so `info` (a
  status/notice role) and `accent` (brand action) were byte-identical and
  indistinguishable in any UI that used both. `info` now maps to its own cyan
  primitive, giving it an independent hue. A regression test asserts the two roles
  differ. Found by the icvlocal demo Wall, which colour-codes by role.

## [0.2.0] - 2026-07-30

Adoption round: four findings from the agentpm pilot (the second, no-JS,
object-scope-authorised consumer) resolved. All additive and backward-compatible.

### Added
- **Route-parameter-dependent nav URLs** (#5). `NavItem` gains
  `url_kwargs_from_request(resolver_match) -> dict`, an optional callable that
  derives reverse kwargs from the current request's route at render time and
  merges them over the static `url_kwargs`. This lets a project-scoped item
  (`projects/<slug>/documents/`) live in the sidebar even though `<slug>` is only
  known per request. `{% bw_nav %}` is now `takes_context=True` and reads
  `request.resolver_match` automatically. If the kwargs are not yet available, the
  item follows `BRICKWORK_NAV_FALLBACK` like any unresolvable URL, never a 500.
- **Typography tokens** (#7). New `--bw-font-family-{sans,display,mono}` plus a
  `--bw-font-size-*` / `--bw-font-weight-*` / `--bw-font-line-height-*` scale. The
  shell and page-header consume them, so an app rebrands its typeface token-first
  (override `--bw-font-family-sans`) instead of reaching into brickwork's classes.
  Default is a neutral system-font stack.
- **`docs/BRANDING.md`** (#8): a token-first branding guide covering colour
  bridging from a lean palette (which tokens are safe to collapse), the
  typography tokens, and the four axes, including how to bridge a
  `prefers-color-scheme` / Tailwind `dark:` app onto brickwork's `data-theme`
  contract (which stays required so dark stays authored-not-derived,
  BR-BW-TOK-002).

### Changed
- **`NavContext.permission_checker` is now optional** (#6), defaulting to
  permissive (everything visible). An app that authorises per object/scope in the
  view (RBAC, membership) no longer has to pass a stub `lambda _p: True`; it
  relies on its own mandatory view-level enforcement (BR-BW-NAV-005: nav
  visibility is display, never authorisation). Supplying a checker still works
  exactly as before. `feature_checker` was already optional.

### Fixed
- Template comments no longer render as visible text. Three shipped templates
  (`shell/base.html`, `forms/_field.html` x2) used a multi-line `{# ... #}` inline
  comment; Django's `{# #}` inline comment is single-line only, so a comment
  spanning a newline is not stripped and renders literally to the page (the
  skip-link note and the form-field aria/error notes appeared as visible text
  above every field). Converted to `{% comment %}` blocks. Two regression tests
  added: a render assertion that no comment text/markers leak, and a source-level
  guard that scans every shipped template for the multi-line-`{# #}` anti-pattern
  so the whole bug class cannot recur. Found live on the first deployed consumer
  (demo.vendablyconnect.com).

### Fixed
- `collectstatic` no longer fails for consumers using a `ManifestStaticFilesStorage`
  (the standard production static storage, incl. WhiteNoise's compressed-manifest
  variant). The generated `tailwind-theme.css` header comment contained an example
  `@import "tailwindcss"`; Django/WhiteNoise rewrite `@import`/`url()` targets by
  regex WITHOUT skipping comments, so it was treated as a real reference to a
  non-existent `brickwork/dist/tailwindcss` and raised `MissingFileError`,
  breaking every consumer's `collectstatic`. The comment is reworded to describe
  the import in prose, and a regression test asserts no shipped CSS carries an
  `@import "..."` or resolvable `url(...)`. Found by the first external consumer
  (icvlocal.com) adopting 0.1.0.

First release: the Phase-0 vertical slice. Within the `0.x` grace window per the
spec's versioning discipline, the contracts stay stable-in-intent but are not yet
1.0-guaranteed (1.0 signals both v1 pilots have cut over).

### Added

Phase 0: the v1 vertical slice. Proves the substrate end-to-end (115 Python
tests + 9 axe/no-JS checks green, coverage 99.67%).

- **Icon registry + `{% bw_icon %}`** (contract: token/template): a name -> SVG
  registry (the public contract) seeded from a curated Lucide subset (ISC +
  MIT-for-Feather, both in `NOTICE`). Injection-safe (name-referenced, never raw
  `|safe`), a11y-enforced (decorative XOR label, ICO-007; icon-only button
  requires an accessible name, ICO-008), loud on an unknown name (ICO-013),
  RTL-flip for directional icons (ICO-014), size tokens (ICO-004).
- **Token layer** (contract: token): DTCG source -> Style Dictionary ->
  stable-named `tokens.css` (`--bw-*` on `:root` + `[data-theme="dark"]` +
  `[data-density=*]`), a Tailwind `@theme inline` bridge, and a JS re-export.
  oklch, dark authored not derived (BR-BW-TOK-002/003), four composable axes.
- **App shell** (`shell/app.html`, `auth.html`, `centred.html`) with named
  blocks and a working no-JS floor (BR-BW-HTMX-001): no `<script>` in the bare
  shell, native `<details>` sidebar toggle + mobile drawer, a skip link, logical
  CSS properties throughout for RTL.
- **Navigation** (contract: navigation): `NavItem`/`NavContext` dataclasses (with
  `badge`, `external_url`, and a section-header variant), a `resolver_match`-based
  active-route resolver (never `path.startswith`), duplicate-key validation at
  import, host-injected permission/feature/policy visibility, and a `safe_reverse`
  that never 500s. Recursive `nav/_nav.html` via Django 6.0 `{% partialdef %}`.
- **Components**: button (icon-only a11y, loading spinner), badge, alert, page
  header, empty state (no-data/no-results), pagination, and a structure-only
  `data_table` (server-side sort, stable per-row swap ids; not virtualisation).
- **Forms + the 422 HTMX contract** (contract: interaction): an accessible field
  renderer (`aria-invalid`/`aria-describedby` on the input), and the
  `hx-target="this" hx-swap="outerHTML"` 422 validation swap, with a full-page
  no-JS fallback that is itself a working page.
- **Theme axes**: `resolve_theme_attributes` (settings defaults + a host
  `theme_resolver`, optional per-tenant logo), exercised for dark mode + density.
- **CI**: the load-bearing accessibility gate is now real (axe-core WCAG 2.2 AA
  against the rendered pages in light AND dark, plus a no-JS floor suite and a
  keyboard check), and the frontend build gate rebuilds + verifies the artefacts.

### Notes
- Flat `BRICKWORK_DEFAULT_*` settings (theme/density/dir + `NAV_FALLBACK`),
  default theme `light`.
- Interaction primitives (modal, toast, dropdown, combobox) are intentionally
  NOT in this slice; they are consentics-only and land later, tagged
  `[v1-single-consumer]`.

### Changed
- Scaffold reconciliation: `saas_ui` -> `brickwork` throughout (app config, template
  and static paths), and the settings shape moved from a nested `BRICKWORK` dict
  to the flat `BRICKWORK_DEFAULT_*` documented in the spec.
