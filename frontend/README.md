# brickwork frontend build

This directory holds the build that compiles brickwork's shipped static assets.
It runs in **this repo only**, during package development and release, not in
any consumer's Django project.

## What it produces

Into `src/brickwork/static/brickwork/dist/` (committed and shipped in the wheel):

- `tokens.css` : the design-token custom properties (all four axes), compiled
  by Style Dictionary from the DTCG source in `src/brickwork/tokens/source/`.
- `theme.css` : the `@theme inline` Tailwind bridge mapping `--bw-*` tokens to
  short utility names.
- `django-brickwork.css` : the compiled component/shell CSS (Vite + `@tailwindcss/vite`).
- `django-brickwork.js` : the compiled Alpine component registrations (wrapping
  `@alpinejs/ui` + `@alpinejs/focus`), which register behaviour and never call
  `Alpine.start()`.

## Decisions already settled (do not relitigate in Phase 0)

Per the build-tool research (2026-07-30, recorded in the umbrella brief):

- **Stable, non-hashed filenames.** Vite output filenames are fixed
  (`django-brickwork.css`, not `django-brickwork-[hash].css`). Versioning rides on the Python
  package's own semver. Consumers reference assets via plain
  `{% static "brickwork/dist/django-brickwork.css" %}`; their own static storage
  (WhiteNoise / ManifestStaticFilesStorage) handles cache-busting.
- **No `django-vite`.** With stable filenames there is no manifest to resolve,
  so `{% vite_asset %}` has nothing to do that `{% static %}` does not. brickwork
  imposes zero build-tool dependency on consumers.
- **No `django-tailwind` / `django-tailwind-cli`.** Those manage a Tailwind
  build inside a live Django project; brickwork compiles here, in its own repo,
  with the same Vite + `@tailwindcss/vite` toolchain the consumer apps use.
- **Alpine + htmx are host-owned peer dependencies.** brickwork bundles neither;
  it registers behaviour onto the host's Alpine instance and never starts it.

## Open (resolved in Phase 0, against consentics + agentpm)

- The exact `--bw-*` token vocabulary and the DTCG source structure (spec
  open question 1).
- The Style Dictionary config and custom output formatters.
- The Vite entry/config specifics and the exact peer-dependency version pins
  (spec open question 6, against consentics' real Vite setup).
- The brand-token authoring mechanism a consumer uses (spec open question 5).

Scripts in `package.json` are stubs until then.
