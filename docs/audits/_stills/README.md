# Visual-bar stills (private)

Local PNG captures for the [VISUAL-BAR](../VISUAL-BAR.md) scorecard pass.
This directory is **gitignored** except for this README. Do not commit
screenshots, kit assets, or Forge stills here.

## Generate and capture

From the package root (package-only CSS, no showcase brand):

```bash
npm run visual-bar:fixtures
npm run visual-bar:capture
```

Optional date override for the output folder name:

```bash
VISUAL_BAR_STILLS_DATE=2026-09-11 npm run visual-bar:capture
```

Output layout: `_stills/<date>/sN-<theme>-<1440|375>.png` plus a
`manifest.json` for that run.

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
