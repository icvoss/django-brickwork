// Style Dictionary config for the brickwork design tokens.
// SCAFFOLD STUB: the real config lands in Phase 0 (spec open question 1/2).
// It will: read the DTCG source in src/brickwork/tokens/source/**, resolve the
// four composable axes (brand x theme x density x direction), and emit thin
// custom formatters -> tokens.css, theme.css (@theme inline bridge), tokens.js
// into src/brickwork/static/brickwork/dist/ with STABLE filenames.
// Style Dictionary major is pinned; only a restricted DTCG subset is used
// (v4 does not yet fully support DTCG 2025.10).
export default {
  source: ["src/brickwork/tokens/source/**/*.tokens.json"],
  platforms: {
    // css: { transformGroup: "css", buildPath: "src/brickwork/static/brickwork/dist/", files: [...] }
  },
};
