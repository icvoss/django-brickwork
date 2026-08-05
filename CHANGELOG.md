# Changelog

All notable changes to brickwork are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
semantic versioning. Template block names, HTMX target IDs, Alpine component
names, event names and token names are treated as public API (see the spec's
versioning contract).

## [Unreleased]

### Added

- **System check for the missing theme context processor**
  (icvoss/django-brickwork#101). The top documented support trap (#22, a
  silently unstyled shell when `brickwork.context_processors.theme` is absent
  from TEMPLATES) now warns at startup: `brickwork.W001` fires when
  `brickwork` is installed but no DjangoTemplates backend lists the processor.
  A deliberate non-shell consumer (components or marketing layers only)
  silences it with `SILENCED_SYSTEM_CHECKS = ["brickwork.W001"]`.
- **A console warning when `registerBrickworkComponents(Alpine)` was never
  called** (icvoss/django-brickwork#87). Registration now stamps
  `data-bw-js-registered` on `<html>`, and with `DEBUG = True` the shell
  appends a small inline detector (gated on the new `bw_debug` context
  variable the theme context processor sets from `settings.DEBUG`): interactive
  `x-data="bw..."` markup plus a running Alpine with no stamp emits a console
  warning pointing at INTEGRATION.md, turning the silent dead-components trap
  into an actionable message. Production pages ship no script at all; a
  consumer can override the new `bw_js_registration_check` block (e.g. for a
  nonce-strict dev CSP). A new `assertBrickworkRegistered()` export offers the
  opt-in hard check.

### Changed

- **`IconNotFoundError` no longer subclasses `KeyError`**
  (icvoss/django-brickwork#74). Django's `{% partialdef %}` machinery catches
  a bare `KeyError`, so an unknown icon name raised inside a template partial
  (e.g. the nav's recursive `nav_item`) was masked as a misleading
  "Partial ... is not defined". The exception now subclasses `BrickworkError`
  and `LookupError`, so the real error surfaces naming the icon; unknown-icon
  messages also gain a did-you-mean hint for near-miss names. Code catching
  `IconNotFoundError` (or `LookupError`) is unaffected; code that caught it AS
  `KeyError` must catch `IconNotFoundError` itself.

### Fixed

- **Shipped templates no longer leak `string_if_invalid` markers**
  (icvoss/django-brickwork#80). `|default:` only substitutes for a
  defined-but-falsy value, so a genuinely undefined optional variable (the app
  shell's `layout`, the toast region's `position`, component variant/size/label
  defaults) rendered a consumer's `string_if_invalid` marker instead of the
  documented default. Every optional-by-design variable in the shipped
  templates now resolves via `{% firstof %}` (immune, failures ignored), with
  the same defaults; the consumer smoke leg now runs under `string_if_invalid`
  to keep it guarded. No contract change.

- **File-type icons in the registry** (icvoss/django-brickwork#88): six new
  seeded names, `video`, `audio`, `document`, `image`, `archive` and
  `spreadsheet`, so media libraries, attachment lists and file managers can
  show a per-type badge instead of falling back to the generic `file` glyph
  for every non-image asset. All resolve file-badge artwork (file outline
  plus a type marker) from the pinned lucide-static v1.28.0 seed
  (`file-play`, `file-music`, `file-text`, `file-image`, `file-archive`,
  `file-spreadsheet`), so a mixed listing reads as one family beside the
  existing `file` and `folder`. `document` deliberately shares the
  text-lines artwork the generic `file` already renders. No `pdf` name is
  seeded: Lucide ships no PDF glyph, so a consumer wanting one registers
  its own via `register_icons()`.

## [1.3.1] - 2026-08-05

### Fixed

- **The collapsed app sidebar now hides the brand wordmark and keeps the brand
  mark** (icvoss/django-brickwork#93). The collapsed rail narrows and hides its
  text labels, but the brand wordmark was left visible, so a consumer that
  filled the `brand_wordmark` block got a full-width wordmark overflowing the
  narrowed rail and clipping against the viewport edge. `shell/app.html` now
  wraps `brand_logo` in `.bw-sidebar__brand-mark` and `brand_wordmark` in
  `.bw-sidebar__brand-wordmark` (brickwork-owned wrappers, so the behaviour is
  independent of the consumer's own inner markup or classes); the collapsed CSS
  visually-hides the wordmark wrapper alongside the nav labels and keeps the
  mark, the standard icon-only-rail affordance. The expanded header layout is
  unchanged, and an unfilled block leaves an `:empty` wrapper that collapses to
  nothing.

## [1.3.0] - 2026-08-05

### Added

- **`NavItem.href`** (NAV-019): a raw, already-resolved internal path as a third
  URL source alongside `url_name` and `external_url`. Unlike `external_url` it
  renders as an ordinary on-site anchor (no external-link icon, same tab by
  default) and participates in active state by matching the current
  `request.path`. This is the seam for a CMS-managed menu whose items only expose
  `page.get_absolute_url()` paths, never Django route names.
- **`NavItem.opens_in_new_tab`** (NAV-020): a tri-state (`None`/`True`/`False`)
  new-tab flag, now an axis INDEPENDENT of whether a link is external. `None`
  (default) keeps the historical behaviour byte-for-byte (external links open a
  new tab, internal links do not); an explicit bool forces either way, so an
  internal link can open a new tab and an external link can stay in the same one.
  Mirrors a CMS menu item's own `open_in_new_window` flag. The external-link
  ICON stays tied to genuine externality (`external_url`), decoupled from the
  new-tab decision.
- `validate_nav_config` now rejects an item that sets more than one of
  `url_name` / `external_url` / `href` (previously the "mutually exclusive"
  contract was documented but unenforced).

### Fixed

- **`{% bw_nav %}` now validates a `NavItem.icon` at prepare time** and raises a
  clear `IconNotFoundError` naming the offending icon, instead of letting an
  unregistered name reach `{% bw_icon %}` inside `nav/_nav.html`'s recursive
  `{% partialdef %}` (icvoss/django-brickwork#89). Django's template-partials
  machinery swallowed the `IconNotFoundError` raised mid-partialdef and
  re-surfaced it as a misleading `Partial 'nav_item' is not defined in the
  current template.`, pointing consumers at the wrong cause entirely. A
  registered icon is unaffected; only a bad name changes behaviour (from a
  misleading error to an accurate one). Adds `brickwork.icons.has_icon(name)`, a
  non-raising companion to `get_icon`.

## [1.2.0] - 2026-08-03

The marketing kit: an opt-in `brickwork.marketing` sub-app (ADR-055) that brings
marketing pages onto the same `--bw-*` token, brand, and accessibility contract
as the console. Additive and backwards compatible: a bare `brickwork` install
(the sub-app not in `INSTALLED_APPS`) renders byte-identical output to 1.1.0. The
marketing surface exists only when a consumer opts in. This is the first shipping
slice of the wider templates-catalogue direction (layout variants, then themed
starter kits, both demand-gated; see the direction doc in the umbrella).

### Added

- **Marketing kit** as the opt-in sub-app `brickwork.marketing`, governed by the
  new `BR-BW-MKT-001..005` rule group (spec section 9) and documented in
  04-interfaces section 4d. Add `"brickwork.marketing"` to `INSTALLED_APPS`
  alongside `"brickwork"`. The sub-app ships no models, migrations, views, or
  URLs (BR-BW-MKT-001): templates, components, and static only.
- **Marketing shell** `brickwork_marketing/shell/marketing.html`: a public-site
  shell (header + primary nav + footer) extending `brickwork/shell/base.html`,
  the marketing counterpart of the app shell, with a wider content measure and
  the full no-JS floor.
- **Eight marketing components** (all `{% include %}`-consumed, clean-room on
  `--bw-*`, empty-graceful): `_hero`, `_feature_grid`, `_pricing_tier`,
  `_pricing_table`, `_cta`, `_testimonial`, `_logo_cloud`, `_stat_band`, `_faq`.
  The FAQ composes the existing `_disclosure.html` (native `<details>`, no-JS
  floor free) and the stat band composes `_stat.html` (BR-BW-MKT-004): marketing
  components reuse existing primitives rather than reimplementing them.
- **Three marketing pages** (`brickwork_marketing/pages/marketing/`):
  `landing.html`, `pricing.html`, `about.html`, each extending
  `shell/marketing.html`, composing the marketing components, empty-graceful, and
  passing axe WCAG 2.2 AA in both themes plus the no-JS render floor
  (BR-BW-MKT-002).
- **Marketing tokens** (MINOR, brand-overridable): a `heading-display` type role,
  `--bw-component-content-max-width-marketing` (80rem), a marketing section-rhythm
  token, and `--bw-color-surface-marketing-tint` (the tinted section-band surface,
  authored per theme, contrast-checked in light and dark).

### Notes

- `_cta.html` uses a `no_tint` opt-out flag (default `False`, tint on) rather than
  a `tint=True` opt-in: Django's `{% include ... with tint=page_var %}` forwards an
  absent page-level context variable as an empty string, so a default-`True` flag
  could never be turned off from a page block; a default-`False` opt-out has no such
  ambiguity.
- All new marketing block, component, and token contracts ship
  `[v1-single-consumer]` (BR-BW-VER-002) until a second consumer ratifies them,
  matching how the page kit shipped.

## [1.1.0] - 2026-08-03

The page-templates kit: a new tier one storey above the page patterns. Where a
pattern is an index or detail scaffold, a page is a whole, opinionated screen a
consuming project extends and fills, composed of the existing components and one
of the shipped shells. Additive and backwards compatible: no existing template,
block, token, or component changed behaviour.

### Added

- **Page-templates kit** (`brickwork/pages/`), governed by the new
  `BR-BW-PAGE-001..005` rule group (spec section 8) and documented in
  04-interfaces section 4c. Each page `{% extends %}` a shell, exposes a minimal
  set of semver-public named blocks (BR-BW-TPL-001), and renders a complete,
  valid document with every optional region left empty (BR-BW-PAGE-002):
  - `pages/form_page.html` (extends `shell/app.html`): a single-object
    create/edit page. One block, `form_body`; the consumer's own `<form>` wraps
    `{% bw_form form %}` and the submit button inside it. Deliberately no
    `form_actions` block, since a base template cannot wrap the consumer's
    `<form>` (BR-BW-PAGE-004).
  - `pages/settings.html` (extends `shell/app.html`): a tabbed settings area.
    Blocks `settings_nav` (a `{% bw_tabs %}` tablist, the page's reason to exist
    so not empty-graceful) and `settings_body`. The tabs contract is
    `[v1-single-consumer]`, so the page's stability is inherited-provisional
    (BR-BW-VER-002).
  - `pages/console.html` (extends `shell/app.html`): a blank-slate console. One
    block, `console_body`, defaulting to the empty-state component.
  - `pages/confirm.html` (extends `shell/centred.html`): a destructive-action
    confirmation. Blocks `confirm_body` and `confirm_actions`; a POST form plus a
    cancel link, zero JS.
  - `pages/auth_signin.html`, `pages/auth_signup.html`, `pages/auth_reset.html`
    (extend `shell/auth.html`): backend-agnostic auth pages (BR-BW-PAGE-003).
    Three separate files for discoverability, identical block shape
    (`auth_heading`, `auth_body`, `auth_secondary`). brickwork ships no
    authentication view, form, model, or URL, references no `{% url %}` that
    could 500, and names no form field, so the same page serves `allauth`,
    `django.contrib.auth`, or a custom backend identically; the consumer wraps
    its own `<form>` and drops `{% bw_form form %}` inside.

### Changed

- **Account-menu CSRF-safe sign-out** (closes
  [#73](https://github.com/icvoss/django-brickwork/issues/73)): an
  `_account_menu.html` item may now opt into a POST via a `method: "post"` key in
  its item dict (`{label, url, icon, danger, method}`). A `post` item renders a
  `<form method="post" action="...">` with `{% csrf_token %}` and a `<button>`
  styled identically to the `<a>` items (including the `danger` treatment), so a
  correct sign-out against Django's POST-only `LogoutView` (POST-only since 5.0)
  lives inside the accessible disclosure panel alongside the link items. Items
  without `method` (or `method: "get"`) render as `<a>` exactly as before: the
  change is purely additive and no existing item dict needs updating.

## [1.0.0rc1] - 2026-08-02

The first public release candidate, and the first release on public PyPI
(`pip install django-brickwork`), graduating from the private index. This is the
parity floor: the complete, spec-governed component surface built across 0.1.0 to
0.16.0, published under the five semver-governed public-API contracts. No API
change from 0.16.0; rc1 marks the surface as complete and stable-candidate.

### Ratification (BR-BW-VER-002)

- The **token, template, and navigation** contracts are exercised by both v1
  pilots and are declared **stable** at 1.0.
- The **interaction contracts** (modal, toast, dropdown, combobox, tabs,
  tooltip, slide-over) remain **`[v1-single-consumer]`**: ratified by consentics
  only, they are not yet declared stable per BR-BW-VER-002 (which requires both
  pilots). The 0.16.0 consumer smoke harness exercises them in-repo, but a
  fixture is not a second independent consumer. These stabilise in a later minor
  once a second real JS consumer (agentpm's JS layer, or vendably_v3) adopts
  them; until then they may change with a documented deprecation window even
  within the 1.x line.

### Changed

- **Public graduation**: the publish pipeline now targets public PyPI via OIDC
  trusted publishing (`.github/workflows/publish.yml`), replacing the
  private-index workflow (`publish-private.yml`, removed). `Development Status`
  is `4 - Beta` (the release-candidate tier); the README status reflects the
  complete surface. Release infrastructure and metadata only, no API change.

## [0.16.0] - 2026-08-02

Test infrastructure only: no source changes (brickwork#61).

### Added

- **Consumer smoke harness** (`tests/consumer/`, `tests/settings_consumer.py`,
  `tests/test_consumer_smoke.py`, brickwork#61): a SECOND, V3-shaped
  integration fixture alongside the existing `brickwork_testapp`/
  `settings_seams` harness, run as its own CI leg (`settings_consumer`).
  Exercises the seams every brownfield adopter hits: multi-host shell
  branding (a simulated django-hosts-style middleware resolving a tenant from
  the request host), a `BRICKWORK_THEME_RESOLVER` tenant resolver proving the
  `brickwork.context_processors.theme` mapping onto the shell's `bw_*`
  attributes per host, a waffle-style `feature_checker` gating a nav item
  (hidden when its flag is off, visible when on, reachable directly either
  way per BR-BW-NAV-005), and the full 422 HTMX form-swap loop
  (BR-BW-HTMX-003) through the `{% bw_form %}` whole-form renderer (0.15.0).
  A further page composes the wider shipped interaction/component set (a
  modal trigger, a slide-over trigger, a selectable data table, a stepper,
  and a toast trigger) so the leg catches a cross-component integration
  break, not just the four named seams.

## [0.15.0] - 2026-08-02

The two highest-cost V3 adoption gaps (#47 section 2/3): table bulk-selection
and the whole-form renderer. All additive; both are opt-in modes over the
existing structure-only primitives, so every pre-0.15.0 render is unchanged.

### Added

- **Data table bulk selection** (`_data_table.html` `selectable=True` +
  `components/_bulk_actions_bar.html` + the `bwTableSelection` Alpine
  component, brickwork#54): the row-selection contract that "must live in
  brickwork or every consumer reinvents it" (#47). Every row checkbox is a
  native `<input type="checkbox" name="selected" value="{{ row.id }}">`
  inside the consumer's own `<form>`; the no-JS floor is a plain multi-value
  POST, read server-side via `request.POST.getlist("selected")`, zero JS
  required. The bulk-actions bar is extend-consumed like `_card.html` (fill
  `bulk_actions_buttons`), always rendered, and reads the checkboxes as the
  sole source of truth when enhanced (`x-data="bwTableSelection()"` on the
  shared form): live "N selected" count (`aria-live="polite"`, translated
  server-side), header select-all with `.indeterminate` wiring. Every
  checkbox carries a visually-hidden accessible label.
- **Sticky header / scroll container** (`_data_table.html`
  `sticky_header=True` or `scroll_container=True`, brickwork#54): CSS-only,
  pins the `<thead>` while the wrap scrolls, reusing the existing
  `--bw-z-sticky` token (no new token needed).
- **Responsive stack mode** (`_data_table.html` `responsive="stack"`,
  brickwork#54): below a 48rem viewport each row renders as a labelled card
  (`data-label` per cell, stamped from the `columns` list by position); the
  `scroll` default (existing horizontal overflow) is unchanged. Backed by a
  new `list_item` template filter (`brickwork_components.py`), the only way
  to index a list by a loop counter in a Django template.
- **Whole-form renderer** (`{% bw_form %}` / `forms/_form.html`, brickwork#53,
  FRM-002/003/019): renders every visible field of a Django form through the
  same `forms/_field.html` chrome a hand-picked per-field include uses, one
  call instead of a per-field `{% include %}` loop written by hand on every
  form (V3's single largest adoption cost after the shell, per #47). Renders
  the FIELDS REGION ONLY, never a `<form>` element, matching the existing
  per-field worked example (docs/INTEGRATION.md section 4): the consumer's
  own `<form>` wraps the include and owns method/action/hx-post/hx-target/
  hx-swap/csrf_token, so the BR-BW-HTMX-003 422 swap contract (each field's
  `{{ field.auto_id }}_errors` container, `_form_errors.html` for non-field
  errors) is identical whether the form region was hand-built or rendered via
  `{% bw_form %}`. `layout="stacked"` (default, one field per row) or
  `"grid"` (an N-column CSS grid via `grid_columns=`, DOM order unchanged so
  tab order still follows source order). `rows=[["first_name", "last_name"],
  ["email"]]` (FRM-019) groups named fields side by side on one row,
  composing with either layout; a field not named in `rows` falls back to
  its own row at its original form-order position, never silently dropped.
  Hidden fields render unwrapped. `density=` sets a scoped form-only density
  override (FRM-018).

## [0.14.0] - 2026-08-02

Overlay and flow primitives, the third post-1.0 component release (#47
inventory). All additive.

### Added

- **Slide-over / side panel** (`components/_slide_over.html` + the `bwSlideOver`
  Alpine component, brickwork#55): an edge-anchored overlay panel, extend-consumed
  like `_modal.html` (fill `slide_over_title` / `slide_over_body` /
  `slide_over_footer`). Dual consumption identical to the modal: the htmx path
  swaps the consumer partial into a dedicated `#bw-slide-over-root` (new in
  `shell/base.html`, so a modal can layer over an open slide-over, the V3
  split-shell case); the no-JS floor is the same partial rendered in-flow on a
  full page. `role="dialog"` `aria-modal="true"`, `aria-labelledby` the title,
  focus-trapped and focus-returned to the invoker, Escape and scrim dismiss, the
  `HX-Trigger: bw:slide-over:close` server dismissal. `placement`
  (inline-end default / start, logical for RTL). Events `bw:slide-over:open` /
  `bw:slide-over:close`.
- **Stepper** (`components/_stepper.html`, brickwork#59): a step progress
  indicator, include-consumed, zero JS. Each step's status (complete / current /
  upcoming) is conveyed by a state glyph, colour, AND visually-hidden text
  ("(completed)" / "(current step)" / "(not started)"), never colour alone; the
  current step carries `aria-current="step"`; the connectors are `aria-hidden`.
  `orientation` (horizontal default / vertical).
- **Wizard pattern** (`patterns/wizard.html`, brickwork#59): a thin multi-step
  flow scaffold extending `shell/app.html`, with blocks for the stepper, the step
  body, and the step navigation. Server-driven: each step is its own URL
  rendering the stepper at the current position plus that step's form; a normal
  POST redirects to the next step on success or re-renders the step with inline
  errors, and Back is an ordinary link. brickwork ships the two rendering pieces
  only and tracks no wizard state (the consumer owns the forms, routing, and
  step persistence).

### Changed

- **Overlay JS shares a helper** (`frontend/src/js/overlay_shared.js`): the
  trap-engage race guard and invoker capture / restore, previously inline in
  `bwModal`, are factored out and shared by `bwModal` and `bwSlideOver`.
  `bwModal`'s public component name, config, events, and behaviour are unchanged
  (regression-verified against the existing modal suite).

## [0.13.0] - 2026-08-02

Input-chrome primitives and the sidebar collapse, the second post-1.0 component
release (#47 inventory). All additive; progressive enhancement over native form
controls (a working native control is always the no-JS floor).

### Added

- **Toggle switch** (`{% bw_toggle %}` / `components/_toggle.html`, brickwork#57,
  BR-BW-INPUT-001): a native `<input type="checkbox" role="switch">` with an
  enforced non-empty `label` (a switch with no label is a WCAG 4.1.2 failure).
  Also a `bw_field_widget` opt-in for form fields (a `CheckboxInput` carrying the
  `bw-toggle` class gets `role="switch"` stamped). `aria-checked` follows the
  checked state natively, so the switch works with zero JS.
- **Tag / chips input** (`components/_tag_input.html` + the `bwTagInput` Alpine
  component, brickwork#57, BR-BW-INPUT-002): the no-JS floor is a real submittable
  text control (a delimited tag list the server splits); Alpine enhances it into
  removable chips (reusing the combobox chip markup), Enter/comma commits,
  Backspace-on-empty removes the last chip. Events `bw:taginput:add` /
  `bw:taginput:remove`.
- **File dropzone** (`components/_dropzone.html` + the `bwDropzone` Alpine
  component, brickwork#57, BR-BW-INPUT-003): a native `<input type="file">` kept
  in the tab order (visually hidden, focusable) inside a labelled `<label>` that
  is the click target, never replaced. Alpine adds the drag-over state and a
  selected-file list; clicking to browse works with zero JS.
- **Styled native date/time inputs** (brickwork#57, BR-BW-INPUT-004): CSS chrome
  so `<input type="date|time|datetime-local">` match the other `bw-input` fields
  (border, height, focus ring, the picker indicator where the engine allows). No
  JS date-picker; the native picker and keyboard entry are the accessible
  baseline.
- **Sidebar collapse** (the `sidebar_toggle` block + the `bwSidebarCollapse`
  Alpine component, brickwork#58, BR-BW-INPUT-005): the shell ships a labelled
  toggle `<button>` (`aria-expanded`, `aria-controls="bw-sidebar"`, translated
  collapse/expand labels) that narrows the sidebar to `--bw-density-sidebar-width-collapsed`
  and hides the nav-item text labels *visually* (the clip technique), keeping
  every item and its accessible name in the a11y tree. The expanded state is the
  no-JS floor; the collapsed preference persists in `localStorage`. The width
  transition is reduced-motion gated.
- **Four toggle tokens**: `--bw-component-toggle-{track-width,track-height,thumb-size,thumb-inset}`
  (canonical grammar with courtesy aliases).

## [0.12.0] - 2026-08-02

Feedback and dashboard primitives, the first of the post-1.0 component releases
burning down the #47 inventory (all additive; the substrate contract is unchanged).

### Added

- **Skeleton** (`{% bw_skeleton %}` / `components/_skeleton.html`, brickwork#56):
  a consumer-facing skeleton placeholder wrapping the existing `.bw-skeleton` CSS.
  `variant` ("text" default | "title" | "row" | "block"), `count` (positive int),
  optional `width` / `height`. The group carries `aria-busy="true"` plus a
  visually-hidden "Loading" text; each shape is `aria-hidden="true"`; the shimmer
  stays reduced-motion gated (STA-004/005). Invalid `variant` or non-positive
  `count` raise `TemplateSyntaxError`.
- **Tooltip** (`components/_tooltip.html` + the `bwTooltip` Alpine component,
  brickwork#56): a rich accessible tooltip, extend-consumed (fill
  `{% block tooltip_trigger %}`). No-JS floor: the trigger keeps a native `title`.
  Enhanced: the bubble (`role="tooltip"`, wired via `aria-describedby`) shows on
  hover AND focus, hides on mouseleave / blur / Escape, and never traps focus
  (WAI-ARIA APG Tooltip). `placement` (top default / bottom / start / end,
  logical for RTL); events `bw:tooltip:show` / `bw:tooltip:hide`. Supersedes the
  title-only baseline (spec STA-015).
- **Progress** (`components/_progress.html`, brickwork#56): a determinate or
  indeterminate progress bar. Determinate (`value` 0-100): `role="progressbar"`
  with `aria-valuenow` / `-valuemin="0"` / `-valuemax="100"` and an accessible
  name from `label`; the fill width rides the `--bw-progress-value` custom
  property via `calc(... * 1%)`, never a hand-built percentage string.
  Indeterminate (no `value`): an animated sweep gated behind
  `prefers-reduced-motion: no-preference`, with a static partial-fill fallback so
  reduced motion still reads as in-progress. Colour is never the only signal
  (spec STA-018 revisited; this is a progress DISPLAY, not the optimistic-update
  pattern STA-007 still declines).
- **Stat sparkline slot** (`_stat.html`, brickwork#60): an optional `sparkline`
  context var (a pre-rendered safe SVG / canvas string) rendered in a
  `bw-stat__sparkline` row below the value. The `trend` arg already shipped in
  0.5.0; this adds only the sparkline extension point. Charts stay
  consumer-mounted (a declared non-goal).
- **Three component tokens**: `--bw-component-tooltip-max-width`,
  `--bw-component-progress-track-height`,
  `--bw-component-stat-tile-sparkline-height` (canonical grammar with courtesy
  aliases, per the 0.11.0 tier re-grammar).

## [0.11.1] - 2026-08-02

Docs-only patch. Documents the `brickwork.css` app-facing-utility-layer change
that 0.10.0 shipped without a migration signal (brickwork#64).

### Added

- **`docs/INTEGRATION.md` section 1: what `brickwork.css` does and does not
  provide** (brickwork#64). Makes explicit that `brickwork.css` styles the
  `bw-*` substrate only, not a general Tailwind utility layer, and that a
  consumer's own page-content utilities must come from the consumer's Tailwind
  build (importing `dist/tailwind-theme.css` to inherit the brand) or their own
  bundle. Closes the discoverability gap behind the 0.10.0 console breakage.

### Fixed

- **The 0.10.0 CHANGELOG now carries the missing migration note** (brickwork#64):
  a retroactive BREAKING entry recording that `brickwork.css` stopped emitting an
  app-facing Tailwind utility layer in 0.10.0, with the two supported migration
  paths. No code change; the behaviour shipped in 0.10.0, the *signal* was
  missing.

## [0.11.0] - 2026-08-02

The token tier re-grammar (ADR-054 Phase b): the authored token surface is
tidied to its canonical grammar before 1.0 freezes the names, and the token
contract gains a machine-readable manifest and a brand-CSS emitter. This release
also lands the issue-wave docs (integration cookbook, adoption guide, branding
recipes, the htmx floor) and the list-pattern querystring-split fix. Names are
the semver-public surface, so every rename ships a courtesy alias; no resolved
default value changes.

### Added

- **Machine-readable load-bearing manifest** (brickwork#39):
  `dist/token-manifest.json`, generated from the DTCG source, enumerates the
  load-bearing brand set (7 core plus the conditional `surface-inverse` / `info`
  and the authored-per-theme `fg-on-accent`) with its constraints (contrast pair
  and minimum ratio, conditional / collapses-to flags), and the full overridable
  `--bw-*` vocabulary. The source now carries explicit
  `$extensions.bw.loadBearing` and constraint metadata rather than the set being
  implicit in the absence of a `derived` expression. `services/token_manifest.py`
  exposes `load_bearing()`, `overridable_names()`, `is_overridable()`.
- **`render_brand_css` emitter** (brickwork#40, `services/brand_css.py`,
  re-exported from `services/tokens`): `render_brand_css(light, dark=None, *,
  validate=True) -> str` takes brand override values keyed by token name (the
  full `--bw-color-accent` or short `color-accent` form), rejects unknown names
  against the manifest vocabulary, enforces the `fg-on-accent` 4.5:1 contrast
  constraint (correct OKLab -> linear-sRGB -> WCAG relative-luminance), warns
  when a status hue collapses onto the accent, and emits the documented
  `:root { }` / `[data-theme="dark"] { }` override blocks. This is the supported
  primitive behind BRANDING.md's per-tenant runtime-branding recipe; every
  consumer doing per-request theming stops hand-rolling CSS generation against
  the token names.
- **Integration cookbook** (`docs/INTEGRATION.md`): a seam-by-seam greenfield
  guide covering settings and static (with the static include-linter allowlist
  heads-up, brickwork#34), the nav config (including `kwarg_name` and the
  resolver-match hook, brickwork#19), the context processor (the theme-var
  mapping sharp edge, brickwork#22), a worked HTMX 422 form end to end
  (brickwork#24), the chrome/body boundary and asset-pipeline coexistence for
  JS-bearing pages (brickwork#33), the htmx floor, and bulk icon registration
  (brickwork#49). Closes brickwork#24, brickwork#33.
- **Adoption / strangle guide** (`docs/ADOPTION.md`): migrating an existing app
  onto brickwork cluster by cluster, with the multi-host and legacy-shell
  asset-coexistence wrinkles a real brownfield cutover hits (brickwork#37,
  brickwork#49). Closes brickwork#37.
- **BRANDING.md: the fg-on-accent contrast trap** (brickwork#35): a worked
  light+dark example where the dark accent is light-toned and therefore needs
  dark `fg-on-accent`, with the ratios `render_brand_css` reports and the "do
  not assume white" warning. Closes brickwork#35.
- **BRANDING.md: a dynamic-theming section** (brickwork#36) with two recipes,
  per-user density/theme/direction via a `theme_resolver`, and per-tenant
  runtime brand-token injection via the `render_brand_css` emitter. Closes
  brickwork#36.

### Changed

- **Primitives are no longer emitted to the browser** (ADR-054 section 2):
  `--bw-primitive-*` (the 43 raw colour ramps) are build-time input only now.
  They leaked onto `:root` through 0.10.0, inviting `var(--bw-primitive-*)` which
  the contract forbids (BR-BW-TOK-001). Style Dictionary resolves every semantic
  reference to a literal at build time, so no resolved value changes.
- **Scales promoted to the canonical semantic grammar** (the scale IS the role
  vocabulary): `--bw-size-space-*` -> `--bw-space-*`, `--bw-size-radius-*` ->
  `--bw-radius-*`. The Tailwind projection's `--spacing` / `--radius-*` follow.
- **Icon-size duplication resolved**: `--bw-icon-size-*` and `--bw-size-icon-*`
  (two names, identical values) collapse to one `--bw-component-icon-size-*`. The
  `{% bw_icon %}` size arg and the `.bw-icon` sizing reference the canonical name;
  the inline `--bw-icon-size` instance property is unchanged.
- **Component tier gains the canonical `--bw-component-*` grammar**: the
  un-infixed component tokens (`button-radius`, `icon-stroke-width`,
  `content-max-width`, `topbar-position`, `disabled-opacity`, `menu-min-width`,
  `select-indicator`, `checkbox-glyph`, `stat-tile-value-size`, `drawer-width`,
  `toast-max-width`, `htmx-indicator-opacity`) are re-infixed under
  `--bw-component-*`.
- **Nav / skeleton / breadcrumb per-component roles re-tiered** from the semantic
  colour family into `--bw-component-*` (`--bw-color-nav-item-active-*`,
  `--bw-color-nav-section-text`, `--bw-color-breadcrumb-*`,
  `--bw-color-skeleton-*` -> `--bw-component-*`). They stay theme-variant; only
  the name moves.
- **Courtesy aliases** ship for every renamed name (`--old: var(--new);` on
  `:root`), so a 0.10.0 consumer does not break on this minor. Aliases are a
  documented, time-boxed 0.x courtesy (ADR-054 section 7); prefer the canonical
  names.
- **README: the htmx floor is now stated explicitly** as `htmx >= 2.0`
  (brickwork#48); htmx 1.9 is out of contract. Documentation index links the new
  integration and adoption guides.

### Fixed

- **The list pattern now owns the sort/pagination querystring split**
  (brickwork#41). Previously `patterns/list.html` fed a single `querystring`
  context var to both the sortable table headers and the pagination links, so a
  consumer could satisfy only one: page links duplicated the sort param or sort
  links dropped the page. Now, when `request` is in context (the view / pattern
  path, via the shipped context processor), each link builds its own href from
  the live GET params with Django's built-in `{% querystring %}` tag: a sort
  click overrides `sort` and drops `page` (a re-sort resets to page one), a page
  click overrides `page` and preserves `sort` and filters. Consumers no longer
  hand-split `querystring` / `pagination_querystring`. Backwards compatible: the
  `querystring` context var remains the documented fallback for components
  rendered standalone with no request, and that path is byte-identical to 0.10.0.
  Django 6.0 floor already guarantees the tag. Touches `_data_table.html`,
  `_pagination.html`, and the `patterns/list.html` docstring.

## [0.10.0] - 2026-08-01

The structural close of the interaction-set programme: consumer Tailwind
utilities now inherit the brand, and the brand attribute is first-class
shell configuration rather than a template override.

### Added

- **Real Tailwind projection** (`dist/tailwind-theme.css`): an `@theme
  inline` block mapping the semantic `--bw-*` contract into Tailwind 4's
  utility namespaces, so consumer utilities (`bg-accent`, `rounded-md`,
  `shadow-3`, `text-heading-lg`, `font-display`, `p-4`) inherit
  brickwork's defaults and any active brand, in both themes, with no
  rebuild (every mapped value is a `var(--bw-*)` reference). Coverage:
  all 51 semantic colours, the 7 radius steps, the 6-level elevation
  ladder as `--shadow-*`, the 12 type roles with line heights, the 3
  font stacks, the preflight font defaults, and the dynamic `--spacing`
  base wired to `--bw-size-space-1` (the space scale was authored as
  Tailwind `--spacing` multiples from the start, so one declaration
  wires the whole numeric scale). Additive to Tailwind's own palette
  (`bg-blue-500` survives); component-tier, state-overlay, z-index,
  opacity, motion, and focus-geometry tokens are deliberately not
  projected. Consumption: import the fragment after the `tailwindcss`
  import. Reference: `docs/DESIGN.md` section 12.
- **Shell brand hook**: `resolve_theme_attributes` gains a `brand` axis.
  A `theme_resolver` that returns a `brand` key wins; otherwise the new
  `BRICKWORK_DEFAULT_BRAND` setting applies (default `""` emits nothing
  and renders byte-identically to 0.9.0). A non-empty brand renders
  `data-bw-brand="<slug>"` on `<html>`, where brand stylesheets scope
  and the derived `color-mix` tokens compute. Slugs are validated
  (`[A-Za-z][A-Za-z0-9_-]*`) at resolve time. This makes the site-level
  `shell/base.html` override that consuming sites carried for the brand
  attribute unnecessary.

### Fixed

- The previous `tailwind-theme.css` was a self-referential `--bw-*`
  identity map: `--bw-*` is not a Tailwind utility namespace, so the
  fragment generated no utilities and no inheritance. It had shipped
  that way since the fragment first appeared.

### Migration (documented retroactively in 0.11.1, brickwork#64)

- **BREAKING for consumers who relied on `brickwork.css` for app-facing
  Tailwind utilities.** Moving consumer-utility generation out to the
  `tailwind-theme.css` projection (above) means `brickwork.css` no longer
  ships a general Tailwind utility layer: it contains the `bw-*` component
  and shell classes only, not `.grid`, `.gap-4`, `.px-3`, `.sm:grid-cols-2`
  and the like. A consumer whose *page content* (inside `{% block content %}`)
  was authored in plain Tailwind utilities and was implicitly getting them
  from `brickwork.css` loses them on upgrade, so content collapses to
  unstyled document flow while the shell chrome still styles correctly.
  This was not called out at the time (0.10.0 framed the projection purely
  as Added), which broke a consumer's console. **The fix:** import
  `dist/tailwind-theme.css` after your `tailwindcss` import and build your
  own utilities from it (so your utilities also inherit the brand), OR
  ensure your own Tailwind / CSS bundle is linked on every brickwork-shell
  page. `brickwork.css` styles the substrate (`bw-*`); your content's
  utilities are yours to build. See `docs/INTEGRATION.md` section 1 (what
  `brickwork.css` does and does not provide).

## [0.9.0] - 2026-08-01

Interactions II: the second tranche of the interaction set (spec
04-interfaces section 4b as amended by umbrella PR #119). Server-driven
throughout: toasts have no client-side creation path, the combobox keeps
a native select as its form-state carrier, and dismiss controls only
exist under JS.

### Added

- **Toast** (`{% bw_toast %}` + `components/_toast_region.html`): the
  shell base now includes the toast region once (`#bw-toast-region`,
  `aria-live="polite"`, four logical positions, default top-end), so
  every shell page has a working toast target. The tag validates intent
  (`success|warning|danger|info`; `neutral` raises) and duration
  (`short|normal|long|persistent`), always renders a close control, and
  gives danger toasts `role="alert"`. Delivery is server-rendered only:
  an htmx response appends via
  `hx-swap-oob="afterbegin:#bw-toast-region"`;
  the no-JS floor is a `django.contrib.messages` alert banner. Alpine:
  `bwToastRegion` (at most 3 visible, older collapse behind "+N more")
  and `bwToast` (auto-dismiss from the duration tokens, timer pauses on
  hover and focus-within, never steals focus); events `bw:toast:show`
  and `bw:toast:dismiss`.
- **Combobox** (`{% bw_combobox %}`): a form-field widget rendered
  inside the field chrome (label, help, errors, `aria-describedby`).
  The base markup is a fully working native `<select>` that remains the
  submitted control at all times; `bwCombobox` progressively enhances
  it with the hand-rolled APG combobox pattern
  (`aria-activedescendant`, typeahead filtering, chips with Backspace
  removal in `multiple` mode, `allow_create` affordance emitting
  `bw:combobox:create`). Server filtering (`filter_mode="server"`, the
  default) debounces at `--bw-debounce-search` and swaps the option
  list into the stable `bw-listbox-<id>` target; 422 re-renders
  rehydrate selection from the DOM.
- **Dismissible alert and badge**: `{% bw_alert %}`/`{% bw_badge %}`
  gain `dismissible` (default off, output unchanged). The close control
  renders hidden and is revealed at JS init; `bwDismissible` removes
  the element and emits `bw:dismiss`. Persistence stays host-owned.
- **Tokens**: `--bw-duration-toast-{short,normal,long}` (4s/6s/10s),
  `--bw-debounce-search` (300ms), `--bw-toast-max-width` (24rem), and
  `--bw-htmx-indicator-opacity` (0.6; the STA-006 in-flight dim
  treatment, implemented for the first time with the combobox listbox
  as its first consumer).

### Fixed

- htmx settle classes (`htmx-added`/`htmx-settling`/`htmx-swapping`)
  knocked classless prose out of the content-typography floor
  (`:where(p:not([class]))` and family) for the settle window, causing
  a visible layout bounce on any swap targeting classless content.
  Latent since the floor shipped in 0.5.0; the `:where()` lists now
  match elements carrying only htmx lifecycle classes.
- A `[class^="bw-"][hidden]` display floor: author `display` rules on
  brickwork components no longer silently defeat the `hidden`
  attribute (the combobox floor/enhanced split and toast collapse rely
  on it).

## [0.8.0] - 2026-08-01

Interactions I: the first tranche of the interactive component library on
the token substrate (spec 04-interfaces section 4b). Progressive
enhancement throughout: the no-JS floor IS the base markup and Alpine
upgrades ARIA at init. Alpine.js, @alpinejs/focus and htmx are host-owned
peers this package never bundles; they appear only as devDependencies for
the test harness.

### Added

- **JS bootstrap**: `brickwork/dist/brickwork.js` ships as an ES module
  exporting `registerBrickworkComponents(Alpine)`, which registers the
  semver-public Alpine components `bwDropdown`, `bwTabs` and `bwModal` on
  a host-owned Alpine instance (never calls `Alpine.start()`). Components
  dispatch namespaced events: `bw:dropdown:open/close`, `bw:tabs:change`,
  `bw:modal:open/close`.
- **Disclosure** (`components/_disclosure.html`): grouped exclusive
  disclosure on native `details name=`, zero JavaScript.
- **Dropdown** (`{% bw_dropdown %}`, `brickwork_interactions` tag
  library): APG menu-button keyboard map (arrows, Home/End, typeahead,
  Escape), ARIA upgraded at init; the no-JS floor is a plain link list.
- **Tabs** (`{% bw_tabs %}`): roving tabindex with MANUAL activation,
  optional `url_sync` via `history.replaceState`, optional `lazy_load`
  panels (`hx-get` + `hx-trigger="intersect once"` with skeleton content
  reserving the swap space); the no-JS floor is real links with the
  server-selected panel rendered.
- **Modal** (`components/_modal.html`, extend-consumed with
  `modal_title`/`modal_body`/`modal_footer` blocks): focus trap via
  wrapped `x-trap.inert.noscroll`, focus returned to the invoker on every
  dismissal route, `[data-bw-autofocus]` initial-focus hook, scrim and
  Escape dismissal. Server-rendered fragments swapped into the new
  `#bw-modal-root` (shell base, `display: contents`, zero footprint)
  auto-open, and a server `HX-Trigger: bw:modal:close` header dismisses
  from the response side.
- **CSS**: dropdown, tabs, modal and disclosure component sections in the
  shipped stylesheet, drawn entirely from existing tokens (elevation,
  z-index ladder, motion, focus, state overlays).
- **Test harness**: Playwright interactions suite (keyboard maps, focus
  routes, htmx swap paths, layout-shift guard) alongside the axe runs.

### Fixed

- `bwModal` captures its component root once at init; previously a
  dismissal invoked from an inline Alpine expression on a descendant
  (the `close_url` anchor) mutated `data-bw-open` on that descendant
  instead of the root, leaving the modal visually stuck open.
- `bwTabs` strips the server-rendered `bw-tabs__tab--active` class at
  init alongside `aria-current`; previously the server-selected tab kept
  its active underline permanently because the stylesheet keys the
  active visual on either that class (the no-JS floor) or
  `data-bw-active` (the JS-owned marker), and only the marker was being
  toggled.

## [0.7.0] - 2026-08-01

The craft round. Owner bar: next to Radix, the components still read as
mechanically generated; token identity alone does not fix control-level
drawing. Additive; nothing renamed. One class-stamping change recorded
below.

### Added

- **Drawn form controls**: `select.bw-input` gets `appearance: none`, an
  embedded chevron (`--bw-select-indicator` component token) and
  hover/focus physics matching text inputs; new `.bw-checkbox` and
  `.bw-radio` custom-drawn controls (checkbox tick is an alpha mask,
  `--bw-checkbox-glyph`, painted with `fg-on-accent` so it stays AA in
  both themes; radio uses the border-width dot). The global focus ring
  covers both natively.
- **Control physics**: inputs gain an inner top hairline and a soft
  accent halo beneath the accessibility outline on focus; solid primary
  and danger buttons gain a border in their own hue and exact icon-only
  squares; secondary buttons gain surface + hairline + elevation.
- **Surface finesse**: light-theme top-light on cards, table wrap and
  menu panels (dark keeps its elevation inset highlights); `::selection`
  accent wash; thin tokenised scrollbars on the table wrap and sidebar
  nav; empty-state icons sit on a tinted accent disc.

### Changed

- `bw_field_widget` class stamping: `CheckboxInput` and
  `CheckboxSelectMultiple` now stamp `bw-checkbox`, `RadioSelect` stamps
  `bw-radio` (per-option, `option_inherits_attrs` verified); `Select`
  keeps `bw-input`. Checkbox widgets no longer carry `bw-input`; a
  consumer targeting `.bw-input` for checkboxes re-targets the new class.

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
