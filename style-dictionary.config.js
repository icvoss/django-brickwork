// Style Dictionary config for the saas_ui design tokens.
// SCAFFOLD STUB: the real config lands in Phase 0 (spec open question 1/2).
// It will: read the DTCG source in src/saas_ui/tokens/source/**, resolve the
// four composable axes (brand x theme x density x direction), and emit thin
// custom formatters -> tokens.css, theme.css (@theme inline bridge), tokens.js
// into src/saas_ui/static/saas_ui/dist/ with STABLE filenames.
// Style Dictionary major is pinned; only a restricted DTCG subset is used
// (v4 does not yet fully support DTCG 2025.10).
export default {
  source: ["src/saas_ui/tokens/source/**/*.tokens.json"],
  platforms: {
    // css: { transformGroup: "css", buildPath: "src/saas_ui/static/saas_ui/dist/", files: [...] }
  },
};
