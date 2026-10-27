# Lockstep with icvoss/brickwork (Wave D)

Tracks [django-brickwork#718](https://github.com/icvoss/django-brickwork/issues/718)
and umbrella ADR-119.

## Rule

Once a unit is **migrated**, its editorial home is `icvoss/brickwork`. This
repository keeps a **release mirror** of source that still lives here, and
**vendors published npm dist** for the token and CSS substrate. Do not edit
mirrored files here and treat that as source: change the monorepo, then
sync and, for tokens/CSS, publish `@bwui/*` and bump the pins below.

## Shipped token and CSS artefacts (npm, 2026-10-27)

The wheel's `static/brickwork/dist/{tokens.css,tailwind-theme.css,tokens.js,brickwork.css}`
are produced from published packages during `npm run build`:

| Package | Pin | Dist files in the wheel |
|---|---|---|
| `@bwui/tokens` | `0.1.2` | `tokens.css`, `tailwind-theme.css`, `tokens.js` (copied) |
| `@bwui/css` | `0.1.2` | `brickwork.css` (minified with lightningcss, plus Django `index.css` extras and `vendor-overlays.css` that `@bwui/css` 0.1.2 omits) |

Integrity: `src/brickwork/static/brickwork/dist/bwui-pin.json` records the
installed versions. CI's frontend-build job runs `npm ci` then `npm run build`
and fails if those artefacts differ from the committed copies.

`token-manifest.json` stays the Django-shaped contract (`contrastPairs`,
`authoredPerTheme`) until `@bwui/tokens` emits that schema. Do not vendor
the thinner npm manifest over it.

Pip consumers never run npm. They still `{% static %}` the same filenames.

## Migrated source units (tokens and CSS 2026-09-28; templates and frontend JS 2026-09-29)

DTCG JSON and CSS layer files remain a **source mirror** so Python contract
tests can read them without Node. They are not compiled in this repo any more
for the shipped CSS/token files.

| Unit | Monorepo canon | Mirror here | Manifest key |
|---|---|---|---|
| Tokens (DTCG) | `packages/tokens/src/dtcg` | `src/brickwork/tokens/source/*.tokens.json` | `units.tokens` |
| CSS product layers | `packages/css/src/layers` | `frontend/src/{shell,nav,components,marketing}.css` | `units.css` |
| Templates | `django/templates/{brickwork,brickwork_marketing}` | `src/brickwork/templates/brickwork`, `src/brickwork/marketing/templates/brickwork_marketing` | `units.templates` |
| Frontend JS and Vite entry | `django/frontend/src/{js/,index.js,index.css}` | `frontend/src/{js/,index.js,index.css}` | `units.frontend-js` |

Integrity for the source mirrors: `lockstep-manifest.json` (sha256 of each
mirrored file). CI asserts local files match the manifest, and that no
mirrored file exists outside it.

Alpine registration JS (`brickwork.js`) is still compiled here with Vite
from the frontend-js mirror. That unit is not an npm package.

## Sync

From a local oss checkout that includes both repos:

```bash
# Preferred: push from monorepo
cd ~/Projects/oss/private/brickwork
node scripts/sync-to-django.mjs --django ~/Projects/oss/public/django-brickwork

# Or pull into Django
cd ~/Projects/oss/public/django-brickwork
node scripts/sync-from-monorepo.mjs
```

Then, when `@bwui/tokens` or `@bwui/css` has a new published version, bump
the pins in `package.json`, run `npm install` and `npm run build`, and
commit the lockfile plus regenerated `static/brickwork/dist` artefacts.

A source-only sync without an npm publish does not change the wheel's CSS.

## Not yet migrated

Explicitly residual; these stay editorial here until a later packaging cutover:

- Python templatetags and inclusion tags (`src/brickwork/templatetags`)
- Python package layout and the PyPI publish pipeline
- Gallery HTML in monorepo vs Django examples (parallel artefacts OK until
  gallery unit is marked migrated)
- `token-manifest.json` Django-shaped extras (`contrastPairs`), the
  `index.css` extras overlay, and `frontend/src/vendor-overlays.css` (dark
  `color-scheme` for native inputs, bare-link underline, wave-e sparkline
  demo cancelled), until [icvoss/brickwork#11](https://github.com/icvoss/brickwork/issues/11)
  lands a `@bwui/css` that includes those repairs

## Fleet pins

Consumers keep pinning `django-brickwork` from PyPI by name. No silent dual
canon for migrated units: a change that only lands in one repo is a defect.
Token and CSS values that reach the browser come from the `@bwui/*` version
recorded in `bwui-pin.json`, not from a second compile of the source mirror.
