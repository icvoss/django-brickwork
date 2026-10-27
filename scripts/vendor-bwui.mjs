#!/usr/bin/env node
/**
 * Vendor published @bwui/tokens and @bwui/css into the Django wheel.
 *
 * Maintainer pipeline, not a consumer step: pip installers never run this.
 * `npm ci` resolves the pins in package.json; this script copies the
 * published artefacts into src/brickwork/static/brickwork/dist/ so the
 * wheel ships the same substrate as an npm install of those packages.
 *
 * brickwork.css is minified with lightningcss so existing Django contract
 * tests (written against Vite's minified output) keep matching. Alpine JS
 * is still compiled in this repo (Vite).
 */
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import { createRequire } from "node:module"
import { transform } from "lightningcss"

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..")
const DIST = resolve(ROOT, "src/brickwork/static/brickwork/dist")
const require = createRequire(import.meta.url)

function pkgDir(name, exported) {
  try {
    return resolve(dirname(require.resolve(exported)), "..")
  } catch {
    console.error(
      `Cannot resolve ${name} (${exported}). Run npm ci in the django-brickwork ` +
        `repo so the package.json pins are installed.`,
    )
    process.exit(1)
  }
}

const tokensDir = pkgDir("@bwui/tokens", "@bwui/tokens/tokens.css")
const cssDir = pkgDir("@bwui/css", "@bwui/css")
const tokensPkg = JSON.parse(readFileSync(resolve(tokensDir, "package.json"), "utf8"))
const cssPkg = JSON.parse(readFileSync(resolve(cssDir, "package.json"), "utf8"))

mkdirSync(DIST, { recursive: true })

const copies = [
  [resolve(tokensDir, "dist/tokens.css"), resolve(DIST, "tokens.css")],
  [resolve(tokensDir, "dist/tailwind-theme.css"), resolve(DIST, "tailwind-theme.css")],
  [resolve(tokensDir, "dist/tokens.js"), resolve(DIST, "tokens.js")],
]

for (const [from, to] of copies) {
  try {
    copyFileSync(from, to)
  } catch (err) {
    console.error(`Missing published artefact ${from}`)
    console.error(err)
    process.exit(1)
  }
}

const cssFrom = resolve(cssDir, "dist/brickwork.css")
const cssTo = resolve(DIST, "brickwork.css")
const indexCss = resolve(ROOT, "frontend/src/index.css")
try {
  const published = readFileSync(cssFrom)
  const { code: minifiedPublished } = transform({
    filename: "brickwork.css",
    code: published,
    minify: true,
  })
  // @bwui/css 0.1.2 omits the Django index.css extras (box-sizing, hidden
  // floor, skip-link, .bw-icon-directional, focus ring, reduced-motion) and
  // ships a reset plus wave-e demo rules that fail the Django a11y gate.
  // Strip @imports so we do not recompile the lockstep layers, then append
  // extras and the a11y overlays. Drop overlays when a later @bwui/css
  // release lands the same repairs (icvoss/brickwork#11).
  const extrasSource = readFileSync(indexCss, "utf8").replace(/@import\s+[^;]+;/g, "").trim()
  const { code: minifiedExtras } = transform({
    filename: "index-extras.css",
    code: Buffer.from(extrasSource),
    minify: true,
  })
  const overlayCss = resolve(ROOT, "frontend/src/vendor-overlays.css")
  const { code: minifiedOverlays } = transform({
    filename: "vendor-overlays.css",
    code: readFileSync(overlayCss),
    minify: true,
  })
  writeFileSync(
    cssTo,
    Buffer.concat([
      minifiedPublished,
      Buffer.from("\n"),
      minifiedExtras,
      Buffer.from("\n"),
      minifiedOverlays,
    ]),
  )
} catch (err) {
  console.error(`Cannot vendor minified ${cssFrom}`)
  console.error(err)
  process.exit(1)
}

const pin = {
  tokens: tokensPkg.version,
  css: cssPkg.version,
  vendored: [...copies.map(([, to]) => to.slice(DIST.length + 1)), "brickwork.css"],
}

writeFileSync(resolve(DIST, "bwui-pin.json"), JSON.stringify(pin, null, 2) + "\n", "utf8")

console.log(
  `Vendored @bwui/tokens@${tokensPkg.version} and minified @bwui/css@${cssPkg.version} -> ${DIST}`,
)
