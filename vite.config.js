// Vite config for the brickwork Alpine registration JS build.
//
// Settled decision (build-tool research 2026-07-30): STABLE, non-hashed output
// filenames (brickwork.js), so consumers reference them via plain {% static %}
// and need no django-vite. Versioning rides on the Python package's own semver,
// not a Vite manifest hash.
//
// Token CSS, the Tailwind theme bridge, tokens.js, and brickwork.css are
// vendored from published @bwui/tokens and @bwui/css (scripts/vendor-bwui.mjs).
// This build compiles only the Alpine registration JS. Warnings are promoted
// to errors via onwarn -> throw.
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: "src/brickwork/static/brickwork/dist",
    emptyOutDir: false, // vendored @bwui artefacts already live here; do not wipe them
    rollupOptions: {
      input: { brickwork: "frontend/src/js/index.js" },
      // brickwork.js is a consumed ESM (registerBrickworkComponents), not an
      // app entry: keep its exports instead of tree-shaking them away.
      preserveEntrySignatures: "strict",
      output: {
        entryFileNames: "brickwork.js",
        assetFileNames: (info) =>
          info.names?.some((n) => n.endsWith(".css")) ? "vite-unused.css" : "[name][extname]",
      },
      onwarn(warning) {
        throw new Error(`vite build warning promoted to error: ${warning.message}`);
      },
    },
  },
});
