# Visual-bar Brandability: 2026-09-12 northline leg

**Status:** Phase 4.3 brand-pack stills pass. Scores the Brandability axis under
the fictional northline skeleton only. Not a beauty certification. Not kiln.
Not a completed programme pass under [VISUAL-BAR.md](../VISUAL-BAR.md)
section 6 (independent sign-off remains Phase 5).
**Package under test:** django-brickwork `3.18.0` on `feat/phase4-visual-proof`.
**Prior package-default craft:**
[2026-09-12-visual-bar-scorecard-phase3.md](2026-09-12-visual-bar-scorecard-phase3.md).
**Reviewer:** agent session (rendered stills + northline token delta).
**Render mode:** package `brickwork.css` inlined, then
`docs/examples/brand-pack/northline/tokens.css`; `data-bw-brand="northline"`
on the html root (`npm run visual-bar:fixtures:northline` then
`VISUAL_BAR_STILLS_DATE=2026-09-12-northline npm run visual-bar:capture:northline`).
**Private stills:** `docs/audits/_stills/2026-09-12-northline/` (gitignored; 32
PNGs). See [_stills/README.md](_stills/README.md).

Bar: [VISUAL-BAR.md](../VISUAL-BAR.md). Clean-room only. Competitor names stay
out of public marketing copy. No kit markup pasted. Do **not** restore
POSITIONING beauty language from this file alone.

## What this pass proves

The same S1 to S8 compositions from the package-default gallery still hold
after the seven-token northline override (surface, fg, border, accent,
danger, success, warning, plus fg-on-accent and type stacks per the
skeleton). Fixture copy still names the example product "Northwind"; that is
example content, not the brand-pack slug.

## Brandability axis

| Check | Rating | Evidence |
|---|---|---|
| Accent reads as brand, not substrate default | **Pass** | Primary buttons and active nav use northline teal/cyan in light and dark (S1 dark, S4 light, S5 both) |
| Surfaces and borders shift without breaking roles | **Pass** | Cooler light surface and darker charcoal dark theme; cards, tables and filters remain distinguishable |
| Display / sans pairing survives override | **Pass** | Page titles and marketing heroes keep display serif; UI chrome stays sans |
| Hierarchy and cadence hold | **Pass** | S4 weighted scorecard and S5 section sequence remain readable under the delta |
| Mobile chrome still usable | **Pass** | S5 dark 375px retains disclosure control and stacked CTAs |
| Kiln / showcase identity | **N/A** | Not applied; this leg is northline only |

**Brandability:** **held** under northline for S1 to S8 at both themes and both
viewports sampled from the 32-PNG run. No new substrate follow-up from this
leg alone.

## Explicit non-claims

- This file does not certify beauty or declare VISUAL-BAR section 6 met.
- Do not update VISUAL-BAR "Latest completed pass" until Phase 5.
- Do not treat northline as a recommended product look or as kiln.
- Full axis re-score against Priority 1 and 2 kits remains the package-default
  and Phase 5 job; this note is Brandability evidence only.
