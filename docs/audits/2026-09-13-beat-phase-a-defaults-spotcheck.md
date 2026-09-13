# Beat Phase A spot-check: raised defaults (3.22.0 candidate)

**Date:** 2026-09-13  
**Tip:** `feat/beat-phase-a` (A.2 marketing + A.3/A.4 app/overlay craft)  
**Against:** visual-compete PASS tip `e79f828` / Phase 5 sign-off
[`2026-09-12-visual-bar-signoff-pass.md`](2026-09-12-visual-bar-signoff-pass.md)  
**Programme:** umbrella `docs/plans/brickwork-beat-tailwind-plus.md` Phase A.5  
**Issue:** [icvoss/django-brickwork#541](https://github.com/icvoss/django-brickwork/issues/541)

## Scope

Spot-check only: confirm zero-kwargs craft raises on white canvas do not
regress the meet-bar axes that already PASS. This is **not** the Phase F win
scorecard and does **not** authorise beat/prefer claim language.

## Method

1. Read source CSS for touched selectors against the card 3.21.0 ambient +
   fg-mix edge recipe.
2. Confirm dark theme strips ambient back to plain elevation.
3. Run focused pytest ambient assertions for marketing and app/overlays.
4. Note residual tracker items that remain out of this spot-check.

## Surfaces checked

| Surface family | Selectors | Spot finding |
|---|---|---|
| Marketing cards/bands | feature-grid cards, testimonial, pricing tier, stat-band, CTA tint | Edge + ambient present on light; dark resets present |
| Marketing type | hero heading/lede, pricing table heading, CTA heading | Wrap/family craft only; no layout fork |
| App chrome | filter bar, data-table wrap, empty-state (md), stats | Edge + ambient; sm empty-state stays unframed |
| Overlays | modal panel, slide-over, dropdown panel, toast | Edge + ambient under existing elevation ladder |
| Shells | topbar, marketing header, auth/centred panels, sidebar edge | Light lift / stronger edge; nav active tokens left alone |

## Regression vs visual-compete PASS

| Axis (VISUAL-BAR) | Spot finding |
|---|---|
| Navigation | No substrate-owned regression noted; header elev additive |
| Typography | Additive wrap/family only |
| Forms | Untouched in this pass |
| Density | Existing density tokens retained |
| Spacing rhythm | Marketing section gaps unchanged |
| Elevation / edge | Strengthened deliberately (CHANGELOG consumer terms) |
| Colour / contrast | Token-only mixes; inverse/ghost AA from 3.21.0 retained |
| Overlay / focus | Elevation floors kept; axe fixtures not regenerated in this note |

**Verdict:** no meet-bar regression observed in this spot-check. Craft changes
are intentional default raises for beat Phase A, not meet-bar repairs.

## Residuals (not blockers for A.5)

- Named `marketing_footer_groups` component remains Phase B (#542); #500
  example/shell honesty already closed.
- Full still regeneration and independent win scorecard wait for Phase F
  (#545) after B/C/D.
- Homepage proof (A.6) follows package release pin on brickworkui.com.

## Honesty

Do not cite this note as a win against Tailwind Plus. Cite it only as Phase A
defaults spot-check clearance before release and homepage redo.
