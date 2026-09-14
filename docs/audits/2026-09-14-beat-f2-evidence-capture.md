# Beat F.2 evidence refresh (capture note)

**Date:** 2026-09-14  
**Package tip:** `e865b00` / 3.25.0 (+ F.1/F.2 docs on `origin/main`)  
**Scope:** Close the F.2 Plus still gap named in
`2026-09-13-beat-win-scorecard.md` §6. Regenerated package-default S1 to S8.
**Not in scope:** Craft changes, F.3 proof site, F.4 claim language, Phase E.

## Package-default stills

| Item | Path |
|---|---|
| Fixtures | `a11y/fixtures/visual-bar/` (16 HTML, package-only, comfortable) |
| Stills | `docs/audits/_stills/2026-09-14-beat-f2-package/` (32 PNGs) |
| Manifest | same dir `manifest.json` (version 3.25.0) |

Recipe:

```bash
VISUAL_BAR_STILLS_DATE=2026-09-14-beat-f2-package npm run visual-bar:fixtures
VISUAL_BAR_STILLS_DATE=2026-09-14-beat-f2-package npm run visual-bar:capture
```

## Matched Plus stills (private Idea-ref)

Staged under umbrella gitignored
`docs/_examples/tailwind-plus-surface-stills/` (see README there).

| Surface | Plus stills now available | Honesty limit |
|---|---|---|
| S1 | Salient payroll / expenses (unchanged) | None for list job |
| S2 | Radiant `profile.png` | Detail / lead profile, not invoice line items |
| S3 | marketing-v4 contact centered (1440/375) | **Partial:** contact form chrome, not app create-form |
| S4 | Salient reporting (+ Radiant app adjacent) | Still the known Lose depth gap |
| S5 | marketing-v4 landing + Salient home (1440/375) | Radiant live `/` blocked (Sanity env); blanks deleted |
| S6 | marketing-v4 pricing three-tier (1440/375) | Radiant `/pricing` same Sanity block |
| S7 | Syntax docs (1440/375) | Live Next capture |
| S8 | Salient contacts / profit-loss (unchanged) | None for dense-list job |

Forge stills under `docs/_examples/forge-ui-kit-site/` remain secondary Idea-ref
only; they do not count as Plus lead/tie.

## Next

Craft for S2/S4 landed on `feat/beat-craft-lose` (see stills
`docs/audits/_stills/2026-09-14-beat-craft-lose/`). Independent F.2 re-score
against the new package stills plus Plus surface stills above. Soft-pass
forbidden. Do not update POSITIONING/README until a future F.2 PASS.

S5 / S7 remain Lose after the 2026-09-14 evidence re-score; S3 remains N/S
(partial contact form). Those are separate craft tracks after S2/S4 re-check.
