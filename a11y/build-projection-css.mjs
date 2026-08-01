// Build the projection-proof consumer CSS (AC-BW-095, the dynamic half).
//
// Compiles a REAL Tailwind 4 consumer entry through the same @tailwindcss/node
// compiler the Vite plugin uses: the tailwindcss import first, then the shipped
// dist/tailwind-theme.css fragment AFTER it (the documented consumer import
// order, so the fragment's namespace keys win over the Tailwind defaults, e.g.
// --radius-md). The utility candidates arrive as argv, and
// a11y/generate_fixtures.py owns the single candidate list, so the fixture
// markup and this build can never drift. The compiled CSS goes to stdout for
// the fixture to inline (file:// fixtures are self-contained, the house rule).
//
// Invoked by generate_fixtures.py at fixture-generation time; deliberately not
// part of npm run build (the package ships the fragment, never a compiled
// consumer build).

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { compile } from "@tailwindcss/node";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

const candidates = process.argv.slice(2);
if (candidates.length === 0) {
  console.error("usage: node a11y/build-projection-css.mjs <utility> [<utility> ...]");
  process.exit(1);
}

const fragment = readFileSync(
  join(ROOT, "src", "brickwork", "static", "brickwork", "dist", "tailwind-theme.css"),
  "utf8",
);
const entry = `@import "tailwindcss";\n${fragment}`;

const compiler = await compile(entry, { base: ROOT, onDependency: () => {} });
process.stdout.write(compiler.build(candidates));
