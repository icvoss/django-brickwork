# Beat Phase F.1: brand × theme × density torture (capture)

**Date:** 2026-09-13  
**Package tip:** `e5f8cee` / 3.25.0 (branch `feat/beat-phase-f` at capture time)  
**Scope:** F.1 harness only. Surfaces **S1, S3, S5**. Brands
**northline**, **harbour**, **folio**. Densities **comfortable** and
**compact**. Both themes and both viewports (1440 / 375).  
**Not in scope:** F.2 win scorecard, F.3 proof site, F.4 POSITIONING/README
claim. Package-only leg optional and not run for this pass.

## Matrix

| Brand | Density | Fixtures dir | Stills dir | PNGs |
|---|---|---|---|---|
| northline | comfortable | `a11y/fixtures/visual-bar-northline/` | `docs/audits/_stills/2026-09-13-beat-f1-northline/` | 12 |
| northline | compact | `a11y/fixtures/visual-bar-northline-compact/` | `docs/audits/_stills/2026-09-13-beat-f1-northline-compact/` | 12 |
| harbour | comfortable | `a11y/fixtures/visual-bar-harbour/` | `docs/audits/_stills/2026-09-13-beat-f1-harbour/` | 12 |
| harbour | compact | `a11y/fixtures/visual-bar-harbour-compact/` | `docs/audits/_stills/2026-09-13-beat-f1-harbour-compact/` | 12 |
| folio | comfortable | `a11y/fixtures/visual-bar-folio/` | `docs/audits/_stills/2026-09-13-beat-f1-folio/` | 12 |
| folio | compact | `a11y/fixtures/visual-bar-folio-compact/` | `docs/audits/_stills/2026-09-13-beat-f1-folio-compact/` | 12 |

Per cell: S1 / S3 / S5 × light / dark × 1440 / 375 = 12 PNGs. Total **72**
stills. Fixtures and stills are gitignored; paths above are local only.

Env used for each cell:

```bash
VISUAL_BAR_BRAND=<brand> VISUAL_BAR_DENSITY=<density> VISUAL_BAR_SURFACES=s1,s3,s5 \
  DJANGO_SETTINGS_MODULE=tests.settings PYTHONPATH=src:.:tests \
  python a11y/generate_visual_bar_fixtures.py

VISUAL_BAR_BRAND=<brand> VISUAL_BAR_DENSITY=<density> VISUAL_BAR_SURFACES=s1,s3,s5 \
  VISUAL_BAR_STILLS_DATE=2026-09-13-beat-f1-<brand>[-compact] \
  node a11y/visual_bar_capture.mjs
```

## Brand packs added

| Pack | Intent | Accent | Type pairing (sans / display) |
|---|---|---|---|
| northline (existing) | B2B cool console | teal | Source Sans 3 / Source Serif 4 |
| harbour | hospitality / warm | amber | Nunito Sans / Fraunces |
| folio | editorial / cool paper | forest ink | Libre Franklin / Newsreader |

Each pack is override-delta only (`tokens.css` + short `DESIGN.md`), matching
the northline skeleton shape.

## Spot check (not F.2)

Capture complete; independent F.2 review pending.

Fixture HTML for sampled cells carries the expected `data-bw-brand` and
`data-density`. PNG file sizes are non-trivial (no blank captures). Sampled
stills (harbour S1 light 1440, folio S5 light 1440, northline compact S3 dark
375) show intact layout: sidebar/list, marketing sections, and form with
validation chrome respectively. Brand accents appear distinct across packs
(warm amber, forest green, teal). No obvious broken render (missing chrome,
collapsed shell, unstyled dump) was noted in that sample.

No substrate-owned fail is claimed or cleared here. F.2 owns the win
scorecard axes.

## Harness changes shipped with this pass

- `KNOWN_BRANDS`: northline, harbour, folio
- `VISUAL_BAR_DENSITY` (`comfortable` default, `compact`)
- `VISUAL_BAR_SURFACES` optional filter
- Fixture out dirs encode brand and non-default density
- Capture stills default path appends density when compact
- npm scripts: `visual-bar:fixtures|capture` for harbour and folio
- Docs: `docs/VISUAL-BAR.md`, `docs/audits/_stills/README.md`,
  `docs/examples/brand-pack/README.md`
