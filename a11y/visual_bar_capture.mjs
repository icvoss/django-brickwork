/**
 * Capture VISUAL-BAR scorecard stills (Phase 1.1 + Phase 4.3 brand leg).
 *
 * Loads fixtures from a11y/fixtures/visual-bar/ (package-only) or
 * a11y/fixtures/visual-bar-<brand>/ when VISUAL_BAR_BRAND is set. Capture at
 * light and dark, desktop ~1440px and phone ~375px. Writes PNGs under
 * docs/audits/_stills/<date>/ (package-only) or
 * docs/audits/_stills/<date>-<brand>/ (brand leg). Not a CI gate.
 *
 * Run:
 *   npm run visual-bar:fixtures
 *   npm run visual-bar:capture
 *
 * Brand pack (northline skeleton):
 *   npm run visual-bar:fixtures:northline
 *   npm run visual-bar:capture:northline
 *
 * Optional:
 *   VISUAL_BAR_STILLS_DATE=2026-09-11 npm run visual-bar:capture
 */

import { chromium } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(HERE);

const VIEWPORTS = [
  { label: "1440", width: 1440, height: 900 },
  { label: "375", width: 375, height: 812 },
];
const THEMES = ["light", "dark"];
const KNOWN_BRANDS = new Set(["northline"]);

function brandFromEnv() {
  const raw = (process.env.VISUAL_BAR_BRAND || "").trim();
  if (!raw) {
    return "";
  }
  if (!KNOWN_BRANDS.has(raw)) {
    throw new Error(
      `VISUAL_BAR_BRAND=${JSON.stringify(raw)} is not a known scorecard brand. Known: northline.`,
    );
  }
  return raw;
}

function fixturesDir(brand) {
  if (brand) {
    return join(HERE, "fixtures", `visual-bar-${brand}`);
  }
  return join(HERE, "fixtures", "visual-bar");
}

function stillsDate(brand) {
  if (process.env.VISUAL_BAR_STILLS_DATE) {
    return process.env.VISUAL_BAR_STILLS_DATE;
  }
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const base = `${y}-${m}-${d}`;
  return brand ? `${base}-${brand}` : base;
}

function requireManifest(brand) {
  const dir = fixturesDir(brand);
  const manifestPath = join(dir, "manifest.json");
  if (!existsSync(manifestPath)) {
    const hint = brand
      ? `npm run visual-bar:fixtures:${brand}`
      : "npm run visual-bar:fixtures";
    throw new Error(`Missing ${manifestPath}. Run: ${hint}`);
  }
  return { dir, manifest: JSON.parse(readFileSync(manifestPath, "utf-8")) };
}

async function capture() {
  const brand = brandFromEnv();
  const { dir: fixtures, manifest } = requireManifest(brand);
  const date = stillsDate(brand);
  const outDir = join(ROOT, "docs", "audits", "_stills", date);
  mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const captured = [];

  try {
    for (const surface of manifest.surfaces) {
      for (const theme of THEMES) {
        const fixtureName = surface[theme];
        const fixturePath = join(fixtures, fixtureName);
        if (!existsSync(fixturePath)) {
          throw new Error(`Missing fixture ${fixturePath}`);
        }
        const url = pathToFileURL(fixturePath).href;

        for (const viewport of VIEWPORTS) {
          const context = await browser.newContext({
            viewport: { width: viewport.width, height: viewport.height },
            colorScheme: theme === "dark" ? "dark" : "light",
            deviceScaleFactor: 1,
          });
          const page = await context.newPage();
          await page.goto(url, { waitUntil: "networkidle" });
          // Let Alpine/theme attributes settle; fixtures are static HTML.
          await page.waitForTimeout(150);

          const stem = `${surface.id}-${theme}-${viewport.label}`;
          const pngPath = join(outDir, `${stem}.png`);
          await page.screenshot({
            path: pngPath,
            fullPage: true,
            animations: "disabled",
          });
          captured.push({
            surface: surface.id,
            label: surface.label,
            example: surface.example,
            theme,
            viewport: viewport.label,
            width: viewport.width,
            height: viewport.height,
            file: `${stem}.png`,
          });
          await context.close();
        }
      }
    }
  } finally {
    await browser.close();
  }

  const runManifest = {
    capturedAt: new Date().toISOString(),
    package: manifest.package,
    version: manifest.version,
    brand: brand || null,
    css: manifest.css,
    stillsDir: `docs/audits/_stills/${date}/`,
    viewports: VIEWPORTS,
    themes: THEMES,
    files: captured,
    note:
      "Private stills for the VISUAL-BAR scorecard. Gitignored. Do not ship.",
  };
  const runManifestPath = join(outDir, "manifest.json");
  writeFileSync(runManifestPath, JSON.stringify(runManifest, null, 2) + "\n");

  console.log(
    `visual-bar stills: ${captured.length} PNGs → ${outDir}` +
      (brand ? ` (brand=${brand})` : " (package-only)"),
  );
  console.log(`run manifest: ${runManifestPath}`);
}

capture().catch((err) => {
  console.error(err);
  process.exit(1);
});
