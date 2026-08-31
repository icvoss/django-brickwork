# Brickwork roadmap

**Status:** active product plan, adopted 2026-08-25.

This is the route to the [interface-system contract](INTERFACE-SYSTEM.md). It
is ordered by dependency and user value, not by date. No delivery date is
committed in this plan.

## Decision and planning basis

**Importance:** the interface-system contract requires Brickwork to let a
Django team ship any interface without a second UI kit, component library or
design-inspiration source ([INTERFACE-SYSTEM.md](INTERFACE-SYSTEM.md), North
star and Completion standard).

**Priority:** Q2, deliberate. There is no external deadline.

**Handling class:** clear for this documentation plan. Each implementation
slice must independently assess its public-template, token, JavaScript and
accessibility-contract impact before work begins.

## Current baseline

Brickwork already ships foundations, five shells, core forms and interactions,
data-table patterns, 39 components, 42 copyable examples, and `bw-prose`.
This is a strong application and marketing baseline, but it does not yet cover
the full set of interface families in the contract. The source tree and example
catalogue are the evidence for this baseline, not this plan.

## Rules for every wave

Every shipped pattern, component or archetype must:

1. solve a named job in one of the interface families;
2. use the shared token system and work with brand, theme, density and
   direction axes;
3. provide keyboard, focus, no-JavaScript, loading, empty and error behaviour
   where applicable;
4. pass the existing accessibility, responsive and contract gates;
5. include a complete copyable example and catalogue documentation; and
6. add a public contract only when the pattern is stable enough to support
   under semantic versioning.

Component count is not a success metric. A component earns inclusion only when
it eliminates repeated design work across at least one archetype.

## Delivery waves

### Wave 0: system usability and catalogue

**Outcome:** a team can discover the right Brickwork starting point without
reading source files or assembling a page from an undifferentiated component
list.

- Define the public catalogue information architecture: foundations,
  primitives, patterns, archetypes and interface families.
- Give every shipped item a live preview, usage contract, states, accessibility
  notes, responsive behaviour and links to the archetypes that use it.
- Make the starting journey explicit: choose a family, choose an archetype,
  apply a brand, copy or extend, then connect Django behaviour.
- Establish the archetype-test harness so every new full-page example is
  rendered in both themes and at the supported responsive widths.

**Exit evidence:** a newcomer can locate and start the right shipped example
for the existing app, auth and marketing families in one catalogue journey.

### Wave 1: data-heavy applications

**Outcome:** Brickwork becomes a credible first choice for operational,
analytical and reporting interfaces.

- Expand data primitives: metric comparison, trends, status, timeline, audit
  trail, queue, saved views, advanced filters and dense responsive tables.
- Define a chart contract: data states, chart frame, axes, legend, tooltip,
  annotation, selection, drill-down, accessible summary and export behaviour.
- Ship the chart components or a first-party renderer integration required to
  satisfy that contract. A consumer must not need another UI kit to make charts
  feel native to the rest of the product.
- Add copyable analysis dashboard, report, comparison, queue and audit-trail
  archetypes.

**Exit evidence:** a team can ship a data-heavy dashboard and report with
consistent filters, tables, metrics and visualisation without introducing a
second design language.

**Delivery status, 2026-08-29.** Recorded against the four bullets above
rather than as a single done or not-done, because they did not land evenly.

*Data primitives: shipped, except three.* `_ranked_list.html` (#183),
`_sparkline.html`, `_trend_indicator.html`, `_gauge.html`, `_scorecard.html`
(VIZ-011/012, the shared dashboard grid CHT-026 makes serve stat tiles and
chart cards alike) and `_stat_comparison.html` (VIZ-019/020) are all on
`main`. **Timeline, saved views and advanced filters did not ship**, and
each is now scoped rather than pending: ADR-092 bricked timeline (VIZ-029)
and saved views (TBL-023), and dropped advanced filters (TBL-024, TBL-003's
refusal of a filter DSL standing). Building the audit-trail archetype showed
the timeline gap is real (expanding one entry means a disclosure below the
table rather than inside the row it belongs to). The per-pattern outcomes for
all seven carried-forward items are at the end of this section.

*Chart contract: shipped.* ADR-081 settled the ownership boundary and
ADR-082 the token vocabulary. `_chart_card.html` carries the frame, legend
chrome and the loading, error and empty states; `bw_chart_mount` carries the
mount and enforces its accessible name; `_chart_data_table.html` (CHT-012,
CHT-013) carries the data fallback as a SIBLING of the `role="img"` mount,
never a descendant, since `role="img"` makes every descendant presentational
and nesting the compensation inside the opaque thing defeats it. **Annotation
and an export seam did not ship**, and ADR-092 refuses both rather than
carrying them: annotation is CHT-027 (the engine draws in its own coordinate
space, which a package not owning the engine cannot own), and export is
answered by CHT-022's existing `chart_toolbar` slot, following TBL-019.

*Chart components: shipped engine-free, as ADR-081 requires.* Bundling an
engine remains forbidden; the mount is the consumer's seam.

*Archetypes: the Data-heavy operations family is open, at five of the seven
the contract requires.* All five planned for this wave ship on `main`:
`analysis-dashboard.html`, `report.html`, `comparison.html`, `queue.html` and
`audit-trail.html`. The cross-wave design-coherence gate ran on this wave's
first archetype and passed.

The two the contract still requires are the dense list and data-empty/error
states (`docs/INTERFACE-SYSTEM.md`, required-archetype table), tracked as
icvoss/django-brickwork#406 and icvoss/django-brickwork#407. This sentence
previously read "the family is complete", which was false against the
contract even though the exit criterion below it was met: the criterion is
deliberately narrower than the family, and stating the narrow claim as the
broad one is how a wave closes on a fiction. Say which of the two is being
claimed, every time.

**EXIT CRITERION MET, 2026-08-29.** The criterion is a statement about pages
shipping, not components existing, so it closes on the archetypes: a
data-heavy dashboard and report both ship from Brickwork alone. Verified
against the artefacts on `main` rather than against this list.

**What Wave 1 did not deliver, now scoped per pattern rather than carried
as a list.** ADR-092 (ratified 2026-08-30) gave each of the seven items one
of three outcomes, closing icvoss/django-brickwork#362. Two became bricks,
two archetype entries were duplication, and three are refused with reasons.
Nothing is left in the ambiguous state that let these survive a whole wave
unscoped.

- **Timeline: bricked, not scheduled** (VIZ-029). The one item with
  affirmative rather than absence evidence: the audit-trail archetype tried
  to expand an entry in place, could not, and shipped a single hardcoded
  disclosure naming one entry beneath a table of many. That establishes
  `_data_table.html` has no in-row expansion seam. It does **not** establish
  that a timeline component is the answer, and the brick says so: a row
  expansion seam was an equally live candidate. VIZ-029 picks a standalone
  `_timeline.html` for chronology with no tabular structure to anchor to,
  and leaves the audit trail's own gap to TBL-022, which already answers it.
- **Saved views: bricked, lower priority** (TBL-023). Presentation only:
  brickwork may own the control, its list and the active state; it must not
  own persistence, naming, sharing or permissions, all of which are
  application data and application authorisation.
- **Advanced filters: dropped** (TBL-024). TBL-003 had already refused a
  filter-definition DSL, which is what makes a filter "advanced". The
  umbrella term bundled that refusal together with a possible component,
  which is why it survived unscoped. A filter chip stack is a display of
  applied state rather than a definition language, and can be bricked on its
  own merits if asked for by name.
- **Audit trail and queue: archetype-only, and the slice 3 entries were
  duplication.** Both shipped in 3.14.0 as pure compositions introducing no
  primitive. The delivery plan listed both in slice 3 and slice 4 with no
  qualifier; what shipped settles it. This closes the double-count in the
  direction of "counted twice", not "silently dropped". The overlap is two
  items, not three: timeline is not named in slice 4 at all.
- **Chart annotation: dropped** (CHT-027). Under ADR-081 the package does not
  bundle an engine, and annotations are drawn by the engine in the engine's
  own coordinate space. A package that does not own the engine cannot own the
  annotation without either an adapter contract per engine or shipping
  geometry it cannot position.
- **Chart export: dropped**, with CHT-022's `chart_toolbar` slot affirmed as
  the complete answer: the package provides the place, the consumer authors
  the button. Consistent with TBL-019 (table export, NO) and ICO-023.

A correction this scoping surfaced, recorded here because it predates
ADR-092 and the ADR did not know it: TBL-022 and CBH-024 were two
mutually inconsistent unshipped answers to the same row-expansion question,
a SLOT and an ARG. TBL-022 stands as the answer; CBH-024 is closed as a
duplicate rather than kept as a second mechanism.

**And what the wave proved about the substrate itself.** The design bar was
tested against a pre-committed falsification condition on the analysis
dashboard, and half fired. Weighted hierarchy and a leading visualisation are
reachable; regional elevation, multi-column arrangement and a visible band
caption are not. An app-surface page can express a vertical stack of
full-width bands and nothing else. That is a finding about the package rather
than about any author, and it is icvoss/django-brickwork#371. Wave 2 should
read it before designing its shells, since documentation and editorial
surfaces need the same arrangement vocabulary.

### Wave 2: documentation and editorial

**Outcome:** Brickwork supports long-form reading and technical reference work
as well as product applications.

- **Ship the documentation surface. Done in 3.15.0, and ADR-091 settled it
  differently from how this bullet originally read.** The bullet said to ship
  "table of contents, search-result, version and feedback regions, as
  overrideable regions on a shell rather than as new shells". ADR-091 ruled
  against both halves, and the shipped shell follows the ADR: the
  documentation surface IS a new shell (`brickwork/shell/docs.html`), because
  a docs page must emit article-then-rail in source order while the marketing
  shell emits a single `content` block, and reconciling those inside one
  template is a fork behind a conditional; and the table-of-contents, version
  and feedback regions were each DECLINED with reasons, since the package
  cannot populate a TOC (a content-pipeline concern), cannot know a
  consumer's version scheme (application routing), and would ship an empty
  box for feedback (a form posting to a consumer endpoint). A consumer builds
  each into `docs_nav_region` or `docs_header_region`/`docs_footer_region`.
  Every shell still derives from one `base.html`; a family diverges by
  exposing its own regions, and the app shell's
  `subnav_region`/`breadcrumbs_region`/`page_header_region`/`footer_region`
  idiom remains the pattern that icvoss/django-brickwork#434 extended to the
  marketing shell and icvoss/django-brickwork#439 extended to this one.
  Six regions ship: `docs_nav_region`, the page-local `docs_header_region`
  and `docs_footer_region`, and the site-chrome `docs_site_header_region` and
  `docs_site_footer_region` added by ADR-091's 2026-08-30 amendment
  (icvoss/django-brickwork#448) after the first consumer adoption found the
  shell had no seam for the header and footer surrounding it. This text was
  left stale for one release after the ADR contradicted it, which is how a
  reader following the roadmap rather than the ADR would have built the wrong
  thing; precedence is Code > ADRs > this plan, and the ADR is authoritative
  wherever the two still disagree.
- Extend content primitives for code examples, API references, citations,
  figures, notices, tabs and cross-links while retaining the existing
  `bw-prose` floor.
- Add all fourteen archetypes the contract's two Wave 2 families require,
  not the eight this bullet previously named. Documentation (7): documentation
  home, article, API reference, search results, navigation, table of contents,
  versioned content. Editorial and publishing (7): article, author, category,
  archive, series, related content, reading-progress patterns. The earlier
  list omitted navigation, table of contents, versioned content, related
  content and reading progress, and merged the two families' separate article
  archetypes into one. All fourteen are filed as
  icvoss/django-brickwork#408 to #421. **Two of the fourteen ship:** the
  Documentation family's home (icvoss/django-brickwork#408) and article
  (icvoss/django-brickwork#409), as `examples/docs/home.html` and
  `examples/docs/article.html`. They are the first shipped templates to extend
  `brickwork/shell/docs.html`, and so the first bound by
  `tests/test_family_boundary.py`'s docs entry, which until then was a forward
  guard catching nothing. The family's other five (API reference, search
  results, navigation, table of contents, versioned content) remain open, and
  icvoss/django-brickwork#412 (navigation) still carries the
  icvoss/django-brickwork#430 constraint that `bw_nav` ships one orientation.
- Define content accessibility rules: heading order, landmark structure, code
  labelling, table responsiveness, reading measure and reading progress.

**Exit evidence:** a team can publish a complete documentation or editorial
site using Brickwork's shells and patterns, without importing a separate docs
theme.

### Wave 3: public web and conversion

**Outcome:** the marketing kit grows from landing-page sections into complete
public-site coverage.

- Add contact, comparison, campaign, customer story, careers, event and
  resource-listing patterns.
- Provide conversion flows: lead capture, booking or request, pricing
  comparison, confirmation and status.
- Make public navigation, search, footer, announcement and locale patterns
  reusable across small and large marketing sites.
- Add archetypes that prove a public site can share the same brand system as a
  product application without looking like its console.

**Exit evidence:** a team can launch a public product site and its conversion
journeys on the same Brickwork brand system as the application.

### Wave 4: transactional and guided journeys

**Outcome:** multi-step and stateful user journeys feel as complete as static
pages and dashboards.

- Expand authentication, onboarding, enrolment, request, checkout, review,
  receipt and status-tracking patterns.
- Standardise validation, save progress, interruption, retry, confirmation,
  cancellation and recovery states.
- Add accessible date, time, address, payment and file-entry interface
  patterns where a reusable design contract is proven.
- Provide complete examples that bind the patterns to ordinary Django forms
  and progressive enhancement.

**Exit evidence:** a team can deliver a high-stakes, multi-step Django flow
without inventing interaction, feedback or recovery conventions.

### Wave 5: breadth, extension and adoption experience

**Outcome:** Brickwork exceeds a component set by being the easiest system to
adopt, extend and evolve.

- Close primitive gaps found while delivering the preceding archetypes, such
  as avatars, calendars, command/search interfaces, notifications, richer
  input controls and media patterns.
- Provide a documented extension model for consumer-owned components that
  inherit Brickwork tokens, accessibility rules and interaction conventions.
- Improve project setup, introspection and developer-facing reference material
  so usage is as quick to discover as the component catalogue.
- Add migration guides for public, documentation, editorial, data-heavy and
  transactional surfaces, not only application chrome.

**Exit evidence:** a consuming team can stay within Brickwork for all reusable
design work while safely extending product-specific behaviour in its own app.

### Wave 6: complete-system proof

**Outcome:** the north star is demonstrated, not merely asserted.

- Maintain one complete reference implementation for every interface family.
- Verify every reference implementation across themes, densities, direction,
  keyboard paths, no-JavaScript floors and supported viewport widths.
- Audit the catalogue against the contract's archetype matrix and publish the
  remaining gaps openly.
- Run adoption reviews with real Django projects. Each review records where a
  second UI kit, component library or ad hoc design work was still required,
  then turns a repeated gap into a roadmap candidate.

**Exit evidence:** independent consuming teams can build each interface family
from Brickwork alone for reusable UI, and the reference implementations prove
the result.

## Dependency map

```text
Wave 0: Catalogue and archetype harness
  ├─ Wave 1: Data-heavy applications
  ├─ Wave 2: Documentation and editorial
  ├─ Wave 3: Public web and conversion
  └─ Wave 4: Transactional journeys
       └─ Wave 5: Breadth, extension and adoption
            └─ Wave 6: Complete-system proof
```

Waves 1 through 4 may progress in parallel after Wave 0. Wave 5 consolidates
the gaps those waves reveal. Wave 6 is a continuing validation discipline, not
a finish line after which Brickwork stops evolving.

## Release discipline

The roadmap does not authorise bundled, speculative rewrites. Each wave breaks
into small, independently releasable slices with a named archetype and a
contract sweep. Additive components and examples can ship in minor releases.
Changes to a stable template, token, navigation, interaction or JavaScript
contract follow the package's semantic-versioning policy and require migration
guidance.

## Success measures

| Measure | Evidence |
|---|---|
| Archetype coverage | A checked matrix of every required archetype in the interface-system contract, with a live reference example. |
| Second-kit escapes | Adoption reviews record whether a team needed another UI kit or component library, and why. The target is zero reusable-design escapes. |
| Composition quality | Reference implementations use shipped tokens and components without ad hoc visual CSS, except documented consumer-owned specialist renderers. |
| Quality baseline | Every new reference page passes the existing accessibility, keyboard, no-JavaScript and responsive gates. |
| Brand portability | Every new pattern works across the supported brand, theme, density and direction axes. |

## What this roadmap does not do

It does not turn Brickwork into a CMS, a source of business logic, or a fixed
house style. It does not require consumers to abandon a specialist renderer or
domain component. It requires those additions to fit Brickwork's design and
interaction contract, so the finished interface still reads as one product.
