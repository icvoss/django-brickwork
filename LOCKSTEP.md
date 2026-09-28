# Lockstep with icvoss/brickwork (Wave D)

Tracks [django-brickwork#718](https://github.com/icvoss/django-brickwork/issues/718)
and umbrella ADR-119.

## Rule

Once a unit is **migrated**, its editorial home is `icvoss/brickwork`. This
repository keeps a **release mirror** only. Do not edit mirrored files here
and treat that as source: change the monorepo, then sync.

## Migrated units (2026-09-28)

| Unit | Monorepo canon | Mirror here | Manifest key |
|---|---|---|---|
| Tokens (DTCG) | `packages/tokens/src/dtcg` | `src/brickwork/tokens/source/*.tokens.json` | `units.tokens` |
| CSS product layers | `packages/css/src/layers` | `frontend/src/{shell,nav,components,marketing}.css` | `units.css` |

Integrity: `lockstep-manifest.json` (sha256 of each mirrored file). CI asserts
local files match the manifest.

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

- Django templates / inclusion tags / Alpine + HTMX behaviours
- `frontend/src/index.css` Vite entry and JS bundle
- Python package layout / PyPI publish pipeline
- Gallery HTML in monorepo vs Django examples (parallel artefacts OK until
  gallery unit is marked migrated)

## Fleet pins

Consumers keep pinning `django-brickwork` from PyPI by name. No silent dual
canon for migrated units: a change that only lands in one repo is a defect.
