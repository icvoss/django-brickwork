/**
 * Capture VISUAL-BAR scorecard stills (Phase 1.1).
 *
 * Loads package-only fixtures from a11y/fixtures/visual-bar/ (generate first)
 * at light and dark, desktop ~1440px and phone ~375px, and writes PNGs under
 * docs/audits/_stills/<date>/ (gitignored). Not a CI gate: local audit tool.
 *
 * Run:
 *   npm run visual-bar:fixtures
 *   npm run visual-bar:capture
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
const FIXTURES = join(HERE, "fixtures", "visual-bar");
const MANIFEST_PATH = join(FIXTURES, "manifest.json");

const VIEWPORTS = [
  { label: "1440", width: 1440, height: 900 },
  { label: "375", width: 375, height: 812 },
];
const THEMES = ["light", "dark"];

function stillsDate() {
  if (process.env.VISUAL_BAR_STILLS_DATE) {
    return process.env.VISUAL_BAR_STILLS_DATE;
  }
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function requireManifest() {
  if (!existsSync(MANIFEST_PATH)) {
    throw new Error(
      `Missing ${MANIFEST_PATH}. Run: npm run visual-bar:fixtures`,
    );
  }
  return JSON.parse(readFileSync(MANIFEST_PATH, "utf-8"));
}

async function capture() {
  const manifest = requireManifest();
  const date = stillsDate();
  const outDir = join(ROOT, "docs", "audits", "_stills", date);
  mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const captured = [];

  try {
    for (const surface of manifest.surfaces) {
      for (const theme of THEMES) {
        const fixtureName = surface[theme];
        const fixturePath = join(FIXTURES, fixtureName);
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
    `visual-bar stills: ${captured.length} PNGs → ${outDir}`,
  );
  console.log(`run manifest: ${runManifestPath}`);
}

capture().catch((err) => {
  console.error(err);
  process.exit(1);
});
