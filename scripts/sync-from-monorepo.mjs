#!/usr/bin/env node
/**
 * Pull migrated units from icvoss/brickwork into this release mirror.
 * Editorial home is the monorepo; edit there, then sync. Updates
 * lockstep-manifest.json.
 *
 * Units: tokens, css (product layers), templates (Django templates),
 * frontend-js (Vite entry: index.js, index.css, js/).
 *
 * Usage:
 *   node scripts/sync-from-monorepo.mjs [--monorepo /path/to/brickwork]
 *
 * Env: BRICKWORK_MONOREPO
 *
 * Keep the unit table in step with brickwork/scripts/sync-to-django.mjs.
 */
import { createHash } from "node:crypto"
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs"
import { dirname, join, relative, resolve, sep } from "node:path"
import { fileURLToPath } from "node:url"

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..")
const TOKEN_FILES = [
  "breakpoint.tokens.json",
  "component.tokens.json",
  "density.comfortable.tokens.json",
  "density.compact.tokens.json",
  "density.spacious.tokens.json",
  "motion.tokens.json",
  "primitive.tokens.json",
  "semantic.dark.tokens.json",
  "semantic.light.tokens.json",
  "typography.tokens.json",
]
const CSS_FILES = ["shell.css", "nav.css", "components.css", "marketing.css"]

/**
 * Tree units: each entry maps a monorepo path to a Django mirror path.
 * Manifest keys are POSIX paths relative to the unit's key root (the parent
 * of the mapped names below). `pruneDirs` are mirror directories where files
 * absent from the monorepo are removed, so deletions propagate.
 */
const TEMPLATE_MAP = [
  { from: "django/templates/brickwork", to: "src/brickwork/templates/brickwork", key: "brickwork" },
  {
    from: "django/templates/brickwork_marketing",
    to: "src/brickwork/marketing/templates/brickwork_marketing",
    key: "brickwork_marketing",
  },
]
const FRONTEND_JS_DIRS = [{ from: "django/frontend/src/js", to: "frontend/src/js", key: "js" }]
const FRONTEND_JS_FILES = ["index.js", "index.css"]

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex")
}

function walk(dir) {
  const out = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) out.push(...walk(full))
    else if (entry.isFile()) out.push(full)
  }
  return out.sort()
}

function posix(p) {
  return p.split(sep).join("/")
}

function fail(message) {
  console.error(message)
  process.exit(1)
}

function findMonorepo() {
  const argIdx = process.argv.indexOf("--monorepo")
  if (argIdx >= 0 && process.argv[argIdx + 1]) return resolve(process.argv[argIdx + 1])
  if (process.env.BRICKWORK_MONOREPO) return resolve(process.env.BRICKWORK_MONOREPO)

  // A Django worktree pairs with the monorepo worktree of the same slug.
  const worktree = posix(ROOT).match(/^(.*)\/public\/django-brickwork\/\.claude\/worktrees\/([^/]+)$/)
  if (worktree) {
    const paired = resolve(worktree[1], "private/brickwork/.claude/worktrees", worktree[2])
    if (existsSync(resolve(paired, "packages/tokens/src/dtcg"))) return paired
  }

  let dir = ROOT
  for (let i = 0; i < 8; i++) {
    const candidate = resolve(dir, "private/brickwork")
    if (existsSync(resolve(candidate, "packages/tokens/src/dtcg"))) return candidate
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return null
}

/** Copy one tree; returns {relKey: sha256}. Prunes mirror files not in source. */
function syncTree({ from, to, key }, mono) {
  const src = resolve(mono, from)
  const dest = resolve(ROOT, to)
  if (!existsSync(src)) fail(`Missing monorepo tree ${src}`)
  const hashes = {}
  const kept = new Set()
  for (const file of walk(src)) {
    const rel = posix(relative(src, file))
    const target = resolve(dest, rel)
    mkdirSync(dirname(target), { recursive: true })
    copyFileSync(file, target)
    hashes[`${key}/${rel}`] = sha256(file)
    kept.add(target)
  }
  if (existsSync(dest)) {
    for (const file of walk(dest)) {
      if (!kept.has(file)) rmSync(file)
    }
  }
  return hashes
}

const mono = findMonorepo()
if (!mono) fail("Could not find icvoss/brickwork checkout. Pass --monorepo PATH or set BRICKWORK_MONOREPO.")

const tokenSrc = resolve(mono, "packages/tokens/src/dtcg")
const tokenDest = resolve(ROOT, "src/brickwork/tokens/source")
const cssSrc = resolve(mono, "packages/css/src/layers")
const cssDest = resolve(ROOT, "frontend/src")
const jsSrcRoot = resolve(mono, "django/frontend/src")

mkdirSync(tokenDest, { recursive: true })
const units = { tokens: {}, css: {}, templates: {}, "frontend-js": {} }

for (const name of TOKEN_FILES) {
  const from = resolve(tokenSrc, name)
  if (!existsSync(from)) fail(`Missing token source ${from}`)
  copyFileSync(from, resolve(tokenDest, name))
  units.tokens[name] = sha256(from)
}

for (const name of CSS_FILES) {
  const from = resolve(cssSrc, name)
  if (!existsSync(from)) fail(`Missing CSS layer ${from}`)
  copyFileSync(from, resolve(cssDest, name))
  units.css[name] = sha256(from)
}

for (const spec of TEMPLATE_MAP) Object.assign(units.templates, syncTree(spec, mono))

for (const spec of FRONTEND_JS_DIRS) Object.assign(units["frontend-js"], syncTree(spec, mono))
for (const name of FRONTEND_JS_FILES) {
  const from = resolve(jsSrcRoot, name)
  if (!existsSync(from) || !statSync(from).isFile()) fail(`Missing frontend entry ${from}`)
  copyFileSync(from, resolve(cssDest, name))
  units["frontend-js"][name] = sha256(from)
}

const manifestPath = resolve(ROOT, "lockstep-manifest.json")
const migrated_units = ["tokens", "css-layers", "templates", "frontend-js"]
let syncedAt = new Date().toISOString()
if (existsSync(manifestPath)) {
  // Keep the timestamp when nothing changed, so a re-run is a true no-op.
  const previous = JSON.parse(readFileSync(manifestPath, "utf8"))
  if (JSON.stringify(previous.units) === JSON.stringify(units) && previous.synced_at) {
    syncedAt = previous.synced_at
  }
}
const manifest = {
  version: 2,
  migrated_units,
  editorial_home: "icvoss/brickwork",
  synced_at: syncedAt,
  units,
}
writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n")
console.log(`Synced from ${mono}`)
console.log(
  `Wrote lockstep-manifest.json (${Object.keys(units.tokens).length} tokens, ` +
    `${Object.keys(units.css).length} css, ${Object.keys(units.templates).length} templates, ` +
    `${Object.keys(units["frontend-js"]).length} frontend-js)`,
)
