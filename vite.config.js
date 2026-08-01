// Vite config for the brickwork component CSS/JS build.
//
// Settled decision (build-tool research 2026-07-30): STABLE, non-hashed output
// filenames (brickwork.js / brickwork.css), so consumers reference them via
// plain {% static %} and need no django-vite. Versioning rides on the Python
// package's own semver, not a Vite manifest hash.
//
// Style Dictionary compiles the design tokens separately (build-tokens.mjs);
// this build compiles brickwork's component CSS + the Alpine registration JS.
// Warnings are promoted to errors (a silent Vite warning has masked broken
// output before) via onwarn -> throw.
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  build: {
    outDir: "src/brickwork/static/brickwork/dist",
    emptyOutDir: false, // the token artefacts already live here; do not wipe them
    rollupOptions: {
      input: { brickwork: "frontend/src/index.js" },
      // brickwork.js is a consumed ESM (registerBrickworkComponents), not an
      // app entry: keep its exports instead of tree-shaking them away.
      preserveEntrySignatures: "strict",
      output: {
        entryFileNames: "brickwork.js",
        assetFileNames: (info) =>
          info.names?.some((n) => n.endsWith(".css")) ? "brickwork.css" : "[name][extname]",
      },
      // Promote build warnings to hard errors so broken output cannot ship green.
      onwarn(warning) {
        throw new Error(`vite build warning promoted to error: ${warning.message}`);
      },
    },
  },
});
