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

// 0.11.0 tier re-grammar (ADR-054 section 2/7, brickwork Phase b). The source
// keeps its historical structure so references resolve; the CANONICAL public
// names are produced here by a rename map applied to the captured names, and
// every OLD name ships as a courtesy alias block (old: var(--new);) on :root so
// a 0.10.0 consumer does not break on the minor (aliases are a documented,
// time-boxed 0.x courtesy per ADR section 7). `bw-` prefix, no leading `--`.
const RENAMES = new Map([
  // Scale promotions: the scale IS the role vocabulary, so it is semantic; drop
  // the `size-` infix (--bw-size-space-* -> --bw-space-*, likewise radius).
  ...spaceRadiusRenames(),
  // Icon-size dedup: both the primitive scale (size-icon-*) and its component
  // alias (icon-size-*) collapse to one component-tier name.
  ...iconSizeRenames(),
  // Component tier: the canonical --bw-component-* grammar for the un-infixed
  // component tokens.
  ["bw-button-radius", "bw-component-button-radius"],
  ["bw-icon-stroke-width", "bw-component-icon-stroke-width"],
  ["bw-content-max-width", "bw-component-content-max-width"],
  ["bw-content-max-width-marketing", "bw-component-content-max-width-marketing"],
  ["bw-section-gap-marketing", "bw-component-section-gap-marketing"],
  ["bw-logo-height", "bw-component-logo-height"],
  ["bw-topbar-position", "bw-component-topbar-position"],
  ["bw-disabled-opacity", "bw-component-disabled-opacity"],
  ["bw-menu-min-width", "bw-component-menu-min-width"],
  ["bw-select-indicator", "bw-component-select-indicator"],
  ["bw-checkbox-glyph", "bw-component-checkbox-glyph"],
  ["bw-stat-tile-value-size", "bw-component-stat-tile-value-size"],
  ["bw-stat-tile-sparkline-height", "bw-component-stat-tile-sparkline-height"],
  ["bw-drawer-width", "bw-component-drawer-width"],
  ["bw-toast-max-width", "bw-component-toast-max-width"],
  ["bw-htmx-indicator-opacity", "bw-component-htmx-indicator-opacity"],
  ["bw-progress-track-height", "bw-component-progress-track-height"],
  ["bw-ranked-list-bar-thickness", "bw-component-ranked-list-bar-thickness"],
  ["bw-ranked-list-row-gap", "bw-component-ranked-list-row-gap"],
  ["bw-sparkline-stroke-width", "bw-component-sparkline-stroke-width"],
  ["bw-sparkline-marker-radius", "bw-component-sparkline-marker-radius"],
  ["bw-tooltip-max-width", "bw-component-tooltip-max-width"],
  ["bw-toggle-track-width", "bw-component-toggle-track-width"],
  ["bw-toggle-track-height", "bw-component-toggle-track-height"],
  ["bw-toggle-thumb-size", "bw-component-toggle-thumb-size"],
  ["bw-toggle-thumb-inset", "bw-component-toggle-thumb-inset"],
  // Re-tier nav/skeleton/breadcrumb per-component roles from semantic COLOUR to
  // component tier (they are per-component, not role-general; ADR section 2).
  // Values stay theme-variant (emitted in the theme blocks); only the name moves.
  ["bw-color-nav-item-active-bg", "bw-component-nav-item-active-bg"],
  ["bw-color-nav-item-active-text", "bw-component-nav-item-active-text"],
  ["bw-color-nav-item-active-border", "bw-component-nav-item-active-border"],
  ["bw-color-nav-item-disabled-text", "bw-component-nav-item-disabled-text"],
  ["bw-color-nav-section-text", "bw-component-nav-section-text"],
  ["bw-color-breadcrumb-current", "bw-component-breadcrumb-current"],
  ["bw-color-breadcrumb-separator", "bw-component-breadcrumb-separator"],
  ["bw-color-skeleton-bg", "bw-component-skeleton-bg"],
  ["bw-color-skeleton-shimmer", "bw-component-skeleton-shimmer"],
]);

function spaceRadiusRenames() {
  const spaceSteps = ["0", "px", "0-5", "1", "1-5", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "16", "20", "24"];
  const radiusSteps = ["none", "sm", "md", "lg", "xl", "2xl", "full"];
  return [
    ...spaceSteps.map((s) => [`bw-size-space-${s}`, `bw-space-${s}`]),
    ...radiusSteps.map((s) => [`bw-size-radius-${s}`, `bw-radius-${s}`]),
  ];
}
function iconSizeRenames() {
  const steps = ["sm", "md", "lg", "xl", "2xl"];
  return steps.flatMap((s) => [
    [`bw-icon-size-${s}`, `bw-component-icon-size-${s}`],
    [`bw-size-icon-${s}`, `bw-component-icon-size-${s}`],
  ]);
}

// Apply the rename to a captured token name; unmapped names pass through.
const canonical = (name) => RENAMES.get(name) ?? name;

// Rewrite every var(--bw-<old>) reference inside a derived expression to its
// canonical name, so a derivation pointing at a re-tiered token still resolves.
function renameRefs(expr) {
  if (!expr) return expr;
  return expr.replace(/var\(--(bw-[a-z0-9-]+)\)/g, (m, name) => `var(--${canonical(name)})`);
}

// The set of OLD names that were emitted in 0.10.0 and are kept as aliases (the
// icon-size dedup maps two old names to one canonical, so both are aliased).
const ALIAS_OLD_NAMES = [...RENAMES.keys()];

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
            // 0.11.0: emit the canonical (renamed) name. The old name is kept as
            // an alias block (see main()).
            name: canonical(t.name),
            value: t.$value ?? t.value,
            // Live derivation expression (DESIGN.md section 3): when present it is
            // emitted as the CSS value instead of the resolved $value, so a brand
            // override of a load-bearing token recolours the family in-browser.
            // $value stays the resolved-default regression baseline. Any --bw-*
            // reference inside the expression is renamed too, so a derivation that
            // points at a re-tiered token (skeleton-shimmer -> skeleton-bg) keeps
            // resolving after the rename.
            derived: renameRefs(t.$extensions?.bw?.derived),
            // The whole bw extension block, so the manifest emitter (brickwork#39)
            // can read loadBearing / constraint metadata straight from the token.
            bw: t.$extensions?.bw,
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
  // Viewport breakpoints (ADR-079, brickwork#220): their own layer, not part
  // of the primitive/component/density composition above. They are emitted
  // to tokens.css unconditionally, unlike primitives (which are build-time
  // input only, see notPrimitive below), because they ARE the public
  // contract SHL-014 names, and to a plain (not inline) @theme block in
  // tailwind-theme.css, because a media query cannot resolve var().
  const breakpoints = await buildLayer([`${SRC}/breakpoint.tokens.json`]);

  // Semantic tokens only (drop the primitive.* names) for the theme blocks, so
  // switching data-theme flips only the theme-variant roles (colour, state
  // overlays, elevation), not the raw ramp or the sizing/density scales. The
  // theme layers are built by merging the primitive file (so references
  // resolve), so filter to the theme-variant name families here.
  const themePrefixes = ["bw-color-", "bw-state-", "bw-elevation-"];
  // The nav/skeleton/breadcrumb per-component roles were re-tiered out of the
  // semantic colour family into --bw-component-* (0.11.0), but they remain
  // theme-variant values (authored per theme in the semantic source), so they
  // must still land in the theme blocks, not on :root. They are exactly the
  // canonical names produced by renaming a bw-color-* source token.
  const reTieredThemeNames = new Set(
    [...RENAMES.entries()].filter(([oldName]) => oldName.startsWith("bw-color-")).map(([, newName]) => newName),
  );
  const themeOnly = (tokens) =>
    tokens.filter(
      (t) => themePrefixes.some((p) => t.name.startsWith(p)) || reTieredThemeNames.has(t.name),
    );

  const header =
    "/* django-brickwork design tokens. GENERATED from src/brickwork/tokens/source/**.\n" +
    " * Do NOT edit by hand: run `npm run build:tokens`. Names are the versioned\n" +
    " * public contract (BR-BW-TOK-001); values are brand-overridable. oklch,\n" +
    " * dark authored not derived (BR-BW-TOK-002/003). */\n";

  // :root carries the base (component + sizing + light colours + the default
  // comfortable density). data-theme flips only colours; data-density flips only
  // the density scale.
  //
  // 0.11.0 (ADR-054 section 2): primitives are BUILD-TIME INPUT ONLY and are no
  // longer emitted to the browser (they leaked onto :root through 0.10.0,
  // inviting var(--bw-primitive-*) which the contract forbids). Style Dictionary
  // has already resolved every semantic reference to a literal by this point, so
  // dropping them from the emitted set changes no resolved value.
  const notPrimitive = (t) => !t.name.startsWith("bw-primitive-");
  const emittedBase = base.filter(notPrimitive);
  const rootTokens = [...emittedBase, ...themeOnly(light), ...densities.comfortable, ...breakpoints];

  // Courtesy alias blocks (ADR-054 section 7): every 0.10.0 name that was renamed
  // ships as `old: var(--new);` so a consumer on the old name does not break on
  // this minor. Aliases are theme-agnostic references (the new name resolves to
  // its own theme-variant value), so one :root block covers all axes. The two
  // icon-size old names both alias the single canonical name.
  const emittedNow = new Set([...rootTokens, ...themeOnly(dark)].map((t) => t.name));
  const aliasLines = ALIAS_OLD_NAMES
    .filter((old) => emittedNow.has(canonical(old)))
    .sort()
    .map((old) => `  --${old}: var(--${canonical(old)});`);
  const aliasBlock =
    "/* 0.10.0 -> 0.11.0 courtesy aliases (ADR-054 section 7): the renamed tokens\n" +
    " * kept under their old names so a 0.10.0 consumer does not break on this\n" +
    " * minor. Time-boxed for the 0.x window; prefer the canonical names. */\n" +
    `:root {\n${aliasLines.join("\n")}\n}`;

  const cssParts = [
    header,
    cssBlock(":root", rootTokens),
    cssBlock('[data-theme="light"]', themeOnly(light)),
    cssBlock('[data-theme="dark"]', themeOnly(dark)),
    cssBlock('[data-density="comfortable"]', densities.comfortable),
    cssBlock('[data-density="compact"]', densities.compact),
    cssBlock('[data-density="spacious"]', densities.spacious),
    aliasBlock,
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
  // Every radius step: --radius-<step> from --bw-radius-<step> (0.11.0 canonical
  // name; was --bw-size-radius-* through 0.10.0).
  for (const t of base) {
    if (t.name.startsWith("bw-radius-")) {
      project(`radius-${t.name.slice("bw-radius-".length)}`, t.name);
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
  // The spacing scale, via the dynamic base only (0.11.0 canonical name; was
  // --bw-size-space-1 through 0.10.0).
  if (baseNames.has("bw-space-1")) project("spacing", "bw-space-1");
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
  // Plain @theme breakpoint block (ADR-079, brickwork#220): deliberately NOT
  // @theme inline. A media query cannot resolve var(), so the breakpoint
  // scale below is plain literals, generated from the SAME source
  // (breakpoint.tokens.json) as the --bw-breakpoint-* literals emitted to
  // tokens.css, so the two never drift from each other. This is a second,
  // distinct mechanism from the semantic @theme inline projection below it:
  // that one is live-adjustable with no rebuild (colours, radius, etc.);
  // this one is compiled into a consumer's own Tailwind build like any other
  // @theme value, and does not (and cannot) reach back into brickwork's own
  // shipped brickwork.css breakpoints (the honest limit, ADR-079 section 7).
  const breakpointTheme =
    "/* GENERATED: plain @theme breakpoint bridge (ADR-079), NOT @theme inline.\n" +
    " * Media queries cannot resolve var(), so these are literals, generated\n" +
    " * from the same source as the --bw-breakpoint-* tokens in tokens.css.\n" +
    " * Aligns a consumer's own sm:/md:/lg:/xl: utilities with brickwork's\n" +
    " * breakpoints. Do not edit by hand. */\n" +
    "@theme {\n" +
    breakpoints.map((t) => `  --breakpoint-${t.name.slice("bw-breakpoint-".length)}: ${t.value};`).join("\n") +
    "\n}\n";

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
  writeFileSync(resolve(DIST, "tailwind-theme.css"), breakpointTheme + "\n" + tailwind, "utf8");

  // JS re-export: the flat name -> css-var-reference map, for a Vite consumer or
  // a chart adapter reading a token via getComputedStyle (used sparingly).
  const allNames = [...new Set([...base, ...light, ...Object.values(densities).flat(), ...breakpoints].map((t) => t.name))].sort();
  const jsBody =
    "// GENERATED: brickwork token names, as CSS custom-property references.\n" +
    "// Read a live value with getComputedStyle(el).getPropertyValue(tokens.X).\n" +
    "export const tokens = Object.freeze({\n" +
    allNames.map((n) => `  ${JSON.stringify(n.replace(/^bw-/, "").replace(/-/g, "_"))}: "var(--${n})",`).join("\n") +
    "\n});\nexport default tokens;\n";
  writeFileSync(resolve(DIST, "tokens.js"), jsBody, "utf8");

  // Contract manifest (brickwork#39): a machine-readable description of the
  // load-bearing brand set and the full overridable vocabulary, so a consumer
  // building a theming UI (or the render_brand_css emitter, brickwork#40) reads
  // the set, its types and its constraints instead of hard-coding token names
  // that semver could move. Derived from the annotated DTCG source, so the
  // manifest and the tokens can never drift. The load-bearing metadata is
  // theme-independent (both themes carry the same flags), so we read it off the
  // light layer; a token's presence in the theme-only set marks it theme-variant.
  const loadBearing = [];
  // contrastPairs (brickwork#289): constraints between a DERIVED token and one
  // or more backgrounds it is actually painted on, as opposed to loadBearing's
  // "a brand authors this" list. --bw-color-X-fg is never brand-authored under
  // the DERIVE fix (it tracks --bw-color-surface live), so it does not belong
  // in loadBearing, but the pairings it forms still need an independently
  // checkable contrast floor: a brand overriding the status hue, or
  // hand-authoring one side of a pair, can still break it. A source token may
  // declare more than one contrastPair (blocker 2, review round 2): X-fg is
  // painted on both X-subtle AND plain surface (.bw-field__error,
  // .bw-stat__trend, .bw-account-menu__item--danger), so both backgrounds get
  // their own manifest entry, not just the first one found. Each entry carries
  // BOTH sides' derived expressions (not just the source token's; a
  // load-bearing pair target like --bw-color-surface resolves to a var()
  // reference to itself, since it IS the value), so a validator can resolve
  // the pair's effective colours even when neither side is an explicit
  // override (e.g. only --bw-color-surface was overridden).
  const contrastPairs = [];
  const byName = new Map(themeOnly(light).map((t) => [t.name, t]));
  for (const t of themeOnly(light)) {
    const meta = t.bw;
    if (meta?.loadBearing) {
      // Names are the --bw-* custom-property form throughout the manifest, so a
      // consumer uses them directly (no prefix reconstruction).
      const entry = { name: `--${t.name}` };
      if (meta.conditional) entry.conditional = true;
      if (meta.authoredPerTheme) entry.authoredPerTheme = true;
      if (meta.contrastPair) {
        entry.contrastPair = `--bw-${meta.contrastPair}`;
        entry.minContrast = meta.minContrast ?? 4.5;
      }
      if (meta.collapsesTo) entry.collapsesTo = `--bw-${meta.collapsesTo}`;
      loadBearing.push(entry);
    } else if (meta?.contrastPair) {
      // brickwork#289 blocker 2: a status -fg token is painted on more than one
      // background (its own -subtle tint AND, via .bw-field__error /
      // .bw-stat__trend / .bw-account-menu__item--danger, plain surface), so
      // contrastPair accepts either a single string (the common case) or an
      // array of strings, one manifest entry per background. minContrast is
      // shared across every pair on this token (all four families use 4.5
      // today; a per-pair override would need a parallel array, not needed yet).
      const pairs = Array.isArray(meta.contrastPair) ? meta.contrastPair : [meta.contrastPair];
      for (const rawPair of pairs) {
        const pairShortName = rawPair.startsWith("color-") ? `bw-${rawPair}` : `bw-color-${rawPair}`;
        const pairToken = byName.get(pairShortName);
        if (!pairToken) {
          throw new Error(`contrastPair ${rawPair} declared on ${t.name} does not resolve to an emitted token`);
        }
        // A load-bearing pair target (e.g. --bw-color-surface) carries no
        // `derived` expression of its own: it IS the value, so its resolution
        // expression is simply a reference to itself (var(--bw-color-surface)),
        // which _resolve_derived()'s var() branch in brand_css.py already
        // handles. Only a genuinely undefined pair target falls back to null.
        const pairDerived = pairToken.derived ?? (pairToken.bw?.loadBearing ? `var(--${pairToken.name})` : null);
        contrastPairs.push({
          name: `--${t.name}`,
          derived: t.derived ?? null,
          contrastPair: `--${pairToken.name}`,
          pairDerived,
          minContrast: meta.minContrast ?? 4.5,
        });
      }
    }
  }
  // The full set of overridable custom-property names: every emitted semantic and
  // component token (NOT primitives, NOT the raw font/space ramps a brand should
  // not target). A consumer's brand override, and the emitter's validation, work
  // against exactly this set.
  const overridable = [...new Set([...base, ...themeOnly(light), ...densities.comfortable, ...breakpoints].map((t) => t.name))]
    .filter((n) => !n.startsWith("bw-primitive-"))
    .sort()
    .map((n) => `--${n}`);
  const manifest = {
    $schema: "https://brickwork.icvoss.dev/token-manifest/v1",
    version: 1,
    description:
      "brickwork token contract: the load-bearing brand set and its constraints (brickwork#39), " +
      "the full overridable --bw-* vocabulary, and derived-pair contrast constraints (brickwork#289, " +
      "distinct from loadBearing: a contrastPairs entry holds between two DERIVED tokens that a brand " +
      "does not directly author but can still break by overriding one of their inputs). " +
      "Generated from the DTCG source; do not edit by hand.",
    loadBearing,
    contrastPairs,
    overridable,
  };
  writeFileSync(resolve(DIST, "token-manifest.json"), JSON.stringify(manifest, null, 2) + "\n", "utf8");

  console.log(
    `tokens built: ${rootTokens.length} root vars, ` +
      `${themeOnly(dark).length} dark theme overrides, 3 densities -> ${DIST}`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
