# Visual-bar scorecard: 2026-09-12 Phase 3 craft re-score

**Status:** Phase 3 substrate craft re-score (package-only CSS). Not a beauty
certification. Not a completed programme pass under
[VISUAL-BAR.md](../VISUAL-BAR.md) section 6 (brand pack second leg deferred;
independent sign-off is Phase 5).
**Package under test:** django-brickwork `3.18.0` tip on
`feat/phase3-visual-craft` (issues #510, #511, #512).
**Prior pass:** [2026-09-11-visual-bar-scorecard.md](2026-09-11-visual-bar-scorecard.md)
plus fixture hygiene #509 (`_stills/2026-09-12/`).
**Reviewer:** agent session (rendered stills + package tokens/templates).
**Render mode:** package-default CSS only (`npm run visual-bar:fixtures` then
`VISUAL_BAR_STILLS_DATE=2026-09-12-phase3 npm run visual-bar:capture`).
**Private stills:** `docs/audits/_stills/2026-09-12-phase3/` (gitignored; 32
PNGs). See [\_stills/README.md](_stills/README.md).

Bar: [VISUAL-BAR.md](../VISUAL-BAR.md). Clean-room only. Competitor names stay
out of public marketing copy. No kit markup pasted. No claim that brickwork
is beauty certified. Do **not** restore POSITIONING beauty language from this
file alone.

## What changed since the Phase 1 rendered pass

| Issue | Change |
|---|---|
| #509 (already landed) | Credible fixtures: nav, filters, hero media, mobile toggle, chart empty |
| #510 | Marketing section gap 4rem → 6rem; hero block air; feature-grid cards get hairline/elevation/padding; stat-band uses marketing tint |
| #511 | `--bw-font-family-display` is a system serif pairing (no longer alias of sans) |
| #512 | `examples/app/dashboard.html` + startsite emit a weighted `_scorecard` (revenue span 2) |

## Kit panel (unchanged)

Priority 1: Tailwind Plus, Preline UI.
Priority 2: shadcn/ui, daisyUI.
Secondary Idea-ref only: Forge stills under umbrella
`docs/_examples/forge-ui-kit-site/`.

## Surfaces (fixtures now credible)

| ID | Surface | Notes for this pass |
|---|---|---|
| S1 to S3, S7, S8 | Unchanged structure | Fixture hygiene already landed; no Phase 3 substrate target |
| S4 | App dashboard | Weighted headline scorecard; populated nav |
| S5 / S6 | Marketing | Mobile toggle present; display serif; cadence/surface craft |

## Scorecard (package-default, both themes × both viewports)

Compared to Phase 1: substrate fails that #510 to #512 targeted are re-judged
from `2026-09-12-phase3` stills.

| Surface | Kit that led | Axes failed (this pass) | Borrow idea (clean-room) | Follow-up |
|---|---|---|---|---|
| S1 App list | Preline / shadcn | None firm | Keep filter → table job | None for Phase 3 |
| S2 App detail | Preline | None firm | Quiet definition vs related | None for Phase 3 |
| S3 App form | shadcn / Preline | None firm on structure | Keep primary submit obvious | Pixel craft optional later |
| S4 App dashboard | Preline / Tailwind Plus | **None firm** (was hierarchy) | Keep weighted scorecard as the Overview argument | Optional: activity sparklines later; not blocking |
| S5 Marketing landing | Tailwind Plus; Preline | **None firm** on prior Phase 3 axes | Keep display pairing + feature surface role + tinted acts | Thin logo cloud remains fixture-thin, not a substrate fail |
| S6 Marketing pricing | Tailwind Plus; Preline | **None firm** on prior Phase 3 axes | Keep highlighted tier; cadence from gap token | FAQ still thin; optional enrichment only |
| S7 Docs article | Tailwind Plus docs | None firm | Quiet prose | None |
| S8 Dense ops | Preline | None firm | Keep weighted ops argument | None for Phase 3 |

### Axis matrix

| Axis | Rating | Evidence from Phase 3 stills |
|---|---|---|
| Hierarchy | **Pass** | S4 revenue span-2 reads as the page argument; supporting tiles equal to each other only |
| Typography | **Pass (defaults)** | Display serif on marketing heroes and app page titles; body remains system sans. Brands still override via northline pack |
| Spacing rhythm | **Pass marketing; pass app** | Marketing gap token 6rem; hero extra block air; sections read as distinct acts |
| Surface differentiation | **Pass marketing; pass app** | Feature-grid cards: hairline + elevation-1 + padding. Stat band: marketing tint. Pricing tiers unchanged pass |
| Density | **Pass mechanism** | Marketing air improved; S4/S8 argue rather than equalise |
| States | Pass contract | Empty/loading branches remain component-owned; fixtures exercise them |
| Navigation / mobile chrome | **Pass examples** | S5/S6 at 375px show disclosure control (#509); app sidebar populated |
| Forms | Pass structure | Unchanged |
| Section cadence (marketing) | **Pass** | Hero → logos → features (surfaced) → tinted stats → testimonial → tinted CTA with breathing room |
| Brandability | Pass mechanism; visual hold deferred | Seven-token model unchanged; brand pack stills not run this pass |

## Outcome

**Phase 3 craft targets #510, #511 and #512 clear on this re-score** for
package-default CSS on S4 to S6. Programme definition of done is **not** met:
brand pack second leg, independent sign-off (Phase 5), and claim restore remain
open. Phase 2 leftovers #488 / #489 do not block this craft wave.

### Explicit non-claims

- This file does not certify beauty.
- Do not update VISUAL-BAR "Latest completed pass" until section 6 criteria
  are met.
- Do not restore README / POSITIONING beauty language from this pass alone.
- Forge stills do not lead any scorecard row.
