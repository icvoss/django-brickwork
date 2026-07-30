// Token build: DTCG source -> stable-named --bw-* artefacts.
//
// Emits three files into src/brickwork/static/brickwork/dist/ with STABLE
// (non-hashed) filenames, versioned by the Python package's semver so consumers
// reference them via plain {% static %} (no django-vite, per the settled
// build-tool decision):
//
//   tokens.css          plain --bw-* custom properties, all four axes as CSS
//                        selectors (:root, [data-theme="dark"], [data-density]).
//   tailwind-theme.css  a Tailwind 4 `@theme inline` fragment bridging --bw-* to
//                        short utility names.
//   tokens.js           a JS re-export of the token names (for a Vite consumer).
//
// Why a custom composer, not vanilla Style Dictionary: the theme and density
// axes must land as SCOPED CSS selectors sharing one token name each, so a live
// `data-theme` / `data-density` switch re-resolves with no recompile. Style
// Dictionary resolves references and formats one flat layer; this script runs it
// per layer and wraps each layer's output in the right selector. Dark values are
// AUTHORED in semantic.dark.tokens.json, never derived here (BR-BW-TOK-002).

import StyleDictionary from "style-dictionary";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = resolve(ROOT, "src/brickwork/tokens/source");
const DIST = resolve(ROOT, "src/brickwork/static/brickwork/dist");

// A token name -> CSS custom property, namespaced --bw-*. Style Dictionary's
// default "css/variables" prefixes with the token path; we force the --bw-
// prefix and drop the leading tier segment ("color", "density") so the public
// names read as --bw-color-surface, --bw-density-control-height, etc.
StyleDictionary.registerTransform({
  name: "name/bw",
  type: "name",
  transform: (token) => `bw-${token.path.join("-")}`,
});

// oklch values pass through untouched (BR-BW-TOK-003: source IS oklch; we do not
// down-convert). The built-in color transforms would coerce to hex/rgb, so we
// deliberately do NOT use them for the colour tier.
const TRANSFORMS = ["attribute/cti", "name/bw"];

async function buildLayer(sourceGlobs) {
  // Build one layer to an in-memory flat list of {name, value} and return it,
  // rather than writing a file per layer. We use a custom format that captures
  // the variables so the composer can wrap them in the right selector.
  let captured = [];
  const sd = new StyleDictionary({
    source: sourceGlobs,
    // The source is DTCG-shaped ($value/$type/$description). Declaring this lets
    // Style Dictionary treat a group's root $description as metadata rather than
    // a nameless token that collides when two source files are merged.
    usesDtcg: true,
    log: { warnings: "error", verbosity: "silent" },
    platforms: {
      capture: {
        transforms: TRANSFORMS,
        files: [{ destination: "unused", format: "bw/capture" }],
      },
    },
    hooks: {
      formats: {
        "bw/capture": ({ dictionary }) => {
          captured = dictionary.allTokens.map((t) => ({
            name: t.name,
            value: t.$value ?? t.value,
          }));
          return "";
        },
      },
    },
  });
  await sd.buildAllPlatforms();
  return captured;
}

function cssBlock(selector, tokens, { indent = "  " } = {}) {
  const lines = tokens.map((t) => `${indent}--${t.name}: ${t.value};`);
  return `${selector} {\n${lines.join("\n")}\n}`;
}

async function main() {
  mkdirSync(DIST, { recursive: true });

  // Base layer: primitive + component + comfortable density (the defaults that
  // sit on :root alongside the light theme). Primitives are emitted too so the
  // semantic references resolve for any consumer reading the raw file.
  const base = await buildLayer([
    `${SRC}/primitive.tokens.json`,
    `${SRC}/component.tokens.json`,
  ]);
  const light = await buildLayer([
    `${SRC}/primitive.tokens.json`,
    `${SRC}/semantic.light.tokens.json`,
  ]);
  const dark = await buildLayer([
    `${SRC}/primitive.tokens.json`,
    `${SRC}/semantic.dark.tokens.json`,
  ]);
  const densities = {};
  for (const mode of ["comfortable", "compact", "spacious"]) {
    densities[mode] = await buildLayer([`${SRC}/density.${mode}.tokens.json`]);
  }

  // Semantic tokens only (drop the primitive.* names) for the theme blocks, so
  // switching data-theme flips only the COLOUR roles, not the raw ramp or the
  // sizing/density scales. The theme layers are built by merging the primitive
  // file (so references resolve), so filter to just --bw-color-* here.
  const colourOnly = (tokens) => tokens.filter((t) => t.name.startsWith("bw-color-"));
  // Component + sizing tokens for :root: everything the base layer produces that
  // is NOT a raw primitive ramp value (those stay available but are not the
  // consumer contract). Semantic colours come from colourOnly(light) separately.
  const nonPrimitive = (tokens) => tokens.filter((t) => !t.name.startsWith("bw-primitive-"));

  const header =
    "/* django-brickwork design tokens. GENERATED from src/brickwork/tokens/source/**.\n" +
    " * Do NOT edit by hand: run `npm run build:tokens`. Names are the versioned\n" +
    " * public contract (BR-BW-TOK-001); values are brand-overridable. oklch,\n" +
    " * dark authored not derived (BR-BW-TOK-002/003). */\n";

  // :root carries the base (primitives + component + sizing + light colours +
  // the default comfortable density). data-theme flips only colours;
  // data-density flips only the density scale.
  const rootTokens = [...base, ...colourOnly(light), ...densities.comfortable];
  const cssParts = [
    header,
    cssBlock(":root", rootTokens),
    cssBlock('[data-theme="light"]', colourOnly(light)),
    cssBlock('[data-theme="dark"]', colourOnly(dark)),
    cssBlock('[data-density="comfortable"]', densities.comfortable),
    cssBlock('[data-density="compact"]', densities.compact),
    cssBlock('[data-density="spacious"]', densities.spacious),
  ];
  writeFileSync(resolve(DIST, "tokens.css"), cssParts.join("\n\n") + "\n", "utf8");

  // Tailwind @theme inline bridge: map the semantic --bw-color-* tokens plus the
  // component/sizing tokens to short Tailwind utility names. Only the semantic
  // and component tiers are bridged (raw primitives are not consumer utilities).
  const bridged = [...colourOnly(light), ...nonPrimitive(base), ...densities.comfortable];
  const seenBridge = new Set();
  const themeVars = bridged
    .filter((t) => !seenBridge.has(t.name) && seenBridge.add(t.name))
    .map((t) => `  --${t.name}: var(--${t.name});`);
  // NOTE: the header comment must NOT contain a literal `@import "..."` string.
  // Django/WhiteNoise ManifestStaticFilesStorage rewrites @import/url() targets by
  // regex WITHOUT skipping comments, so a commented example import is treated as a
  // real reference and fails collectstatic with a MissingFileError (found by the
  // icvlocal.com consumer, brickwork 0.1.0). Describe the import in prose instead.
  const tailwind =
    "/* GENERATED: Tailwind 4 @theme inline bridge for --bw-* semantic tokens.\n" +
    " * Import this fragment in a consumer's entry CSS AFTER the Tailwind import\n" +
    " * (the line that pulls in tailwindcss itself). Do not edit by hand. */\n" +
    "@theme inline {\n" +
    themeVars.join("\n") +
    "\n}\n";
  writeFileSync(resolve(DIST, "tailwind-theme.css"), tailwind, "utf8");

  // JS re-export: the flat name -> css-var-reference map, for a Vite consumer or
  // a chart adapter reading a token via getComputedStyle (used sparingly).
  const allNames = [...new Set([...base, ...light, ...Object.values(densities).flat()].map((t) => t.name))].sort();
  const jsBody =
    "// GENERATED: brickwork token names, as CSS custom-property references.\n" +
    "// Read a live value with getComputedStyle(el).getPropertyValue(tokens.X).\n" +
    "export const tokens = Object.freeze({\n" +
    allNames.map((n) => `  ${JSON.stringify(n.replace(/^bw-/, "").replace(/-/g, "_"))}: "var(--${n})",`).join("\n") +
    "\n});\nexport default tokens;\n";
  writeFileSync(resolve(DIST, "tokens.js"), jsBody, "utf8");

  console.log(
    `tokens built: ${rootTokens.length} root vars, ` +
      `${colourOnly(dark).length} dark colour overrides, 3 densities -> ${DIST}`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
