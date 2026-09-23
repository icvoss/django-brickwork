# Brickwork interface-system contract

**Status:** target product contract, adopted 2026-08-25.

Brickwork owns the reusable design system for a Django project's interfaces.
It is the shared starting point for every interface family, rather than an
application shell with an adjacent marketing kit. A project may add
domain-specific behaviour and content, but it should not need to invent a
second visual language, layout grammar, or interaction convention to deliver
a complete interface.

## North star

A Django team can build any interface with Brickwork without needing a second
UI kit, component library or design-inspiration source to make that interface
feel finished. Brickwork earns that position through reusable foundations,
primitives, patterns, archetypes and an excellent catalogue experience, not by
forcing every consumer into one visual aesthetic.

## Product intent

The system enables a team to begin a new project quickly and deliver
consistent, distinctive, accessible interfaces across public sites, product
applications, operations tools, documentation, editorial publishing and
transactional journeys.

"Everything" describes coverage of interface design, not an attempt to own a
consumer's business model. Brickwork owns the reusable visual and interaction
decisions. Consumers own their data, permissions, domain rules, routes,
content sources and integrations.

## What Brickwork owns

### Foundations

- Brand, colour, type, spacing, elevation, motion, density, direction and
  responsive tokens.
- Accessibility, focus, keyboard, no-JavaScript and responsive behaviour as
  baseline component contracts.
- Icons, content rhythm and a coherent prose treatment.

### Primitives and patterns

- Inputs, feedback, selection, navigation, overlays, status, loading and
  empty states.
- Data display and control patterns: tables, filters, search, bulk actions,
  pagination, metrics, comparisons, chart frames, legends, tooltips and
  drill-down affordances.
- Content patterns: prose, code, media, callouts, tables, citations, table of
  contents and related content.
- Workflow patterns: onboarding, authentication, settings, multi-step tasks,
  confirmation, receipts, progress and status tracking.

### Layouts and page archetypes

Brickwork supplies the responsive shells, layout patterns and copyable page
archetypes that compose those primitives. The app shell
(`brickwork/shell/app.html`) supports `layout="sidebar"` (default),
`layout="topbar"`, and `layout="regions"` (full-width topbar above sibling
capability rail, contextual sidebar, and workspace; see INTEGRATION.md).
Coverage is required for these families:

| Family | Required archetypes |
|---|---|
| Marketing and public web | Landing, campaign, pricing, comparison, about, contact and conversion flows |
| Product applications | Dashboard, list, detail, create/edit, settings, search, activity and guided task flows |
| Data-heavy operations | Dense list, analysis dashboard, reporting, comparison, queue, audit trail and data-empty/error states |
| Documentation | Documentation home, article, API reference, search results, navigation, table of contents and versioned content |
| Editorial and publishing | Article, author, category, archive, series, related content and reading-progress patterns |
| Transactional journeys | Sign-in, enrolment, checkout or request flow, review, confirmation, receipt and status tracking |

An archetype is complete only when it has a deliberate hierarchy, responsive
behaviour, dark and light theme treatment, accessible states, loading, empty
and error states, and a copyable example that proves its composition.

## Design ownership boundary

Brickwork owns design wherever a decision can be made generically and reused
across projects. That includes the framing and interaction conventions for
data visualisation. A consumer may choose a charting engine or provide a
specialist renderer, but that renderer must fit Brickwork's tokens, layout,
states, legends, tooltips, filters and accessibility contract.

Brickwork does not own:

- domain semantics, calculations or business workflows unique to one product;
- a consumer's data, authorisation, content management or publishing process;
- external-service credentials or integration-specific transport;
- arbitrary tenant-authored CSS or JavaScript; or
- a single house aesthetic. Consumers express their identity through the
  token system.

These are ownership boundaries, not exclusions from interface design. When a
domain capability needs a reusable interface pattern, Brickwork should provide
the pattern while the consumer supplies the domain meaning.

## Delivery rule

The system expands through proven interface needs, not by adding disconnected
components. Each addition must identify its interface family and archetype,
reuse the shared token and interaction contracts, include a representative
example, and pass the existing accessibility and responsive gates. A component
is not complete because it renders in isolation: it is complete when it makes
one or more archetypes materially easier to compose without bespoke design
work.

## Completion standard

Brickwork has met this product contract only when a team can select a relevant
archetype, apply its brand, connect its Django data and behaviour, and ship a
finished interface without importing another UI kit. Where a specialist
renderer is necessary, it must fit Brickwork's tokens, layout, interaction and
accessibility contract rather than introducing a second design language.

## Current state and next work

At tip (ahead of the **3.33.0** PyPI pin) the required INTERFACE-SYSTEM
archetype matrix is complete: Documentation and Editorial **7/7**, Product
applications **15**, Data-heavy operations **7/7**, Marketing and public web
**7/7**, and Transactional journeys **7/7** (see [POSITIONING.md](POSITIONING.md)
section 1 and gated section 5 counts). Foundations, six shells, Theme L1 to
L4, core interaction and form primitives, data-table patterns, the marketing
kit and `bw-prose` are in the wheel. Archetype burn evidence lives in
`changelog.d/` fragments (400 to 407, 422 to 427, 614) until the next minor
assembles them.

At **3.34.0** the viable primitives and cheap options pack has landed:
`input_group`, `article_meta`, `comparison_table`, `toc`,
`date_picker_chrome` (chrome only), hero `media_placement="above"`,
`bw_ranked_list` optionals (#604 to #606), and `bw_theme_switch` `data=`
passthrough (#253).

Still explicitly deferred (do not silent-ship):

- `timeline` and `saved_views` (ADR-092 scoped)
- advanced filters, chart annotation, chart export (ADR-092 refusals)
- Wave 5 / P2 command surfaces: `command_palette` (#156), `notification_list`,
  `popover`, `newsletter_band`
- Beat residuals #570 / #571 (soft-stage / product-shot)
- #493 / #494 (DRF theme API / DB nav)

The versioned interaction surfaces (Alpine.data names, `bw:` events, and
package-owned HTMX target IDs) are declared in the generated
`interaction-manifest.json` sibling beside `token-manifest.json` and
`template-manifest.json` (icvoss/django-brickwork#229). Catalogue taxonomy
remains a separate descriptive manifest, not a BR-BW-VER-001 surface.

This document is the source of truth for the intended coverage. The current
component inventory and examples remain the source of truth for what ships in
any released version. [ROADMAP.md](ROADMAP.md) is the active delivery plan.
