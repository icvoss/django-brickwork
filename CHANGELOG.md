# Changelog

All notable changes to brickwork are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
semantic versioning. Template block names, HTMX target IDs, Alpine component
names, event names and token names are treated as public API (see the spec's
versioning contract).

## [Unreleased]

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
