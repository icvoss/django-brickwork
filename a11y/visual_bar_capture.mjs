/**
 * Capture VISUAL-BAR scorecard stills (Phase 1.1 + Phase 4.3 brand leg + F.1).
 *
 * Loads fixtures from a11y/fixtures/visual-bar/ (package-only, comfortable),
 * a11y/fixtures/visual-bar-<brand>/ when VISUAL_BAR_BRAND is set, or
 * ...-compact / ...-<brand>-compact when VISUAL_BAR_DENSITY=compact.
 * Capture at light and dark, desktop ~1440px and phone ~375px. Writes PNGs
 * under docs/audits/_stills/<date>/ (package-only) or
 * docs/audits/_stills/<date>-<brand>/ (brand leg); appends -compact when
 * density is compact and VISUAL_BAR_STILLS_DATE is unset.
 *
 * Optional VISUAL_BAR_SURFACES=s1,s3,s5 filters which manifest surfaces to
 * capture (must already be present in the fixture manifest).
 *
 * Run:
 *   npm run visual-bar:fixtures
 *   npm run visual-bar:capture
 *
 * Brand packs (northline / harbour / folio skeletons):
 *   npm run visual-bar:fixtures:harbour
 *   npm run visual-bar:capture:harbour
 *
 * Density and surface filter (env; no separate npm scripts required):
 *   VISUAL_BAR_DENSITY=compact VISUAL_BAR_SURFACES=s1,s3,s5 \
 *     npm run visual-bar:fixtures:harbour
 *   VISUAL_BAR_DENSITY=compact VISUAL_BAR_STILLS_DATE=2026-09-13-beat-f1-harbour-compact \
 *     npm run visual-bar:capture:harbour
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
const KNOWN_BRANDS = new Set(["northline", "harbour", "folio"]);
const KNOWN_DENSITIES = new Set(["comfortable", "compact"]);

function brandFromEnv() {
  const raw = (process.env.VISUAL_BAR_BRAND || "").trim();
  if (!raw) {
    return "";
  }
  if (!KNOWN_BRANDS.has(raw)) {
    throw new Error(
      `VISUAL_BAR_BRAND=${JSON.stringify(raw)} is not a known scorecard brand. Known: ${[...KNOWN_BRANDS].sort().join(", ")}.`,
    );
  }
  return raw;
}

function densityFromEnv() {
  const raw = (process.env.VISUAL_BAR_DENSITY || "comfortable").trim() || "comfortable";
  if (!KNOWN_DENSITIES.has(raw)) {
    throw new Error(
      `VISUAL_BAR_DENSITY=${JSON.stringify(raw)} is not supported. Known: ${[...KNOWN_DENSITIES].sort().join(", ")}.`,
    );
  }
  return raw;
}

function surfacesFilterFromEnv() {
  const raw = (process.env.VISUAL_BAR_SURFACES || "").trim();
  if (!raw) {
    return null;
  }
  const requested = raw
    .split(",")
    .map((part) => part.trim().toLowerCase())
    .filter(Boolean);
  return requested.length ? requested : null;
}

function fixturesDir(brand, density) {
  const parts = ["visual-bar"];
  if (brand) {
    parts.push(brand);
  }
  if (density !== "comfortable") {
    parts.push(density);
  }
  return join(HERE, "fixtures", parts.join("-"));
}

function stillsDate(brand, density) {
  if (process.env.VISUAL_BAR_STILLS_DATE) {
    return process.env.VISUAL_BAR_STILLS_DATE;
  }
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const parts = [`${y}-${m}-${d}`];
  if (brand) {
    parts.push(brand);
  }
  if (density !== "comfortable") {
    parts.push(density);
  }
  return parts.join("-");
}

function requireManifest(brand, density) {
  const dir = fixturesDir(brand, density);
  const manifestPath = join(dir, "manifest.json");
  if (!existsSync(manifestPath)) {
    const hint = brand
      ? `VISUAL_BAR_BRAND=${brand} npm run visual-bar:fixtures:${brand}`
      : "npm run visual-bar:fixtures";
    throw new Error(`Missing ${manifestPath}. Run: ${hint}`);
  }
  return { dir, manifest: JSON.parse(readFileSync(manifestPath, "utf-8")) };
}

async function capture() {
  const brand = brandFromEnv();
  const density = densityFromEnv();
  const surfaceFilter = surfacesFilterFromEnv();
  const { dir: fixtures, manifest } = requireManifest(brand, density);
  const date = stillsDate(brand, density);
  const outDir = join(ROOT, "docs", "audits", "_stills", date);
  mkdirSync(outDir, { recursive: true });

  let surfaces = manifest.surfaces;
  if (surfaceFilter) {
    const known = new Set(surfaces.map((s) => s.id));
    const unknown = surfaceFilter.filter((id) => !known.has(id));
    if (unknown.length) {
      throw new Error(
        `VISUAL_BAR_SURFACES has IDs missing from fixture manifest: ${unknown.join(", ")}. Present: ${[...known].join(", ")}.`,
      );
    }
    const wanted = new Set(surfaceFilter);
    surfaces = surfaces.filter((s) => wanted.has(s.id));
  }

  const browser = await chromium.launch({ headless: true });
  const captured = [];

  try {
    for (const surface of surfaces) {
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
    density,
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
      (brand ? ` (brand=${brand}` : " (package-only") +
      `, density=${density})`,
  );
  console.log(`run manifest: ${runManifestPath}`);
}

capture().catch((err) => {
  console.error(err);
  process.exit(1);
});
