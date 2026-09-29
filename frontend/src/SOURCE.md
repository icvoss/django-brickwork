# Frontend sources (release mirror)

**Migrated units:**

- CSS product layers: `shell.css`, `nav.css`, `components.css`, `marketing.css`
  (editorial home `icvoss/brickwork` at `packages/css/src/layers`)
- Vite entry and behaviours: `index.css`, `index.js`, `js/`
  (editorial home `icvoss/brickwork` at `django/frontend/src`)

Sync: `node scripts/sync-from-monorepo.mjs` (see `/LOCKSTEP.md`). Do not edit
these files here.

Not migrated: Python templatetags, the Python package and the PyPI pipeline.
