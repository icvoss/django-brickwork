# Vite + Tailwind consumer recipe

Brickwork Theme Phase F (icvoss/django-brickwork#601). Copy these files into a
consuming Django project, adjust paths, then run the sync command.

## Layout

```text
frontend/
  css/main.css          # this recipe's entry (below)
  src/brickwork-theme.css   # vendored by sync_brickwork_projection
  brands/<slug>/tokens.css  # your Brickwork Theme profile (optional)
package.json
vite.config.js
```

## Sync the projection (once per brickwork bump)

```bash
python manage.py sync_brickwork_projection frontend/src/brickwork-theme.css
```

That replaces AgentPM-style hand copies from site-packages. See
[INTEGRATION.md](../../INTEGRATION.md#13-vite--tailwind-4-consumer-recipe-brickwork-theme-phase-f).

## `frontend/css/main.css`

```css
@import "tailwindcss";

/* Point dark: at brickwork's data-theme axis (not prefers-color-scheme). */
@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));

@source "../../templates";
@source "../js";

@import "../src/brickwork-theme.css";

/* Optional: your L1 to L4 brand delta (after projection). */
/* @import "../brands/northline/tokens.css"; */
```

## `package.json` (devDependencies excerpt)

```json
{
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "tailwindcss": "^4.0.0",
    "vite": "^6.0.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "sync:bw-theme": "python manage.py sync_brickwork_projection frontend/src/brickwork-theme.css"
  }
}
```

## `vite.config.js` (minimal)

```js
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  build: {
    outDir: "static/dist",
    emptyOutDir: true,
    rollupOptions: {
      input: "frontend/css/main.css",
      output: { assetFileNames: "app.css" },
    },
  },
});
```

## Template cascade

1. Shell links `{% static "brickwork/dist/brickwork.css" %}` (tokens + `.bw-*`).
2. `head_extra` links your built `app.css` (utilities + brand).
3. Do **not** import `brickwork.css` into Vite; do **not** dual-link it.

Brand profile depth: [THEME.md](../../THEME.md).
