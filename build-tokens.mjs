// Token build: DTCG source -> stable-named --bw-* artefacts.
//
// Emits three files into src/brickwork/static/brickwork/dist/ with STABLE
// (non-hashed) filenames, versioned by the Python package's semver so consumers
// reference them via plain {% static %} (no django-vite, per the settled
// build-tool decision):
//
//   tokens.css          plain --bw-* custom properties, all four axes as CSS
//                        selectors (:root, [data-theme="dark"], [data-density]).
//   tailwind-theme.css  a Tailwind 4 `@theme inline` projection of the semantic
//                        --bw-* contract into Tailwind's utility namespaces
//                        (ADR-054 section 4), imported by a consumer AFTER the
//                        tailwindcss import.
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
            // Live derivation expression (DESIGN.md section 3): when present it is
            // emitted as the CSS value instead of the resolved $value, so a brand
            // override of a load-bearing token recolours the family in-browser.
            // $value stays the resolved-default regression baseline.
            derived: t.$extensions?.bw?.derived,
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
  // A derived token emits its live expression as the single declaration (no
  // fallback line: color-mix is Baseline Widely Available, DESIGN.md section 3).
  const lines = tokens.map((t) => `${indent}--${t.name}: ${t.derived ?? t.value};`);
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
    `${SRC}/typography.tokens.json`,
    `${SRC}/motion.tokens.json`,
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
  // switching data-theme flips only the theme-variant roles (colour, state
  // overlays, elevation), not the raw ramp or the sizing/density scales. The
  // theme layers are built by merging the primitive file (so references
  // resolve), so filter to the theme-variant name families here.
  const themePrefixes = ["bw-color-", "bw-state-", "bw-elevation-"];
  const themeOnly = (tokens) =>
    tokens.filter((t) => themePrefixes.some((p) => t.name.startsWith(p)));

  const header =
    "/* django-brickwork design tokens. GENERATED from src/brickwork/tokens/source/**.\n" +
    " * Do NOT edit by hand: run `npm run build:tokens`. Names are the versioned\n" +
    " * public contract (BR-BW-TOK-001); values are brand-overridable. oklch,\n" +
    " * dark authored not derived (BR-BW-TOK-002/003). */\n";

  // :root carries the base (primitives + component + sizing + light colours +
  // the default comfortable density). data-theme flips only colours;
  // data-density flips only the density scale.
  const rootTokens = [...base, ...themeOnly(light), ...densities.comfortable];
  const cssParts = [
    header,
    cssBlock(":root", rootTokens),
    cssBlock('[data-theme="light"]', themeOnly(light)),
    cssBlock('[data-theme="dark"]', themeOnly(dark)),
    cssBlock('[data-density="comfortable"]', densities.comfortable),
    cssBlock('[data-density="compact"]', densities.compact),
    cssBlock('[data-density="spacious"]', densities.spacious),
  ];
  writeFileSync(resolve(DIST, "tokens.css"), cssParts.join("\n\n") + "\n", "utf8");

  // Tailwind @theme inline projection (ADR-054 section 4): map the SEMANTIC
  // --bw-* contract into Tailwind 4's utility namespaces so a consumer's own
  // utilities (bg-accent, rounded-md, shadow-3, text-heading-lg, p-4) inherit
  // the brand. Every mapped value is a var(--bw-*) reference, never a literal,
  // so data-theme / data-bw-brand switching recolours consumer utilities with
  // zero rebuild (which is also why the block must be `@theme inline`).
  //
  // Coverage is the semantic visual contract ONLY, walked from the token data:
  // colours, radius steps, elevation ladder, type roles (size + line-height),
  // font stacks, the dynamic --spacing base, and the two --default-* font keys.
  // Deliberately NOT projected: component-tier tokens, state overlays, z-index,
  // opacity, motion, focus ring geometry (--bw-focus-*; the ring COLOUR is a
  // semantic colour and projects with that family), density, borders, icons,
  // and the raw font/space scales (roles and the --spacing base are the
  // consumer surface). Our entries
  // ADD semantic names alongside Tailwind's own palette (no --color-* wildcard
  // wipe: a consumer may still want blue-500 for one-off content); the one
  // deliberate global override is --spacing, which works because the space
  // scale is authored as Tailwind --spacing multiples of 0.25rem (DESIGN.md
  // section 6.1), so p-4 stays 1rem by default yet rescales with the brand.
  const baseNames = new Set(base.map((t) => t.name));
  const projected = [];
  const seenProjection = new Set();
  const project = (utilityKey, bwName) => {
    if (seenProjection.has(utilityKey)) return;
    seenProjection.add(utilityKey);
    projected.push(`  --${utilityKey}: var(--${bwName});`);
  };
  // Every semantic colour: --color-<name> from --bw-color-<name>.
  for (const t of themeOnly(light)) {
    if (t.name.startsWith("bw-color-")) {
      project(`color-${t.name.slice("bw-color-".length)}`, t.name);
    }
  }
  // Every radius step: --radius-<step> from --bw-size-radius-<step>.
  for (const t of base) {
    if (t.name.startsWith("bw-size-radius-")) {
      project(`radius-${t.name.slice("bw-size-radius-".length)}`, t.name);
    }
  }
  // The elevation ladder: --shadow-<level> from --bw-elevation-<level>.
  for (const t of themeOnly(light)) {
    if (t.name.startsWith("bw-elevation-")) {
      project(`shadow-${t.name.slice("bw-elevation-".length)}`, t.name);
    }
  }
  // The type roles: --text-<role> from --bw-text-<role>-size, plus Tailwind 4's
  // companion key --text-<role>--line-height where the role has a line-height
  // token (all roles do today; guarded so a future role without one is safe).
  for (const t of base) {
    const role = t.name.match(/^bw-text-(.+)-size$/)?.[1];
    if (!role) continue;
    project(`text-${role}`, t.name);
    const lineHeight = `bw-text-${role}-line-height`;
    if (baseNames.has(lineHeight)) project(`text-${role}--line-height`, lineHeight);
  }
  // The font stacks: --font-<name> from --bw-font-family-<name>.
  for (const t of base) {
    if (t.name.startsWith("bw-font-family-")) {
      project(`font-${t.name.slice("bw-font-family-".length)}`, t.name);
    }
  }
  // The spacing scale, via the dynamic base only.
  if (baseNames.has("bw-size-space-1")) project("spacing", "bw-size-space-1");
  // Preflight defaults follow the brand stacks.
  if (baseNames.has("bw-font-family-sans")) {
    project("default-font-family", "bw-font-family-sans");
  }
  if (baseNames.has("bw-font-family-mono")) {
    project("default-mono-font-family", "bw-font-family-mono");
  }
  // NOTE: the header comment must NOT contain a literal `@import "..."` string.
  // Django/WhiteNoise ManifestStaticFilesStorage rewrites @import/url() targets by
  // regex WITHOUT skipping comments, so a commented example import is treated as a
  // real reference and fails collectstatic with a MissingFileError (found by the
  // icvlocal.com consumer, brickwork 0.1.0). Describe the import in prose instead.
  const tailwind =
    "/* GENERATED: Tailwind 4 @theme inline projection of the --bw-* semantic\n" +
    " * contract into Tailwind's utility namespaces (ADR-054 section 4), so\n" +
    " * consumer utilities inherit the brand and both themes: colours, radius,\n" +
    " * elevation (shadow-*), type roles (text-<role>), font stacks, and the\n" +
    " * dynamic --spacing base. Every value is a var(--bw-*) reference, so theme\n" +
    " * and brand switching recolours consumer utilities with no rebuild.\n" +
    " * Import this fragment in a consumer's entry CSS AFTER the Tailwind import\n" +
    " * (the line that pulls in tailwindcss itself). Do not edit by hand. */\n" +
    "@theme inline {\n" +
    projected.join("\n") +
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
      `${themeOnly(dark).length} dark theme overrides, 3 densities -> ${DIST}`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
