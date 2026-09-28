#!/usr/bin/env node
/**
 * Pull migrated token + CSS units from icvoss/brickwork into this mirror.
 *
 * Usage:
 *   node scripts/sync-from-monorepo.mjs [--monorepo /path/to/brickwork]
 *
 * Env: BRICKWORK_MONOREPO
 */
import { createHash } from "node:crypto"
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, resolve } from "node:path"
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

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex")
}

function findMonorepo() {
  const argIdx = process.argv.indexOf("--monorepo")
  if (argIdx >= 0 && process.argv[argIdx + 1]) return resolve(process.argv[argIdx + 1])
  if (process.env.BRICKWORK_MONOREPO) return resolve(process.env.BRICKWORK_MONOREPO)
  let dir = ROOT
  for (let i = 0; i < 8; i++) {
    for (const rel of [
      "private/brickwork",
      "private/brickwork/.claude/worktrees/wave-d-lockstep",
    ]) {
      const candidate = resolve(dir, rel)
      if (existsSync(resolve(candidate, "packages/tokens/src/dtcg"))) return candidate
    }
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return null
}

const mono = findMonorepo()
if (!mono) {
  console.error("Could not find icvoss/brickwork checkout. Pass --monorepo PATH or set BRICKWORK_MONOREPO.")
  process.exit(1)
}

const tokenSrc = resolve(mono, "packages/tokens/src/dtcg")
const tokenDest = resolve(ROOT, "src/brickwork/tokens/source")
const cssSrc = resolve(mono, "packages/css/src/layers")
const cssDest = resolve(ROOT, "frontend/src")

mkdirSync(tokenDest, { recursive: true })
const units = { tokens: {}, css: {} }

for (const name of TOKEN_FILES) {
  const from = resolve(tokenSrc, name)
  const to = resolve(tokenDest, name)
  copyFileSync(from, to)
  units.tokens[name] = sha256(from)
}
for (const name of CSS_FILES) {
  const from = resolve(cssSrc, name)
  const to = resolve(cssDest, name)
  copyFileSync(from, to)
  units.css[name] = sha256(from)
}

const manifest = {
  version: 1,
  migrated_units: ["tokens", "css-layers"],
  editorial_home: "icvoss/brickwork",
  synced_at: new Date().toISOString(),
  units,
}
writeFileSync(resolve(ROOT, "lockstep-manifest.json"), JSON.stringify(manifest, null, 2) + "\n")
console.log(`Synced from ${mono}`)
