# Changelog

All notable changes to brickwork are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
semantic versioning. Template block names, HTMX target IDs, Alpine component
names, event names and token names are treated as public API (see the spec's
versioning contract).

## [Unreleased]

Two mobile accessibility defects the package's own gate should have caught
and did not, because the gate that catches this class of thing was only ever
pointed at marketing fixtures. `a11y/axe.spec.mjs`'s 320px/360px/375px/414px
sideways-scroll sweep (added for #125) ran over `sections-*.html` and
`hero-placement-*.html` only, so the app shell and the auth shell, the two
surfaces with the most chrome, were never swept; and axe's own `target-size`
rule reports `incomplete` rather than `violation` for most of these shapes
and never fires on a plain anchor, so a control could sit well under the
WCAG 2.5.8 floor with the gate green throughout. Both gaps are now closed,
not just the two defects: the sideways-scroll sweep runs over every fixture,
and an explicit `getBoundingClientRect()` measurement replaces trust in
axe's `target-size` rule.

### Fixed

- **Three shipped components, plus the package's own documented
  marketing-header composition, rendered interactive controls under the
  WCAG 2.5.8 24x24 target-size floor** (icvoss/django-brickwork#208).
  `.bw-data-table__sort` measured 74x16 at 375px (`inline-flex` with no
  `min-block-size`, so its height was whatever the label's line-height
  gave it); `.bw-data-table__row-link` and `.bw-checkbox` sat under the
  floor too. Widening the sweep found the same missing-minimum shape on
  `.bw-breadcrumbs__link`, `.bw-nav-header__link`,
  `.bw-bulk-actions-bar__select-all`, and
  `.bw-marketing-header__actions > a:not(.bw-btn)` and
  `.bw-marketing-header__nav :where(a)`, the header's own documented "a
  plain link alongside a bw_button" composition (measured 40x21).
  `.bw-data-table__sort`, `.bw-data-table__row-link`, the breadcrumb, nav
  and header links all take a `min-block-size` only: their content already
  centres, so this changes no visual weight. `.bw-checkbox` (and its
  `.bw-radio` sibling, sharing the same rule) had no wrapping label to
  extend the hit area through in either of its two shipped uses (a bare
  input in the data table's select column, and `bw_field_widget`'s
  unwrapped form-field render), so its box grew from 18px to the 24px
  floor instead, with the tick glyph and radio dot scaled to keep the same
  proportion; this is the one visible size change in the set, verified in
  both themes.

  `.bw-toggle` and the marketing footer's link-group default share the same
  missing-minimum shape and were deliberately left unfixed: the toggle is a
  fixed-shape switch that would need its visible proportions changed to
  meet the floor in the one context (`bw_field_widget`) where it has no
  wrapping label, and the footer group's layout is documented consumer
  territory, not brickwork's to size. Both are excluded from the new gate
  with the reasoning recorded alongside each exclusion, not silently
  passed.

- **The app shell's topbar and the auth shell's panel could scroll a 320px
  viewport sideways** (icvoss/django-brickwork#209). `.bw-topbar`'s
  fixed-content children (the drawer trigger, notifications, the account
  menu) had no shrink floor and no wrap, so a long account label (a real
  name or email, not the short "Account" default) pushed the row past a
  narrow viewport with nowhere to give; it now wraps, the same shape #125
  used for the marketing header. `.bw-auth`/`.bw-centred`'s single
  implicit grid track defaulted to `auto`, sized to fit its content's
  min-content width, so unbreakable panel content grew the track past the
  viewport and `.bw-auth__panel`'s own `inline-size: min(28rem, 100%)`
  inherited the oversized `100%` along with it; `grid-template-columns:
  minmax(0, 1fr)` caps the track at the available space, the grid
  counterpart of the `min-inline-size: 0` fix flex items need for the same
  "child refuses to shrink below its content" hazard.

- **`a11y/axe.spec.mjs`'s mobile sweep now covers every fixture, not just
  the marketing ones** (icvoss/django-brickwork#209). The sideways-scroll
  check iterates the fixture directory exactly as the axe loop above it
  already does, rather than naming `sections-*.html` and
  `hero-placement-*.html`; this is why the app and auth shells shipped
  #209 unnoticed; a component named nowhere near "marketing" now gets the
  same floor.

- **`a11y/axe.spec.mjs` now measures the WCAG 2.5.8 target-size floor
  directly instead of trusting axe's `target-size` rule**
  (icvoss/django-brickwork#208). axe reports `incomplete`, never
  `violation`, for most of these shapes and does not fire on a plain
  anchor at all, so the axe gate stayed fully green through every control
  in this release. The same "`incomplete`, not `violation`" gap the
  3.4.0 entry below records for the hero scrim's composited contrast: a
  real defect sitting behind an axe rule that cannot flag it needs a
  direct measurement, not a wider tag set.

## [3.5.1] - 2026-08-24

A documentation-only release. No template's rendered output changed, no option,
block, tag or token was added or removed, and no behaviour differs from 3.5.0.
There is nothing to integrate: upgrading from 3.5.0 is a version-number change.

Both entries fix the same class of defect, where the text a consumer would
actually follow disagreed with what the package shipped. One made a real
upgrade hazard invisible (a block name read from a newer checkout than your pin
is silently discarded), the other made a shipped example unfindable, which sent
a consumer to file for a component that will never exist.

### Changed

- **Named block headers now state which version introduced each block name**
  (icvoss/django-brickwork#193), for `_card.html`, `_modal.html`,
  `_slide_over.html`, `_alert.html`, `_tooltip.html` and `_empty_state.html`.
  Every concise name (`title`, `body`, `footer`, `header`, `actions`,
  `heading`, `action`, `trigger`, and `_empty_state`'s new `icon`) landed in
  3.4.0; every deprecated prefixed name (`modal_title`, `card_body`,
  `alert_body`, `tooltip_trigger`, and so on) predates it. No template's
  rendered output changed: this is a documentation-only fix.

  Upgrading is, and always was, safe: every concise name has a deprecated
  predecessor still shipped alongside it. The unsafe direction is reading a
  block name from a newer checkout (or newer docs) than the version you have
  pinned. A Django `{% block %}` override that names a block the parent
  template does not define is silently discarded: no error, no warning,
  `DEBUG=True` does not catch it, and `get_template()` only checks parse-time
  syntax, so a consumer pinned below 3.4.0 who fills a concise block name
  read from `main` gets a structurally valid, entirely empty region that
  still passes ordinary template-loading tests. Check the block's own
  version note in the template header against your pin before relying on a
  name.

### Fixed

- **`app/date-range-picker.html` is now listed in both example listings**
  (icvoss/django-brickwork#199). It shipped without ever being added to
  `src/brickwork/examples/README.md`'s file table or `README.md`'s
  enumerated list and page count (which said fifteen; it is sixteen), so a
  consumer had no way to find it short of reading the examples directory
  directly. One filed icvoss/django-brickwork#172 asking for the date-picker
  component `BR-BW-INPUT-004` deliberately never ships, having missed the
  example that answers it. `README.md`'s "Example pages" section now also
  says directly that there is no date-picker component and points at the
  example, and a new test asserts every non-section example on disk appears
  in the examples README's file table, so the next example cannot ship
  unlisted.

## [3.5.0] - 2026-08-22

A wave of composition and accessibility work, plus the ecosystem's first
copy-paste date range picker.

Two themes run through it. Components gained the arrangement and data seams
consumers were hand-building around: a topbar search form, a status-free
stepper mode, `data-*` hooks on table rows and stats, and badges on disabled
nav items. And measurement replaced assumption in the accessibility work: the
tenant focus ring is now derived and verified rather than aliased and hoped
for, and the obsolete hero scrim, whose contrast varied with where text
happened to sit, is gone along with the examples that carried it.

### Added

- `_stepper.html` now supports `mode="sequence"` for ordered, status-free
  stages, and horizontal steppers stack below 48rem rather than overflowing
  narrow viewports (icvoss/django-brickwork#114).

- `{% bw_search %}` adds a reusable, no-JavaScript topbar search form with an
  optional clearable scope chip (icvoss/django-brickwork#155).

- `_data_table` record rows now support a safe `data` mapping for consumer-owned
  `data-*` hooks (icvoss/django-brickwork#184).

- `_stat` now supports a safe `data` mapping for consumer-owned `data-*` hooks
  (icvoss/django-brickwork#186).

- **A complete, accessible date range picker**, as a copy-paste example rather
  than a shipped component (`examples/app/date-range-picker.html`).
  `BR-BW-INPUT-004` is Type Fixed and forbids brickwork shipping a JS
  date-picker widget; `the-wall.md` EXT-006 says a date picker is a SLOT the
  consuming team builds, with brickwork supplying the no-JS base. This is that
  build, written once properly, so the rule stays intact and unamended: no tag,
  no component template, no `frontend/src` JavaScript, no manifest entry.

  Native `<input type="date">` controls are the submitted form controls at all
  times, in single and range mode, so the no-JS floor is the OS date picker
  rather than a parsed text field. Above that: a two-month grid collapsing to
  one at narrow widths, the WAI-ARIA APG keyboard map, min/max bounds, disabled
  dates, a weekday mask, hover and keyboard range preview, swap on inverted
  selection, and presets. Month and day names and the week start come from
  Django's own l10n. Copy it, own it, adapt it.

### Changed

- Published wheels and sdists now include `CHANGELOG.md`, with an artefact-level
  publish check preventing it from being dropped (icvoss/django-brickwork#153).

### Fixed

- Tenant accent overrides now derive a verified focus-ring colour that clears
  3:1 against every surface it can land on, rather than aliasing the accent and
  hoping (icvoss/django-brickwork#145).

  **Breaking for some tenants.** `render_brand_css()` previously accepted a
  non-OKLCH accent (a hex value, say) and simply skipped the contrast check with
  a warning. It now raises `BrandValidationError`, because a ring whose contrast
  cannot be measured cannot be verified, and an unverifiable focus ring is the
  defect this fixes. If you override `--bw-color-accent`, that value and the
  contrast-relevant surfaces (`--bw-color-surface`, `--bw-color-surface-raised`,
  `--bw-color-surface-inverse`, `--bw-color-fg`) must be concrete `oklch()`
  literals. Converting a hex value is a one-line change.

  Overriding `--bw-color-focus-ring` directly is also rejected now: the ring is
  derived from your accent so it stays verified, and a direct override would
  silently reintroduce the unverified case.

- Disabled navigation items now render their existing `badge` value, so a
  consumer can show a visible status such as "Coming soon" without changing
  the item label (icvoss/django-brickwork#168).

- Hero examples now use the shipped `media_placement` contract instead of
  carrying duplicate markup and CSS. This removes the obsolete gradient scrim
  whose contrast varied with the position of text over media
  (icvoss/django-brickwork#170).

- An absent `data` mapping on `_data_table` rows or `_stat` no longer raises
  under Django's `string_if_invalid`. The guard accepted `None` and `""` but
  treated anything else non-mapping as an error, so a consumer running
  `string_if_invalid` had a missing `row.data` resolve to the marker *string*
  and an optional option raise `TemplateSyntaxError`, failing the whole page. A
  string can never be a valid mapping, so it now means "not supplied"; a
  genuinely wrong type still raises.

### Upgrading

Everything is additive except one case, called out in full above: if you
override `--bw-color-accent` through `render_brand_css()`, that value and the
contrast-relevant surfaces must now be concrete `oklch()` literals, and
`--bw-color-focus-ring` can no longer be overridden directly. Both exist so the
focus ring's contrast can actually be measured rather than assumed.

If you copied `examples/sections/hero/media-behind.html` or `split-media.html`,
your copy keeps working: you own that markup. The shipped stylesheet no longer
carries `.bw-hero-behind` or `.bw-hero-split`, so if you copied the markup but
relied on brickwork's CSS for it, move to `_hero.html`'s `media_placement`
option, which expresses the same arrangements as a supported contract.

## [3.4.0] - 2026-08-21

The composition wave. Brickwork's components gained the named blocks its own
specification had promised but never shipped, the block-name contract became
machine-checkable rather than merely documented, and the marketing kit lost
three arrangement gaps that had forced consumers to hand-build sections.

The through-line is ADR-077, ratified during this wave: sections are a contract
tier between components and pages, a tag's private render target never exposes
consumer-facing blocks, and a unit that exists only because a component lacks an
arrangement option is a gap to close, not a section to ship.

### Added

- **Named composition blocks on the SLOT components** (#163). `the-wall.md`
  resolved ten components as SLOT; four shipped include-only with no blocks.
  `_page_header` gains `breadcrumb`, `title`, `title_badge`, `description`,
  `actions`, `tabs`; `_empty_state` gains `icon`, `heading`, `body`, `action`;
  `_disclosure` gains `trigger_meta`; `_hero` gains `eyebrow`, `heading`, `lede`,
  `actions`, `media`. Every block wraps the pre-existing conditional as its
  default content, so a caller using only context variables renders
  byte-identically.

  Four wall bricks were deliberately NOT implemented as blocks. `_dropdown`,
  `_toast`, `_tabs` and `_combobox` are private render targets of their
  `{% bw_* %}` tags: a consumer-facing block would let a caller extend past the
  tag and skip its render-time enforcement (icon-only `aria_label`, variant and
  duration validation, duplicate-key validation, `filter_mode` validation). The
  wall specified the wrong mechanism and was corrected to ARG.

- **The template contract manifest and rename-detection gate** (#164), resolving
  README Open Question 2 and CHK-BLD-005. `BR-BW-TPL-001` made every named block
  semver-public, but nothing enforced it: `AC-BW-010` checked only that a block
  was *documented*, never that its name was *stable*, so a rename passed CI green
  and broke every consumer who had filled it. `template-manifest.json` plus
  `services/template_manifest.py` now mirror the token contract's architecture,
  generated from the compiled template tree, with a gate that fails on a removal
  or rename lacking a deprecation and names the block, its template, and the
  three legitimate ways forward.

- **`media_placement` on `_hero`** (#118, #169): `below` (default), `behind`,
  `beside`, per ADR-057 section 1a. `behind` stacks the media under the copy on
  an inverse surface with a scrim, so a headline can sit over an illustration.

- **`width` on `_cta`** (#173): `contained` (default) and `bleed`, filling in
  ADR-057 section 1a's ratified vocabulary alongside the existing `band`.

- **A `logo` block on `_testimonial`** (#173). The component accepted `logo` only
  as pre-rendered safe HTML a view had to `mark_safe`, which a plain template
  cannot build.

### Changed

- **Thirteen prefixed block names gained concise successors** (#165, #166), per
  ADR-077 section 4: the declaring template is the scope, so a prefix carries no
  information. `_card` gains `header`/`title`/`actions`/`body`/`footer`, `_modal`
  and `_slide_over` gain `title`/`body`/`footer`, `_alert` gains `body`,
  `_tooltip` gains `trigger`.

- **`_empty_state`'s `title` and `description` blocks are deprecated** in favour
  of `heading` and `body`, which match both the context variable and the CSS
  class they wrap. The old names never did.

- **Hero media radius now applies to `img` only**, not `svg` (#118). A photograph
  wants a frame; a diagram or logotype has none to round, and clipping its
  corners damaged artwork the caller drew deliberately.

### Deprecated

- All fourteen prefixed block names (`card_header`, `card_title`, `card_actions`,
  `card_body`, `card_footer`, `modal_title`, `modal_body`, `modal_footer`,
  `slide_over_title`, `slide_over_body`, `slide_over_footer`, `alert_body`,
  `tooltip_trigger`, `empty_state_action`) plus `_empty_state`'s `title` and
  `description`. **All keep rendering, and their behaviour is unchanged.** They
  are removed at 4.0.

### Fixed

- **A contrast defect in the hero `behind` scrim, found by measurement rather
  than by the accessibility gate** (#169). The first implementation used a
  gradient scrim, which makes the contrast ratio depend on where a line of text
  sits, so the guarantee changed with copy length: measured against pale media
  the lede reached only 4.25:1, under WCAG 1.4.3's 4.5:1 floor. A uniform scrim
  makes the floor unconditional; the same worst case now measures 8.32:1.

  axe reports `incomplete` rather than a violation for text over a background
  image, so the accessibility gate was green throughout. A Playwright test now
  measures composited pixels, and was validated by reinstating the gradient and
  confirming it fails.

### Upgrading

Nothing to do. Every change is additive, no existing caller's output changes,
and every deprecated block still renders with its original behaviour.

If you fill any deprecated block name, move to its successor before 4.0. The
rename-detection gate added in this release means a future rename cannot happen
silently.

## [3.3.0] - 2026-08-19

Two themes. The HTMX fragment contract becomes first-class: the data table's
rows are a semver-public partial with a stable swap target, and the 422
form-validation recipe now uses a Django 6.0 template partial instead of a
hand-authored fragment file, so a consumer re-renders shipped markup rather
than rebuilding it and letting the copy drift.

The rest is verification catching what a green suite had been hiding. The
class contract is now checked against every shipped component rather than the
example sections alone (an unstyled default button size had shipped live
behind a passing suite), brand values are validated on the emission path
rather than only their token names, and three a11y defects are fixed that
measurement found and inspection had not: a focus ring below the 3:1 WCAG
2.2 AA floor, disabled link-buttons that were still focusable, and wide
content that scrolled the page sideways.

### Added

- The class contract is now verified against every shipped component, form, nav and
  marketing template, not just the example sections. Previously a class emitted only by
  a component was never checked, which is how an unstyled default button size shipped
  live on every page behind a green suite. Adds 195 cases across 33 templates and their
  documented option vocabularies, with a non-triviality guard so a context that fails to
  populate cannot turn the check into a silent no-op (#137).

- **Django 6.1 added to the CI test matrix**, with the matching
  `Framework :: Django :: 6.1` classifier. The matrix ran 6.0 only while the
  package declares `Django>=6.0` with no upper bound, so 6.1 compatibility was
  asserted but never exercised. The 6.0 floor is unchanged (BR-BW-TPL-004)
  (#158).

- The data table's rows are now a semver-public template partial. A consumer driving
  sort, filter or pagination over HTMX can re-render just the rows from the shipped
  component with `render(request, "brickwork/components/_data_table.html#table_rows",
  ctx)`, or include them cross-file, instead of hand-rebuilding `<tbody>` markup and
  duplicating the selection contract, the `data-label` stacking behaviour and the
  row-link logic. The `<tbody>` carries a stable `id="<table_id>-tbody"` as the swap
  target. This completes the stable-id contract BR-BW-HTMX-005 already makes for rows.

### Changed

- The HTMX 422 form-validation recipe in `docs/INTEGRATION.md` now uses a Django 6.0
  template partial rather than a separate hand-authored fragment file. The form region
  and the page it lives in are one file addressed by fragment name, so the two cannot
  drift, and there is no `partials/` template to keep in sync. The package has mandated
  Django 6.0 since BR-BW-TPL-004, so the previous recipe was teaching a workaround its
  own floor had already made unnecessary.

### Fixed

- `render_brand_css` now validates brand **values**, not just token names. Values are
  interpolated into a stylesheet and CSS has no escaping mechanism for them, so a value
  containing `}` closed brickwork's block and took over the rest of the sheet. That is
  reachable from the documented multi-tenant recipe in `docs/BRANDING.md`, where tenant
  brand values travel from the database into a `<style>` block. Every value is now
  checked against the accepted colour syntaxes (`oklch()`, `oklab()`, `lab()`, `lch()`,
  hex, `rgb()`/`rgba()`, `hsl()`/`hsla()`, `var()` with an optional fallback, and bare
  keywords such as `transparent`) and anything else raises `BrandValidationError`.
  The check is deliberately **not** governed by `validate=False`: that flag skips the
  name and contrast checks only, because emitting an unvalidated value is an injection
  sink however much the caller trusts its data (#133).

- The focus ring no longer aliases `--bw-color-accent` directly. Painted against the
  surfaces it actually sits on, that alias measured 2.53:1 in light and 2.43:1 in dark
  (1.06:1 on a dark card), well below the 3:1 that WCAG 2.2 AA 1.4.11 requires of a
  focus indicator. It now derives from the accent through `color-mix()` in oklab with a
  contrast-safe lightness per theme, so a tenant's brand hue still reaches their focus
  rings while every pairing clears 3:1 (#134).

- A disabled link-button (`bw_button` with `href` and `disabled`) is no longer
  clickable or keyboard-reachable. It kept its `href` with only `aria-disabled="true"`,
  so it announced itself as disabled to assistive tech and then navigated anyway on
  click and on Enter. It now renders a non-navigable `<span>`, following the precedent
  already set for disabled pagination controls, with the visual appearance unchanged
  (#135).

- Wide content inside a card no longer drags the whole page sideways. A card is a grid
  item of the section stack, and a grid item defaults to `min-width: auto`, so a wide
  data table blew out its track and the scroll container inside it never received a
  width to scroll within: a 375px viewport rendered a 749px document. Cards and section
  stack children now carry `min-inline-size: 0`, and the table scroll wrap carries
  `contain: paint` (#136).

- Three components rendered with unstyled elements. A dismissible alert's body had no
  `flex` and its close control no `flex-shrink`, so on a flex row the text collapsed to
  its content width and the dismiss button crowded it instead of sitting at the trailing
  edge. A loading data table's skeleton had no padding while every real cell is inset by
  the row-density tokens, so the loading bars ran flush to the card border and jumped
  inward when data arrived (#137).
- `bw-data-table-wrap--stack` is no longer emitted. It duplicated `bw-data-table--stack`
  on the table under the identical condition, and every stack rule keys off the
  table-level class (#137).

- Front-door documentation now tells one consistent story. The README claimed "stable
  1.x" at version 3.2.0, `pyproject.toml` classified the package as Beta, and
  `docs/ADOPTION.md` described it as pre-1.0 and advised waiting for a 1.0 that had
  long passed. The README also claimed CI runs a "beautiful by default" gate; no such
  gate exists, and that phrase belongs to `docs/DESIGN.md` as a design principle. The
  accessibility claim is kept because it is real, but narrowed from "every component"
  to the 78 rendered fixtures the gate actually covers. Also corrects the marketing
  component count from eight to nine and removes a stale comment in `ci.yml` describing
  the accessibility and frontend jobs as stubbed when both are wired and blocking
  (#138).

## [3.2.1] - 2026-08-09

A fix-only patch. Everything here came out of auditing a consumer against
3.2.0: two shipped classes with no CSS rule behind them, a marketing header
that pushed a 320px viewport sideways, two docstrings still teaching the
pre-3.0.0 option names, and nav typing that made lazy translations
impossible to pass without breaking language switching. No option grammar,
template block, event or token moves.

### Fixed

- **Marketing header no longer overflows a 320px viewport** (icvoss/django-brickwork#125). The header's brand/nav/actions row now wraps instead of forcing the page 6px wider than a 320px viewport. Verified against the layout constraint in an automated 320px sideways-scroll check; a real-browser visual check at 320px is still recommended before relying on the wrapped layout looking right.

- **Two component docstrings documented the pre-3.0.0 option names** (icvoss/django-brickwork#129). `_account_menu.html` documented `align` where the code reads `placement`, and `_card.html` documented `padding`/`bw-card--padding-*` where the code reads `size`/`bw-card--size-*`. Both docstrings now match the shipped ADR-060 spelling.

- **Three shipped classes had no CSS rule: `bw-btn--md`, `bw-field__control`, `bw-card__body`** (icvoss/django-brickwork#130). `bw-btn--md` and `bw-field__control` now carry real rules; `bw-card__body` is documented as an intentionally positioning-only hook. Widened `test_examples.py`'s emitted-class-is-styled check to also cover the shipped component templates that named these classes, not only the copy-paste examples.

- **`NavItem.label` and `NavItem.badge` now accept lazy translations** (icvoss/django-brickwork#131). Both were typed `str`, which mypy rejects for a `gettext_lazy(...)` promise even though that is the correct way to supply user-facing nav text. Widened to `str | django.utils.functional.Promise` (the real runtime lazy-string base class), so no `django-stubs-ext` dependency is needed.

## [3.2.0] - 2026-08-07

The second and final wave of example sections. With `pricing`, `testimonial`,
`faq`, `stats` and `listing`, the catalogue is complete at **26 sections across
nine types**: every variant on the original list, none added to fill a grid and
none dropped. Additive throughout; nothing in 3.0.0's option grammar moves.

The `listing` variants existed to answer a question rather than to fill a row in
a table. A card grid is composed by four of the planned layouts and by this
section type, and the package ships one card with no grid, so the plan
deliberately deferred "should a grid be a component" until two variants had been
written. The answer is no: what the variants share is the ENTRY CONTRACT, not a
layout. A card grid is multiple columns of vertical stacks and a media list is a
single column of horizontal rows, and they have no layout declaration in common.

As in 3.1.0, the defects below were found by the gates rather than by the test
suite, which stayed green throughout. One of them is worth reading even if you
never touch this package: the a11y fixture had been supplying context to exactly
one section, so every other section that needs view data was stacking into the
fixture EMPTY and clearing both axe and the mobile gate while testing nothing at
all. A blank section violates no assertion.

### Added

- **Thirteen more example sections, completing the catalogue's nine types.**
  `pricing` (three-tier, single-plan, comparison-table), `testimonial`
  (single-quote, quote-grid, logo-and-quote), `faq` (single-column, two-column),
  `stats` (inline-band, card-row) and `listing` (card-grid, media-list,
  compact-table) join the four types that shipped in 3.1.0, for 26 sections in
  total. Every one clears the same gates as wave 1: axe WCAG 2.2 AA in both
  themes, the no-JS floor, and no horizontal scroll at 360, 375 or 414px.
- **A card grid is still not a component, now on evidence rather than
  assumption.** The plan deferred the decision until the first two `listing`
  variants existed. They now do, and what they share turned out to be the ENTRY
  CONTRACT (`title`, `summary`, `url`, `meta`), not a grid: the card grid is a
  multi-column layout of vertical stacks and the media list is a single column
  of horizontal rows, and the two share no layout declaration. Promoting a grid
  component would have abstracted the half they do not have in common, so the
  four declarations stay in each example where a consumer can change them.
- **Two sections deliberately take no context where a looping wrapper would
  have.** `pricing/single-plan` includes `_pricing_tier.html` once and `faq/*`
  include `_disclosure.html` once per question, both with flat strings, because
  a consumer copying a static pricing or FAQ band wants to edit words in the
  template rather than wire up a view. Each file documents the list-shaped route
  as the alternative for data-driven content.

### Fixed

- **The a11y fixture rendered every context-taking section empty, so the axe and
  mobile gates were measuring nothing.** `a11y/generate_fixtures.py` supplied
  context to exactly one section (`features/icon-grid`) via an inline
  `if "icon-grid" in name` test, so any other section needing view data stacked
  into the fixture as an empty wrapper and passed every gate while being wholly
  untested. The generator now imports `_SECTION_CONTEXTS` from
  `tests/test_examples.py`, the one place that list is already declared and kept
  exhaustive, and raises rather than writing a fixture if a section renders
  empty. Found by screenshotting the fixture rather than by any test: the
  suite was green throughout, because a blank section violates no assertion.
- **A wide table painted outside its own scroll container, so the PAGE scrolled
  sideways on a phone instead of the table.** `overflow-x: auto` sized and
  scrolled the container correctly (scrollWidth 687 against clientWidth 310 at
  360px) while the table still rendered to its full intrinsic width, putting the
  document 224px past the viewport. Both the pricing comparison table and the
  listing compact table now `contain: paint`, which clips the overflow to the
  container that already owns the scroll. The listing table was not yet tripping
  the mobile gate, so it was fixed as the latent case of the same defect rather
  than left until a longer title surfaced it.
- **Small print in five new sections used `--bw-color-fg-subtle` and failed AA
  contrast** at 2.36:1 against a 4.5:1 requirement. That token is for decorative
  ink whose meaning is carried by adjacent text; every one of these was
  meaningful prose, so they now use `--bw-color-fg-muted` like the rest of the
  kit's captions and notes.

## [3.1.0] - 2026-08-07

The first wave of the examples library: **sections**, the band-sized unit a
real page is actually assembled from, plus the long-form prose floor the blog
and docs layouts to come depend on. Additive throughout; nothing in 3.0.0's
option grammar moves.

The three defects fixed below were all found by a new mobile-first gate that
runs the sections at 360, 375 and 414px in both themes. Every one of them
passed axe and the full test suite beforehand, because nothing in this repo
previously measured viewport width. Two of them were in shipped 1.x code, not
in the new sections.

### Added

- **Example sections: the copy-paste unit is now a band, not a whole page.**
  Thirteen section variants ship under `examples/sections/<type>/<variant>.html`
  across four types (hero, features, cta, content). Previously every example was
  a complete page, so a consumer who wanted a pricing band had to copy a pricing
  page and delete most of it. Sections are package data off the template-loader
  path exactly as the page examples are (ADR-056), and each carries its copy
  inline, so all but one render from an empty context.
- **A long-form prose floor, `bw-prose`.** One class on a wrapper styles bare
  `h1` to `h6`, paragraphs, lists, blockquotes, inline code, code blocks,
  tables, figures and rules, at the 65ch reading measure, entirely from the
  existing text-role and colour tokens. It is the shape a rendered Markdown body
  or a CMS rich-text field actually arrives in: no classes on any child. Every
  descendant rule sits inside `:where()`, so a consumer's own class on any
  element wins without `!important`. Both themes are covered by the token layer
  rather than by theme-specific rules.

### Fixed

- **The hero no longer scrolls the page sideways on a phone.** Three separate
  causes, all found by the new mobile-first gate and all invisible to the
  existing suites. `.bw-hero__copy` sized to its content rather than its
  container, because `.bw-hero` sets `align-items` to something other than
  `stretch`; the display heading was a fixed 3.75rem, at which a single
  unbreakable word ("Documentation") measures 406px and cannot wrap, overflowing
  any viewport narrower than that; and neither had a wrap fallback. The heading
  is now fluid, capped at the display token so a brand retuning the type scale
  still governs the ceiling. A multi-word heading hid this by wrapping between
  words, which is why the shipped marketing pages never tripped it.
- **A code block no longer widens the page it sits in.** The `<pre>` scrolled
  its own overflow correctly while its `<code>` child painted straight through
  the scroll container, so the document itself scrolled horizontally.
- **`.bw-callout--note` had no CSS rule.** It is the default kind and the
  documented spelling, so it rendered unstyled: the
  icvoss/django-brickwork#120 defect class, caught this time by a test that
  asserts every class an example emits exists in the compiled stylesheet.

## [3.0.0] - 2026-08-06

One option name per concept, across every component.

An inventory of all 40 component templates and the 16 registered tags found the
package spelling one concept up to four ways: `variant`/`style`/`intent` for
treatment, six names for arrangement, three for scale, four for a link
destination. The consequence was that knowing one component taught you nothing
about the next, which is the opposite of what a substrate is for.

**Migration is mechanical and the table below is complete.** Rename the option
at each call site; no behaviour changed and no component was removed. There are
no aliases or deprecation warnings, so a missed spelling raises rather than
failing quietly, which is the intended way to find them.

Nothing outside the option names moved: every component, tag, shell, token,
Alpine name, HTMX id and the icon registry are unchanged from 2.0.1.

### Added

- **Every closed option vocabulary is now enforced** (ADR-060 rule 2).
  `{% bw_badge %}` had a documented variant set and no validation at all, so a
  typo emitted a `.bw-badge--<typo>` class that does not exist and failed
  silently; `{% bw_form %}`'s `density` reached `data-density` unvalidated while
  its two sibling arguments on the same tag validated. Both now raise on an
  unknown value.

- **`{% bw_dropdown %}` gains `placement`** (`start` default, `end`), closing
  icvoss/django-brickwork#120. `.bw-dropdown--end` had shipped in every
  consumer's stylesheet since 0.8.0 with no code path able to emit it.

- **A test asserts every documented option value resolves to a real CSS rule**
  (`tests/test_option_vocabularies.py`, ADR-060 rule 3). This is the systematic
  version of the #120 check, and it immediately found three more defects in the
  opposite direction, where a documented DEFAULT emitted a class the stylesheet
  never matched: `.bw-tabs--underline`, `.bw-slide-over--md` and
  `.bw-hero--start` now ship real rules. `.bw-hero--end` is added alongside, so
  the hero's alignment axis is complete (ADR-057 section 1a).

### Changed

- **BREAKING: one option name per concept, across every component** (ADR-060).
  The package spelled one concept up to four ways, so knowing one component
  taught you nothing about the next. Every rename below is mechanical, and there
  are no aliases or deprecation shims: brickwork has no external consumers.

  | Component | Was | Now |
  |---|---|---|
  | `bw_alert` | `variant="error"` | `variant="danger"` |
  | `bw_tabs` | `style=` | `variant=` |
  | `_disclosure.html` | `style=` | `variant=` |
  | `bw_toast` | `intent=`, `action_url=` | `variant=`, `action_href=` |
  | `bw_dropdown` items | `intent` | `variant` |
  | `_card.html` | `padding=` | `size=` |
  | `_account_menu.html` | `align=` | `placement=` |
  | `_toast_region.html` | `position=` | `placement=` |
  | `_modal.html`, `_slide_over.html` | `close_url` | `close_href` |
  | `_data_table.html` | `scroll_container` (alias) | `sticky_header` only |
  | `_cta.html` | `no_tint=True` | `band="plain"` (default `"tint"`) |
  | `_hero.html`, `_cta.html` | `primary_cta_url`, `secondary_cta_url` | `*_cta_href` |
  | `_pricing_tier.html` | `cta_url` | `cta_href` |

  `bw_alert`'s `"error"` was the sharpest case: every sibling component and the
  whole token layer use `danger`, and because both closed sets were validated,
  each spelling raised on the other component.

  CSS moved in lockstep: `.bw-alert--error` to `.bw-alert--danger`, and
  `.bw-card--padding-*` to `.bw-card--size-*`.

  Deliberately unchanged: `url` inside per-item dicts (nav, dropdown, tabs,
  crumbs, CTA dicts) is consumer data rather than an emitted attribute, and
  `trigger_variant` qualifies a named sub-element rather than the component.

## [2.0.1] - 2026-08-06

### Fixed

- **`{% bw_button %}` accepts `name` and `value`, so the documented
  bulk-actions wiring works** (icvoss/django-brickwork#119).
  `_bulk_actions_bar.html`'s own header comment documented
  `{% bw_button label="Archive" type="submit" name="bulk_action" value="archive" %}`
  as the way to fill its actions block, but the tag accepted neither keyword, so
  that exact call raised `TemplateSyntaxError`. A bulk-actions bar exists to tell
  the server which action was pressed, which is what `name`/`value` carry, so the
  component's whole purpose was unreachable through the supported API.

  Both apply to the `<button>` branch only. Passing them alongside `href` (which
  renders an `<a>`, where they are meaningless) is a render error rather than a
  silent drop, as is a `value` with no `name`, which the browser never sends.
  A button given neither renders byte-identically to before.

## [2.0.0] - 2026-08-06

brickwork's contract is components, shells, and tokens. Whole pages are
examples you own.

That is the whole of this release. The page and pattern template tiers, the
only part of the package a consumer imported and extended to get a whole
screen, are removed and re-cast as copy-paste examples shipped in the wheel
where the template loader deliberately cannot reach them. Everything else,
which is to say every component, tag, shell, token, CSS rule, Alpine name and
HTMX id, is untouched.

**If you compose brickwork components into your own pages, this release is a
no-op for you.** If you extended a shipped page or pattern, there is exactly
one migration and it is mechanical: copy the matching file out of
`brickwork/examples/` into your own templates tree. See the Removed section
for the mapping and the reasoning.

### Added

- **Copy-paste example pages, shipped in the wheel off the template loader
  path** (ADR-056). Fifteen complete, working pages built from the tokens,
  components, and shells, each carrying real content rather than placeholders:
  an annotated `base.html`, the app set (list, detail, dashboard, form, wizard,
  settings, console, confirm), the auth trio, and the marketing set (landing,
  pricing, about). They live in `brickwork/examples/` as package DATA, not
  under an app `templates/` directory, so Django's `APP_DIRS` loader
  structurally cannot resolve them: the only way to use one is to open it and
  copy it into your own tree, where you own it outright.

- **`brickwork.examples`, a small read accessor for that tree**
  (`list_examples()`, `read_example(name)`, `examples_root()`). It lets tooling
  read example source straight from the installed package, so the gallery and
  the wheel cannot drift. It reads no settings and touches no template engine,
  so it is safe to import before `django.setup()`.

- **`examples/base.html`, annotated line by line.** Every load-bearing line in
  the document skeleton is explained where it sits: the skip link and why it
  must be first, the modal and slide-over swap roots and why the empty divs
  cannot be deleted, the four `<html>` attributes carrying the theme, density,
  direction, and brand axes, and why `{% firstof %}` rather than `|default`.
  Copy it to own your skeleton, or keep extending `brickwork/shell/base.html`
  and receive improvements automatically; both remain supported.

### Changed

- **Changelog entries are now one fragment file per change**
  (icvoss/django-brickwork#113). A feature branch adds
  `changelog.d/<slug>.<type>.md` rather than editing `CHANGELOG.md`, and the
  release PR assembles the fragments with
  `python scripts/assemble_changelog.py <version>`. Parallel branches editing
  one shared `[Unreleased]` block conflicted on every merge in the 1.4.0 wave,
  and union-resolving those conflicts silently filed new capabilities under
  `Fixed`; two fragments are two files, so they merge without being compared.
  This is a contributor-workflow change only, with no effect on the installed
  package.

### Fixed

- **The dev extra now pins ruff to exactly the version CI installs**
  (icvoss/django-brickwork#110). The `[dev]` extra allowed any `ruff>=0.5.0`
  while `.github/workflows/ci.yml` installed `ruff==0.15.22`, so a local
  `ruff format` run under a newer ruff reformatted files the pinned version
  formats differently and produced phantom drift with no source change behind
  it. Both pins now move together, by construction.

- **The marketing shell now spaces its first content section**
  (icvoss/django-brickwork#111). The section rhythm was applied only BETWEEN
  children, so a page whose opening section was not a hero (a page header, a
  feature grid, a docs index) rendered flush against the header's hairline, and
  consumers were wrapping their first child in a padding div to compensate. The
  hero opts out, since it already owns its own vertical rhythm. This changes a
  visual default: a page that already compensates with its own top padding will
  gain doubled space until that workaround is removed, which is why it lands in
  a major.

- **`_alert.html` renders correctly when included directly.** The component
  derived its status icon in the `{% bw_alert %}` tag, so a plain
  `{% include "brickwork/components/_alert.html" with variant="warning"
  title="..." message="..." %}`, which is the composition shape the examples
  now document, passed an empty icon name and raised `IconNotFoundError`. The
  variant-to-icon mapping is resolved in the template as a fallback, so both
  call shapes work. The tag path still passes an explicit icon, which wins, so
  its output is byte-identical to 1.x.

### Removed

- **BREAKING: the shipped page and pattern template tiers are removed from the
  template loader path** (ADR-056). These templates no longer exist as
  loadable templates:

  - `brickwork/pages/{form_page,settings,console,confirm}.html`
  - `brickwork/pages/{auth_signin,auth_signup,auth_reset}.html`
  - `brickwork/patterns/{list,detail,dashboard,wizard,_table_card}.html`
  - `brickwork_marketing/pages/marketing/{landing,pricing,about}.html`

  Their block contracts (`BR-BW-PAGE-001` to `BR-BW-PAGE-005`, the pattern
  block sets, and the marketing page blocks within `BR-BW-MKT`) are retired
  rather than deprecated in place. All were `[v1-single-consumer]` and none
  was ever ratified by a second consumer, which is precisely the licence to
  unwind cleanly.

  **Migration, and it is the only one in this release:** if you wrote
  `{% extends "brickwork/pages/..." %}`, `{% extends "brickwork/patterns/..." %}`,
  or `{% extends "brickwork_marketing/pages/marketing/..." %}`, copy the
  equivalent file from `brickwork/examples/` in the installed package into your
  own `templates/` tree and point your `{% extends %}` at your own base or at a
  brickwork shell. The examples compose the same components, so the rendered
  page is the same; you now own the file. There is a one-to-one mapping for
  every removed template.

  **Nothing else moved.** The components, the template tags, the shells
  (`shell/base`, `shell/app`, `shell/auth`, `shell/centred`,
  `shell/marketing`), the CSS, the `--bw-*` token contract, the Alpine
  component names, the HTMX target ids, and the icon registry are all
  unchanged. A project that composed components into its own pages, which is
  most of them, needs no change at all.

  **Why a whole page could not stay an extendable contract:** a page is the
  most project-specific thing you own, and importing one hands a dependency
  the power to reshape your own landing page on a pin bump. It also forced a
  flat page-level context bag, which is why the old landing page needed
  `cta_heading`, `logo_cloud_heading`, and `features_heading` to avoid
  collisions between its own sections. Composing scoped
  `{% include ... with %}` calls has neither problem.

## [1.4.0] - 2026-08-05

The drop-in maturity wave: every silent wiring trap now fails loudly, the
marketing sections are drivable from plain templates, the NavItem tree gains
two more renderers, and the consumer-seam contracts are documented and
executable. Additive and backwards compatible throughout; no shipped contract
was renamed or removed.

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

- **`--bw-component-logo-height`: the marketing brand slot now sizes a
  dropped-in logo out of the box** (icvoss/django-brickwork#83). The marketing
  shell's `brand_logo` / `brand_wordmark` blocks were bare holes with no
  default sizing, so an unconstrained SVG rendered full-height and pushed the
  nav off-screen. The blocks are now wrapped in brickwork-owned elements
  (`.bw-marketing-header__brand-mark` / `.bw-marketing-header__brand-wordmark`,
  the app shell's #93 wrapper precedent); any `img`/`svg` inside caps at the
  new component token (default `2rem`) with width following the intrinsic
  ratio, the wrappers stay `flex: 0 0 auto` so nav and actions keep the
  remaining width, and an unfilled block leaves an `:empty` wrapper that
  collapses to nothing. The cap is applied at zero specificity (`:where`), so
  one consumer rule (or a token override) resizes it.

- **Flat CTA kwargs on the marketing section components**
  (icvoss/django-brickwork#98). Every dict-shaped CTA in the marketing kit now
  also accepts flat string kwargs, generalising `_stat.html`'s flat-string
  shape so a template-authored page (the ADR-056 compose-it-yourself model)
  can drive the sections through `{% include ... with %}`, which cannot build
  a dict inline: `_hero.html` and `_cta.html` take
  `primary_cta_label`/`primary_cta_url` and
  `secondary_cta_label`/`secondary_cta_url` alongside `primary_cta`/
  `secondary_cta`, and `_pricing_tier.html` takes `cta_label`/`cta_url`
  alongside `cta` (a tier dict passed to `_pricing_table.html` may carry the
  flat pair too). Additive and backwards compatible: a dict-shaped caller
  renders byte-identically, and when both shapes are supplied the dict wins
  outright. List-shaped context (`items`, `stats`, `tiers`, `logos`,
  `faq` items, `features`) has no flat spelling, a Django template cannot
  build a list inline, so each template header now documents the honest
  template-authored pattern instead (supply the list from context, or compose
  the per-item primitive, `_stat.html`/`_pricing_tier.html`/
  `_disclosure.html`, directly). The three shipped marketing pages forward
  the flat names per section (`cta_primary_label` et al for the CTA band),
  shadowed into each include so the hero's flat names never bleed into a
  later section's context.

- **Feature-grid items can link** (icvoss/django-brickwork#99). A
  `_feature_grid.html` item now takes an optional `url`: when present the
  whole card renders as an anchor (`bw-feature-card--link`, content ink
  preserved, no underline smear, heading moves to accent ink on hover/focus
  with the standard colour transition), so a marketing feature band's cards
  can navigate to their subjects. An optional per-item `aria_label` overrides
  the linked card's accessible name. Items without `url` render the plain
  non-interactive card byte-identically to before, mirroring `_stat.html`'s
  `href` contract.

- **The auth-aware marketing header recipe** (icvoss/django-brickwork#85).
  The supported anonymous-vs-logged-in `marketing_actions` pattern (branch on
  `request.user.is_authenticated`; log out as a POST form; bare `<a>` links
  styled by the shell, `{% bw_button %}` for CTA weight) is now documented as
  INTEGRATION.md section 8 and in `shell/marketing.html`'s own header
  comment. brickwork still never reads auth state itself: the state is
  host-injected, matching the app nav's visibility model.

- **`{% bw_nav_header %}`**, a horizontal marketing-header renderer over the
  same `NavItem` tree (icvoss/django-brickwork#102). Plain-anchor visual
  weight matching the marketing shell's own header links, plus the active
  state plain anchors lose (accent underline, full ink, `aria-current="page"`
  on the exact item, the active-ancestor treatment when a descendant is
  current). Works with the 1.3.0 `href` seam, so a CMS-menu-driven header nav
  keeps active state and visibility gating with no consumer CSS against
  renderer internals. Flat by design: section headers contribute their
  children to the row (labels not rendered) and link items' children are not
  rendered. `bw_nav` and `nav/_nav.html` are unchanged for existing callers.

- **`{% bw_nav_rail %}`**, a compact icon+label rail renderer over the same
  `NavItem` tree, tier one of the capability-rail + contextual-sidebar
  (two-tier) layout (icvoss/django-brickwork#82). Every rail entry is a real
  link (never a JS-only trigger); labels stay visible at caption size;
  children belong to the paired contextual `{% bw_nav %}` and the rail entry
  lights whenever it or any descendant is the current route. The
  `.bw-nav-two-tier` wrapper pairs the tiers inside the sidebar block,
  hairline-divided; no flyout ships (the no-JS floor stays free), and the
  mobile drawer keeps the full tree navigable through a plain `{% bw_nav %}`.
  All three renderers share one prepare pipeline, so URL resolution, the
  `BRICKWORK_NAV_FALLBACK` handling, and active state can never drift.

- **Icon family guidance and the chrome-name contract**
  (icvoss/django-brickwork#77). `docs/INTEGRATION.md` section 7 now states the
  registration timing and collision semantics (module-level registry, register
  in `AppConfig.ready()`, no race with the seed, re-register overrides, the
  directional flag survives a glyph swap), publishes the list of icon names
  brickwork's own shipped templates hard-reference (the minimum set an
  alternate-family consumer must keep registered), and adds
  Heroicons-vs-Lucide family guidance: mixing families, the whole-family swap,
  the chrome-name Heroicons map, the stroke-based-wrapper and stroke-width
  gotchas, and the licence notes. A drift-guard test asserts the documented
  chrome-name list matches the shipped templates so it cannot rot. The bulk
  `register_icons` recipe now shows inner paint markup, correcting an example
  that registered full `<svg>` wrappers the tag would have nested.

- **The coexisting-component-framework contract**
  (icvoss/django-brickwork#75). `docs/ADOPTION.md` now states explicitly that
  a second component framework (django-components as the named case) rendering
  inside `{% block content %}`, form bodies and card bodies is a supported end
  state, with the migration boundary (generic chrome to brickwork, domain
  components stay put, mounted in brickwork slots) and a do/do-not list
  covering dependency-injection ordering against the shell's assets, the
  one-Alpine rule, and CSP nonce pass-through. The consumer smoke harness
  gains a fixture simulating a second framework's component and dependency
  tags inside the shell, keeping the promise executable without depending on
  django-components.

- **The per-role accent recipe** (icvoss/django-brickwork#76).
  `docs/BRANDING.md` dynamic theming gains recipe 3: `BRICKWORK_THEME_RESOLVER`
  is now explicitly guaranteed to accept ANY request state as its key (session
  values, an active role, user, host, tenant), so a single-brand product whose
  accent flips by the user's active role mid-session is a stated supported
  path, not an off-label accident. The recipe covers the brand-slug wiring
  with per-role `[data-bw-brand]` accent blocks, per-accent fg-on-accent
  verification per theme, dark composition per role, and the emitter variant
  for data-driven accents. Tests pin the session-keyed resolver guarantee, the
  per-role emitter shape, and that the shipped stylesheet keeps the accent
  family derived live over `var(--bw-color-accent)` in every theme scope.

- **`docs/INTEGRATION.md` section 4 now documents the htmx SUCCESS contract**
  (icvoss/django-brickwork#84). The worked 422 form previously said "valid
  submissions redirect (302) as always" inside an `hx-target="this"` /
  `hx-swap="outerHTML"` example, which is exactly the full-page-into-partial
  trap: htmx follows the bare 302 and swaps the redirected full page (shell,
  nav, sidebar) into the form's slot. The section now works the success path
  end to end: `HX-Redirect` (a client-side full navigation) when success
  navigates elsewhere, a 200 region partial plus `HX-Trigger` / `HX-Push-Url`
  when success stays in place, and the plain `redirect()` kept for the
  non-htmx no-JS floor, with the trap and its symptom named.

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

- **`bw_badge`'s documented default variant `neutral` now has a real CSS
  rule** (icvoss/django-brickwork#100). The tag's no-args default is
  `variant="neutral"`, but the shipped CSS carried rules only for
  `info`/`success`/`warning`/`danger`, so the default badge's look was left
  implicit in the `.bw-badge` base class with no `.bw-badge--neutral` rule
  behind the contract. The rule now ships explicitly (sunken surface, muted
  fg, transparent hairline border: the token-derived neutral chip treatment,
  AA in both themes), so the contract and the CSS agree.

- **A testimonial no longer zeroes the marketing section gap above itself**
  (icvoss/django-brickwork#86). `.bw-testimonial`'s blanket `margin: 0` reset
  tied on specificity with the marketing shell's
  `.bw-marketing__content > * + *` section-gap rule and, sitting later in
  source order, won the tie, collapsing the rhythm above any composed
  testimonial (the stat-band/testimonial collision). The blanket reset is
  gone: the UA `<figure>` block margins are neutralised at zero specificity
  (`:where(.bw-testimonial)`) instead, so the shell's section rhythm always
  applies when a testimonial is composed as a marketing section.

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
