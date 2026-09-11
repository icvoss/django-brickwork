# Visual-bar scorecard: 2026-09-11 Phase 1 provisional

**Status:** Phase 1 provisional. Render-blocked for viewport and theme
eyesight. Not a beauty certification. Not a completed pass under
[VISUAL-BAR.md](../VISUAL-BAR.md) section 6.
**Package under test:** django-brickwork `3.18.0`
(`src/brickwork/__init__.py` / `pyproject.toml` in this worktree).
**Reviewer:** agent session (package CSS, templates, examples, tokens only).
**Render mode:** no live render. Judgement is package-default CSS and
example templates only. Brand pack second pass: not run.

Bar: [VISUAL-BAR.md](../VISUAL-BAR.md). Clean-room only. Competitor names stay
out of public marketing copy. No kit markup pasted. No claim that brickwork
is beauty certified.

## Kit panel for this pass

Priority 1: Tailwind Plus, Preline UI.
Priority 2: shadcn/ui, daisyUI.
Priority 3 (coverage notes only): Flowbite, Tailgrids, Tailkit.
Behaviour only: Headless UI.

## Evidence available in this worktree

| Source | Present? | Use for this pass |
|---|---|---|
| Marketing / app screenshots (png/webp) | No | None found under the package or this worktree |
| Example pages S1 to S8 | Yes | Structure, composition, promised states |
| Package `tokens.css` / `brickwork.css` | Yes | Type roles, spacing, surfaces, elevation, density |
| Playwright / axe fixtures (`landing-*.html`, `list-*.html`, …) | Referenced by `a11y/axe.spec.mjs` and archetype harness | A11y and layout gates only; not opened as visual stills here |
| Intentional brand override render | No | Brandability judged from `BRANDING.md` + token derivation only |

## Comparison protocol (for the rendered follow-up)

Run before calling any axis a final pass or fail. Do not score thin fixtures.

1. Install package-only CSS (no showcase brand). Render each VISUAL-BAR
   surface example (or the matching archetype fixture) at desktop ~1440px and
   phone ~375px, light and dark.
2. Capture stills of the same eight jobs. Keep them private to the audit;
   do not ship kit assets.
3. Clean-room Idea refs only: open public kit docs / owned Tailwind Plus
   trees under umbrella `docs/_examples/`. Note which kit leads each failed
   axis in one line. Never paste markup, class strings, or structure.
4. Re-render the same surfaces with one intentional seven-token brand pack
   (`BRANDING.md`). Confirm composition still holds (brandability).
5. Fill the per-axis matrix below with pass / fail / n/a. Open package issues
   for substrate fails. Fixture defects first if copy, media, or example
   data is thin.

Until steps 1 to 4 run, treat every rating marked **provisional** as a
hypothesis from package evidence, and every axis marked **render-blocked** as
unscored for release-train done criteria.

## Surfaces

| ID | Surface | Package-only | Brand | Notes |
|---|---|---|---|---|
| S1 | App list | provisional (structure) | blocked | `examples/app/list.html`: filter, table, empty, pagination |
| S2 | App detail | provisional (structure) | blocked | definition table + related + danger zone |
| S3 | App form | provisional (structure) | blocked | consumer-owned `<form>` + `bw_form` + actions |
| S4 | App dashboard | provisional (structure) | blocked | equal KPI tiles; richer argument shape lives in ops analysis example |
| S5 | Marketing landing | provisional fail (craft) | blocked | text-only hero; no mobile toggle in example |
| S6 | Marketing pricing | provisional (mixed) | blocked | tiers + FAQ + CTA; centred hero, no media |
| S7 | Docs article | provisional (structure) | blocked | `bw-prose`, callouts, anchors; quiet by design |
| S8 | Dense ops | provisional (structure) | blocked | `examples/ops/analysis-dashboard.html` (and siblings) shipped |

## Axis fill vs render-blocked

| Axis | Fillable from CSS / templates? | This pass |
|---|---|---|
| Hierarchy | Partial (type roles, heading slots) | Provisional; eyesight blocked |
| Typography | Yes (families, roles, measures) | Provisional fail (defaults) |
| Spacing rhythm | Partial (tokens and section gaps) | Provisional fail on marketing; app provisional |
| Surface differentiation | Yes (surface tokens, card/feature chrome) | Provisional fail on marketing; app weak pass |
| Density | Partial (density scale; marketing gap token) | Provisional fail marketing air; app OK |
| States | Yes (promised empty / loading / error branches) | Provisional pass (contract); craft blocked |
| Navigation / mobile chrome | Partial (shell behaviour documented) | App provisional pass; marketing provisional fail |
| Forms | Partial (label / error / action structure) | Provisional pass (structure); craft blocked |
| Section cadence (marketing) | Partial (example composition + gap token) | Provisional fail |
| Brandability | Partial (override model + derivation) | Provisional pass (mechanism); visual hold blocked |

**Render-blocked everywhere (both themes × both viewports):** whether the
page reads as one focal point in a real viewport; accidental voids; dark
elevation craft; skeleton and empty-state beauty; brand pack hold after
override; any claim against a kit screenshot pair.

## Clean-room kit comparison notes (memory of public docs + package evidence only)

No kit markup. Idea refs only.

| Kit | What public docs typically lead on | Brickwork package evidence against that idea |
|---|---|---|
| Tailwind Plus | Hierarchy, section rhythm, header / footer / flyout craft | Marketing gap token is 4rem; landing is a stack of includes without media or alternating bands; marketing mobile flyout is opt-in, not in S5/S6 examples |
| Preline UI | HTML-first section and dashboard compositions | App shells and ops analysis page show argument ordering; simple S4 dashboard still equalises four KPI tiles; marketing surfaces stay flatter than Preline-style section theatre |
| shadcn/ui | Semantic token clarity, option grammar, a11y as default | Strong match on `--bw-*` roles, documented options, axe/archetype gates; not a visual taste win by itself |
| daisyUI | Theme density, "looks done" with little setup | Density axis and dark authored themes exist; default display font aliases to system sans, so "done" marketing type is weaker out of the box |
| Flowbite | Pattern inventory / block breadth | Coverage ambition, not scored as craft here |
| Tailgrids | Marketing and app block variety | Same: inventory gap, not scored as paint |
| Tailkit | Indie completeness checklist | Same |
| Headless UI | Overlay / menu / disclosure behaviour | App drawer, disclosures, menus exist as package chrome; behaviour craft not eyeballed this pass |

## Scorecard (provisional)

Fill legend: **fail** = package substrate likely loses the axis against the
named kit's published quality bar. **pass** = structure and tokens support
the axis; eyesight still required. **n/a** unused this pass.
**blocked** = cannot rate without render.

| Surface | Kit that led | Axes failed (provisional) | Borrow idea (clean-room) | Follow-up |
|---|---|---|---|---|
| S1 App list | Preline (product density); shadcn (token clarity) | None firm from CSS alone. Render-blocked: hierarchy eyesight, density at 375px, dark table chrome | Keep filter → table → empty → pagination as one job; tighten row rhythm only if stills show air | Render list fixtures light/dark; confirm empty and loading branches with realistic rows |
| S2 App detail | Preline | None firm. Render-blocked: surface stack of definition + related + danger | Prefer definition surface quieter than related table chrome so the record is the focus | Render detail; check danger zone weight vs kits' destructive bands |
| S3 App form | shadcn / Preline | None firm on structure (`bw_form`, field chrome, actions). Render-blocked: label/control alignment craft | Keep primary submit obvious beside ghost cancel; borrow kit form vertical rhythm only as token spacing | Render form and form-errors fixtures |
| S4 App dashboard | Preline / Tailwind Plus dashboards | Density / hierarchy risk: equal `bw-stat-grid` tiles flatten the argument (ops analysis example already teaches weighted scorecard) | Borrow "one headline metric, supporting cast" from kit dashboards into the default S4 example, clean-room on `--bw-*` | Prefer analysis-dashboard shape for S4 scoring, or revise S4 example spans |
| S5 Marketing landing | Tailwind Plus; Preline | Typography; spacing rhythm; surface differentiation; density (air); section cadence; navigation / mobile chrome | Distinct display pairing; larger marketing section cadence; alternating surface bands; feature surfaces with role, not bare stacks; ship mobile disclosure in the scorecard example | Fixture: add media + `_mobile_nav_toggle.html`; then re-render |
| S6 Marketing pricing | Tailwind Plus; Preline | Typography; section cadence; navigation / mobile chrome. Pricing tier chrome (border + elevation + highlight) is closer to pass | Highlighted tier already elevates; borrow kit pricing intro measure and section breathing room via tokens | Same mobile toggle gap as S5; render three-tier stills |
| S7 Docs article | Tailwind Plus docs / Preline content | None firm. Quiet prose is intentional. Render-blocked: heading scale vs body, code/callout banding | Keep content as the interface; borrow only measure and heading jump if stills show near-body titles | Render article light/dark at both widths |
| S8 Dense ops | Preline; Tailgrids (coverage) | None firm on structure (weighted scorecard, chart states, ranked lists). Render-blocked: ops density vs sparse accident | Keep argument order (headline → shape → breakdown); borrow kit dense-table ink contrast if stills wash out | Render analysis-dashboard and report; confirm loading/empty/error exclusivity visually |

### Provisional axis detail (package-default)

| Axis | Provisional rating | Evidence |
|---|---|---|
| Hierarchy | Mixed / eyesight blocked | Display role and clamped hero heading exist; page headers use `heading-xl`. Display family equals sans, so size carries almost all hierarchy. |
| Typography | Fail (defaults) | `--bw-font-family-display: var(--bw-font-family-sans)` with a system UI stack. Kits that win marketing type ship a deliberate display pairing; brickwork leaves that to brand overrides. |
| Spacing rhythm | Fail marketing; provisional app | `--bw-component-section-gap-marketing: 4rem`. App `--bw-density-section-gap` scales with density. Marketing stills needed to confirm voids. |
| Surface differentiation | Fail marketing; weak pass app | `--bw-color-surface-raised` aliases `--bw-color-surface`. Feature cards are gap-only flex columns (no border/elevation). Cards, stats, tables, pricing tiers use hairline border + elevation. |
| Density | Fail marketing air; pass mechanism | Density tokens cover compact / default / comfortable. Marketing air is a single 4rem gap, not kit-like section theatre. |
| States | Pass (contract) | Data table loading skeleton + empty state; chart card loading/error/empty; form field errors; empty_state variants. Craft of those states is render-blocked. |
| Navigation / mobile chrome | Fail marketing examples; pass app shell | App: sidebar → drawer at `--bw-breakpoint-md`. Marketing: collapse requires `_mobile_nav_toggle.html`; S5/S6 examples omit it and rely on flex-wrap. |
| Forms | Pass (structure) | Consumer-owned form, `bw_form`, `--bw-size-max-width-form`, primary/ghost actions. Pixel alignment blocked. |
| Section cadence (marketing) | Fail | Landing is hero → logos → features → stats → testimonial → CTA with uniform gap and no media on the default hero. Reads as stacked templates vs sequenced sections. |
| Brandability | Pass (mechanism) | Seven-ish load-bearing tokens, live `color-mix` derivation, `BRANDING.md`. Visual hold after a named brand pack is blocked. |

## Fixture hygiene before scoring

Do not score thin or broken fixtures as package visual fails. Correct example
data / showcase assets first, then re-render.

Known fixture gaps for this pass (site or example defects first):

- S5 landing example supplies no hero `media` and no mobile nav toggle.
- S6 pricing hero is copy-only (acceptable for pricing, but weak for media craft comparisons).
- S4 simple dashboard equalises KPIs; S8 analysis-dashboard is the stronger ops proof.
- No checked-in screenshots to compare against the frozen kit panel.

## Outcome

**Phase 1 provisional complete for structure-only axes. Rendered pass not
started.** Do not update VISUAL-BAR.md "Latest completed pass" until section 6
done criteria are met (independent rendered review, both themes and
viewports, priority-1 and priority-2 kits).

### Top 3 craft gaps for Phase 3

1. **Marketing section cadence and surface roles** (S5/S6): enlarge and
   vary marketing vertical rhythm; give feature / band surfaces distinct
   roles without card spam; sequence sections rather than stacking identical
   gaps. Kit Idea refs: Tailwind Plus, Preline.
2. **Default display typography**: stop relying on system sans for both body
   and display in package defaults, or document a deliberate base-theme
   display pairing that brands can still override. Kit Idea refs: Tailwind
   Plus, daisyUI theme density.
3. **Marketing mobile chrome in scorecard fixtures**: put the package-owned
   mobile disclosure into S5/S6 examples used for scoring, then raise header
   / disclosure craft toward Preline and Tailwind Plus HTML-first nav
   patterns (clean-room CSS only).

### Explicit non-claims

- This file does not certify beauty.
- Axe green, archetype harness green, and catalogue counts are out of scope
  for pass/fail here ([VISUAL-BAR.md](../VISUAL-BAR.md) section 4).
- Public copy must not name these kits as brickwork's identity
  ([POSITIONING.md](../POSITIONING.md)).
