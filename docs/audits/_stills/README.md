# Visual-bar stills (private)

Local PNG captures for the [VISUAL-BAR](../VISUAL-BAR.md) scorecard pass.
This directory is **gitignored** except for this README. Do not commit
screenshots, kit assets, or Forge stills here.

## Two-leg recipe

### Leg 1: package-only (package-default proof gallery)

S1 to S8 with compiled `brickwork.css` only. No showcase, kiln, or brand
pack. This **is** the package-default proof gallery named in VISUAL-BAR
section 5.

```bash
npm run visual-bar:fixtures
npm run visual-bar:capture
```

Output: `_stills/<date>/sN-<theme>-<1440|375>.png` plus `manifest.json`.

### Leg 2: brand pack (northline / harbour / folio skeletons)

Same surfaces after appending
`docs/examples/brand-pack/<brand>/tokens.css` and setting
`data-bw-brand="<brand>"` on the html root. Fictional skeletons only; not
kiln or a product identity. Brands: `northline`, `harbour`, `folio`.

```bash
npm run visual-bar:fixtures:northline
npm run visual-bar:capture:northline
# likewise :harbour and :folio
```

Output: `_stills/<date>-<brand>/` (or an explicit
`VISUAL_BAR_STILLS_DATE=...` folder name) plus `manifest.json` with
`"brand": "<brand>"`.

Density and surface filter (env on both fixtures and capture):

```bash
VISUAL_BAR_DENSITY=compact VISUAL_BAR_SURFACES=s1,s3,s5 \
  npm run visual-bar:fixtures:harbour
VISUAL_BAR_DENSITY=compact \
  VISUAL_BAR_STILLS_DATE=2026-09-13-beat-f1-harbour-compact \
  npm run visual-bar:capture:harbour
```

Optional date override for either leg:

```bash
VISUAL_BAR_STILLS_DATE=2026-09-11 npm run visual-bar:capture
VISUAL_BAR_STILLS_DATE=2026-09-12-northline npm run visual-bar:capture:northline
```

Fixtures for leg 2 land under `a11y/fixtures/visual-bar-<brand>/` (and
`...-compact` when density is compact; also gitignored). Both legs honour
`VISUAL_BAR_BRAND` (empty = package-only).

## Surfaces

S1 to S8 map to the examples named in VISUAL-BAR section 3. Fixtures are
rendered by `a11y/generate_visual_bar_fixtures.py` through the sanctioned
examples Engine (ADR-056).

## Scoring rules

- Score against Priority 1 and 2 panel kits (look and idea only).
- Forge stills under the umbrella `docs/_examples/forge-ui-kit-site/` clarify
  "finished"; they do not lead a scorecard row.
- Fixture defects first; do not file substrate fails for thin examples.
- Never paste kit markup, class strings, or structure into the package.
- Brandability is judged on leg 2 (composition holds under the seven-token
  override); do not score kiln preference as a package win or loss.
