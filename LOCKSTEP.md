# Lockstep with icvoss/brickwork (Wave D)

Tracks [django-brickwork#718](https://github.com/icvoss/django-brickwork/issues/718)
and umbrella ADR-119.

## Rule

Once a unit is **migrated**, its editorial home is `icvoss/brickwork`. This
repository keeps a **release mirror** only. Do not edit mirrored files here
and treat that as source: change the monorepo, then sync.

## Migrated units (tokens and CSS 2026-09-28; templates and frontend JS 2026-09-29)

| Unit | Monorepo canon | Mirror here | Manifest key |
|---|---|---|---|
| Tokens (DTCG) | `packages/tokens/src/dtcg` | `src/brickwork/tokens/source/*.tokens.json` | `units.tokens` |
| CSS product layers | `packages/css/src/layers` | `frontend/src/{shell,nav,components,marketing}.css` | `units.css` |
| Templates | `django/templates/{brickwork,brickwork_marketing}` | `src/brickwork/templates/brickwork`, `src/brickwork/marketing/templates/brickwork_marketing` | `units.templates` |
| Frontend JS and Vite entry | `django/frontend/src/{js/,index.js,index.css}` | `frontend/src/{js/,index.js,index.css}` | `units.frontend-js` |

Integrity: `lockstep-manifest.json` (sha256 of each mirrored file, keyed by
relative path). CI asserts local files match the manifest, and that no mirrored
file exists outside it.

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

Then rebuild Django frontend assets (`npm run build`) and commit the mirror
plus any regenerated `static/brickwork/dist` artefacts as usual.

## Not yet migrated

Explicitly residual; these stay editorial here until a later packaging cutover:

- Python templatetags and inclusion tags (`src/brickwork/templatetags`)
- Python package layout and the PyPI publish pipeline
- Gallery HTML in monorepo vs Django examples (parallel artefacts OK until
  gallery unit is marked migrated)

## Fleet pins

Consumers keep pinning `django-brickwork` from PyPI by name. No silent dual
canon for migrated units: a change that only lands in one repo is a defect.
