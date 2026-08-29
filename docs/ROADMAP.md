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
`main`. **Timeline, saved views and advanced filters did not ship and are
not merely pending**: they have no spec brick, and building the audit-trail
archetype showed the timeline gap is real (expanding one entry means a
disclosure below the table rather than inside the row it belongs to).
Scoping decision for all five unshipped slice 3 patterns is
icvoss/django-brickwork#362.

*Chart contract: shipped.* ADR-081 settled the ownership boundary and
ADR-082 the token vocabulary. `_chart_card.html` carries the frame, legend
chrome and the loading, error and empty states; `bw_chart_mount` carries the
mount and enforces its accessible name; `_chart_data_table.html` (CHT-012,
CHT-013) carries the data fallback as a SIBLING of the `role="img"` mount,
never a descendant, since `role="img"` makes every descendant presentational
and nesting the compensation inside the opaque thing defeats it. **Annotation
and an export seam did not ship**, and neither has a spec brick backing the
roadmap's mention of them.

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

**What Wave 1 did not deliver, carried forward rather than quietly dropped.**
Timeline, saved views and advanced filters (no spec brick; the audit trail
demonstrated the timeline gap is real, since expanding an entry means a
disclosure below the table rather than inside the row it belongs to), and the
chart contract's annotation and export seam (likewise no brick behind the
roadmap's mention). Scoping for all five unshipped slice 3 patterns is
icvoss/django-brickwork#362.

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

- Ship the documentation and editorial surfaces with contextual navigation,
  mobile navigation, table of contents, search-result, version and feedback
  regions, as overrideable regions on a shell rather than as new shells. Every
  shell derives from one `base.html`, so a family diverges by exposing its own
  regions, not by forking the document. The app shell's
  `subnav_region`/`breadcrumbs_region`/`page_header_region`/`footer_region`
  idiom is the pattern; icvoss/django-brickwork#434 extended it to the
  marketing shell, and icvoss/django-brickwork#257 decides the documentation
  surface's own region set.
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
  icvoss/django-brickwork#408 to #421.
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
