// Vite config for the brickwork component CSS/JS build.
// SCAFFOLD STUB: the real config lands in Phase 0 (spec open question 6,
// against consentics' actual Vite setup).
// Key settled decision (build-tool research 2026-07-30): STABLE, non-hashed
// output filenames (django-brickwork.css / django-brickwork.js), so consumers reference them via
// plain {% static %} and need no django-vite. Versioning rides on the Python
// package's semver.
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  build: {
    outDir: "src/brickwork/static/brickwork/dist",
    emptyOutDir: false,
    rollupOptions: {
      // input: { "django-brickwork": "frontend/src/js/index.js" },
      output: {
        entryFileNames: "django-brickwork.js",
        assetFileNames: (info) =>
          info.names?.some((n) => n.endsWith(".css")) ? "django-brickwork.css" : "[name][extname]",
      },
    },
  },
});
