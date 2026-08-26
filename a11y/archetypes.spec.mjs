// The W0.3 archetype-test harness: sweeps every catalogue-manifest archetype
// (a11y/generate_archetype_fixtures.py, a11y/fixtures/archetypes/*.html) over
// the full W0.1 breakpoint matrix, in both themes, against the full gate set
// the plan requires (render succeeds, axe passes, no horizontal overflow at
// the smallest supported width, the two themes are visibly distinct, plus
// keyboard/no-JS/composited-contrast where the shape under test calls for
// them).
//
// Auto-discovery, twice over: fixtures are discovered by directory scan
// (readdirSync over a11y/fixtures/archetypes/), so a 17th archetype is swept
// with zero edits to this file the moment
// a11y/generate_archetype_fixtures.py has produced its fixtures, which itself
// requires zero edits (it reads the catalogue manifest). Width sources come
// from the SHIPPED tokens.css, parsed with the identical regex
// tests/test_archetype_harness.py uses on the Python side, never a literal
// array hand-copied from ADR-079's prose: a token rename or value change is
// picked up here on the next fixture regeneration, with no second edit.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";
import { measureComposedContrast } from "./composed-contrast.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(HERE);
const FIXTURES = join(HERE, "fixtures", "archetypes");
const TOKENS_CSS_PATH = join(ROOT, "src", "brickwork", "static", "brickwork", "dist", "tokens.css");
const CATALOGUE_MANIFEST_PATH = join(ROOT, "src", "brickwork", "static", "brickwork", "dist", "catalogue-manifest.json");

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

// --- Width source: --bw-breakpoint-sm/md/lg/xl on the shipped tokens.css ---
// (ADR-079 section 6, the authoritative supported-width matrix). Read live,
// exactly as tests/test_archetype_harness.py's _read_breakpoint_tokens()
// does on the Python side: one mechanism (parse the literal off :root),
// applied on both sides of the pytest/Playwright split, never a hardcoded
// width array on either side.
function readBreakpointTokens() {
  const css = readFileSync(TOKENS_CSS_PATH, "utf-8");
  const tokens = {};
  for (const match of css.matchAll(/--bw-breakpoint-(sm|md|lg|xl):\s*([0-9.]+)rem;/g)) {
    tokens[match[1]] = Number(match[2]);
  }
  const missing = ["sm", "md", "lg", "xl"].filter((name) => !(name in tokens));
  if (missing.length > 0) {
    throw new Error(
      `tokens.css is missing --bw-breakpoint-{${missing.join(",")}}; the archetype harness's width matrix ` +
        "cannot resolve. Rebuild the frontend (npm run build) or check ADR-079's token source.",
    );
  }
  return tokens;
}

// rem -> px at the browser default 16px root, matching the conversion
// ADR-079 section 6 itself states alongside every rem value.
const REM_TO_PX = 16;
const breakpointsRem = readBreakpointTokens();
const breakpointsPx = Object.fromEntries(Object.entries(breakpointsRem).map(([name, rem]) => [name, rem * REM_TO_PX]));

// The supported-width matrix ADR-079 section 6 names as what W0.3 consumes:
// one width below sm (representative of docs/POSITIONING.md's blocking
// mobile-overflow gate, which already covers 320/360/375/414px below sm in
// a11y/axe.spec.mjs's own MOBILE_WIDTHS), each of the four breakpoint
// values themselves, and one width comfortably above xl.
const WIDTHS = [
  { label: "below-sm", px: 375 },
  { label: "sm", px: breakpointsPx.sm },
  { label: "md", px: breakpointsPx.md },
  { label: "lg", px: breakpointsPx.lg },
  { label: "xl", px: breakpointsPx.xl },
  { label: "above-xl", px: breakpointsPx.xl + 160 },
];

const THEMES = ["light", "dark"];

// One entry per archetype: { slug, light: "<filename>", dark: "<filename>" }.
// Discovered from the fixture directory itself (not a name list maintained
// here), so a fixture the generator did not produce for both themes fails
// loudly below rather than silently sweeping only the theme that exists.
function discoverArchetypes() {
  const files = readdirSync(FIXTURES).filter((f) => f.endsWith(".html"));
  const slugs = new Map();
  for (const file of files) {
    const match = file.match(/^(.+)-(light|dark)\.html$/);
    if (!match) continue;
    const [, slug, theme] = match;
    if (!slugs.has(slug)) slugs.set(slug, {});
    slugs.get(slug)[theme] = file;
  }
  return [...slugs.entries()].map(([slug, byTheme]) => ({ slug, ...byTheme }));
}

const archetypes = discoverArchetypes();

// The catalogue manifest's own archetype count (src/brickwork/static/brickwork/
// dist/catalogue-manifest.json, a COMMITTED artefact, unlike the gitignored
// fixtures this spec scans): the independent expected count a fixture-count
// guard needs. Reading it directly, rather than trusting "more than zero"
// alone, is what catches a generator that silently drops archetypes (a
// filter bug, an early return) without dropping to exactly zero, which the
// discovery tests above cannot distinguish from "sixteen rendered
// correctly".
function expectedArchetypeCount() {
  const manifest = JSON.parse(readFileSync(CATALOGUE_MANIFEST_PATH, "utf-8"));
  const count = manifest.counts?.archetypes;
  if (typeof count !== "number") {
    throw new Error(`${CATALOGUE_MANIFEST_PATH} has no counts.archetypes; cannot size the fixture-count guard.`);
  }
  return count;
}

test.describe("archetype harness: discovery", () => {
  test("every discovered archetype has both a light and a dark fixture", () => {
    const incomplete = archetypes.filter((a) => !a.light || !a.dark);
    expect(incomplete, JSON.stringify(incomplete)).toEqual([]);
  });

  test("at least one archetype was discovered (the sweep below is not vacuous)", () => {
    expect(archetypes.length).toBeGreaterThan(0);
  });

  test("the fixture count matches the catalogue manifest's archetype count, both themes", () => {
    const expected = expectedArchetypeCount();
    expect(archetypes.length, `expected ${expected} archetypes (catalogue-manifest.json), found ${archetypes.length}`).toBe(
      expected,
    );
    for (const theme of THEMES) {
      const withTheme = archetypes.filter((a) => a[theme]).length;
      expect(withTheme, `expected ${expected} ${theme} fixtures, found ${withTheme}`).toBe(expected);
    }
  });
});

// --- Gate 1: render succeeds, at every width, in every theme -----------
// "Render succeeds" for a pre-rendered fixture means the browser can load
// and paint it without a page error; Playwright surfaces a load failure as a
// rejected goto() or a pageerror event, both asserted here.
for (const archetype of archetypes) {
  for (const theme of THEMES) {
    const file = archetype[theme];
    if (!file) continue; // reported by the discovery test above
    for (const width of WIDTHS) {
      test(`${archetype.slug} (${theme}) renders at ${width.label} (${width.px}px)`, async ({ page }) => {
        const errors = [];
        page.on("pageerror", (err) => errors.push(String(err)));
        await page.setViewportSize({ width: width.px, height: 900 });
        const response = await page.goto(pathToFileURL(join(FIXTURES, file)).href);
        expect(response?.ok() ?? true).toBeTruthy();
        await expect(page.locator("html")).toHaveCount(1);
        expect(errors, `page-level JS errors while rendering ${file} at ${width.px}px`).toEqual([]);
      });
    }
  }
}

// --- Gate 2: axe WCAG 2.2 AA, at every width, in every theme ------------
// Matches a11y/axe.spec.mjs's own tag set and animation-settling step, so an
// archetype is held to exactly the accessibility floor every other fixture
// in this repo is held to, not a narrower one.
for (const archetype of archetypes) {
  for (const theme of THEMES) {
    const file = archetype[theme];
    if (!file) continue;
    for (const width of WIDTHS) {
      test(`${archetype.slug} (${theme}) passes axe WCAG 2.2 AA at ${width.label} (${width.px}px)`, async ({
        page,
      }) => {
        await page.setViewportSize({ width: width.px, height: 900 });
        await page.goto(pathToFileURL(join(FIXTURES, file)).href);
        await page.evaluate(() =>
          Promise.all(
            document
              .getAnimations()
              .filter((a) => a.effect?.getTiming().iterations !== Infinity)
              .map((a) => a.finished),
          ),
        );
        const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
        expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
      });
    }
  }
}

// --- Gate 3: no horizontal overflow, at the smallest supported width -----
// Mirrors a11y/axe.spec.mjs's own MOBILE_WIDTHS sweep mechanism (root-cause
// offender reporting), scoped here to the narrowest width in this harness's
// own matrix (below-sm, 375px) per the plan's "no horizontal overflow at the
// smallest supported width" wording. The broader 320/360/375/414px sweep
// a11y/axe.spec.mjs already runs stays that file's job; this is the
// archetype-harness-scoped assertion of the same property.
const SMALLEST_WIDTH = WIDTHS[0];
for (const archetype of archetypes) {
  for (const theme of THEMES) {
    const file = archetype[theme];
    if (!file) continue;
    test(`${archetype.slug} (${theme}) has no horizontal overflow at ${SMALLEST_WIDTH.px}px`, async ({ page }) => {
      await page.setViewportSize({ width: SMALLEST_WIDTH.px, height: 900 });
      await page.goto(pathToFileURL(join(FIXTURES, file)).href);

      const result = await page.evaluate(() => ({
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        offenders: [...document.querySelectorAll("*")]
          .filter((el) => {
            const rect = el.getBoundingClientRect();
            if (rect.right <= window.innerWidth + 1) return false;
            const parent = el.parentElement?.getBoundingClientRect();
            return !parent || parent.right <= window.innerWidth + 1;
          })
          .slice(0, 5)
          .map((el) => `${el.tagName}.${typeof el.className === "string" ? el.className.split(" ")[0] : ""}`),
      }));

      expect(
        result.documentWidth,
        `${file} scrolls horizontally at ${SMALLEST_WIDTH.px}px; root causes: ${JSON.stringify(result.offenders)}`,
      ).toBeLessThanOrEqual(result.viewportWidth + 1);
    });
  }
}

// --- Gate 4: the two themes produce visibly distinct output --------------
// Complements tests/test_archetype_harness.py's source-level
// test_light_and_dark_renders_are_distinct (which proves data-theme reached
// the markup at all): this proves the browser-COMPUTED style genuinely
// differs, which is what "visibly distinct" means for a reader rather than
// for the HTML source. Compares the resolved --bw-color-surface/--bw-color-fg
// custom properties on <html>, the two tokens every themed page depends on
// (brickwork skill: "seven load-bearing tokens make a brand"), rather than a
// full-page screenshot diff, which would also fire on legitimate
// content-only differences.
for (const archetype of archetypes) {
  test(`${archetype.slug}: light and dark themes are visibly distinct`, async ({ page }) => {
    if (!archetype.light || !archetype.dark) test.skip();

    await page.goto(pathToFileURL(join(FIXTURES, archetype.light)).href);
    const lightColours = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement);
      return {
        surface: style.getPropertyValue("--bw-color-surface").trim(),
        fg: style.getPropertyValue("--bw-color-fg").trim(),
      };
    });

    await page.goto(pathToFileURL(join(FIXTURES, archetype.dark)).href);
    const darkColours = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement);
      return {
        surface: style.getPropertyValue("--bw-color-surface").trim(),
        fg: style.getPropertyValue("--bw-color-fg").trim(),
      };
    });

    expect(lightColours.surface, "light/dark --bw-color-surface resolved identically").not.toBe(darkColours.surface);
    expect(lightColours.fg, "light/dark --bw-color-fg resolved identically").not.toBe(darkColours.fg);
  });
}

// --- Gate 5: keyboard and no-JS floors, where an archetype's own header
// comment documents one, reusing the existing blocking suites' own
// mechanism rather than re-deriving it -----------------------------------
//
// Every archetype (base.html included: it carries the skip link and
// #bw-main directly rather than via a shell, but it does carry them, per
// build/review note on PR icvoss/django-brickwork#230) ships the skip-link
// and no-JS floor a11y/axe.spec.mjs's own "no-JS floor" describe block
// proves concretely against the hand-maintained list-*.html/dashboard-*.html
// fixtures; duplicating those per-widget assertions here for a fixture that
// composes the SAME shell and the SAME components would test the shell
// twice, never the archetype. What is archetype-specific, and what this
// harness DOES assert directly, is the one floor every archetype shares
// structurally: the skip link is the first tab stop and targets #bw-main
// (BR-BW-HTMX-001's no-JS floor, keyboard entry point), proved with
// JavaScript disabled so no scripting is required for it to hold. No
// per-archetype exemption exists here: an archetype that genuinely lacks a
// working skip link fails this gate by name, which is the point.
test.describe("no-JS floor: skip link", () => {
  test.use({ javaScriptEnabled: false });

  for (const archetype of archetypes) {
    for (const theme of THEMES) {
      const file = archetype[theme];
      if (!file) continue;
      test(`${archetype.slug} (${theme}): skip link is the first tab stop, JS disabled`, async ({ page }) => {
        await page.goto(pathToFileURL(join(FIXTURES, file)).href);
        await page.keyboard.press("Tab");
        const focused = await page.evaluate(() => ({
          tag: document.activeElement?.tagName,
          href: document.activeElement?.getAttribute("href"),
          classes: document.activeElement?.className,
        }));
        expect(focused.tag).toBe("A");
        expect(focused.href).toBe("#bw-main");
      });
    }
  }
});

// --- Gate 6: composited contrast, where an archetype composes a surface
// that needs it (dormant unless one does; auto-activates by construction) --
//
// WCAG 1.4.3 composited-contrast defects (text painted over a background
// image or gradient) are invisible to axe (it reports "incomplete", never a
// violation, for that shape: axe.spec.mjs's own comment on this). None of
// the 16 archetypes shipped today compose a media_placement="behind" hero or
// any other documented composited surface (verified: no archetype passes
// media_placement to _hero.html), so this gate has nothing to measure yet.
// It is wired here, scanning for the composited-surface marker class
// (.bw-hero--media-behind, the one shape ADR-057/#118 established this
// measurement for) on EVERY fixture rather than a named archetype list, so
// the day a marketing or product archetype adopts media_placement="behind"
// this gate measures it with no harness edit, the same auto-discovery
// principle applied to which GATES apply, not only which archetypes exist.

// measureComposedContrast now lives in ./composed-contrast.mjs, shared with
// axe.spec.mjs (icvoss/django-brickwork#239 contention audit: the two files
// carried near-identical copies).

for (const archetype of archetypes) {
  for (const theme of THEMES) {
    const file = archetype[theme];
    if (!file) continue;
    test(`${archetype.slug} (${theme}): any composited-surface text clears WCAG 1.4.3`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(pathToFileURL(join(FIXTURES, file)).href);

      const compositedHeroCount = await page.locator(".bw-hero--media-behind").count();
      if (compositedHeroCount === 0) {
        // No composited surface on this archetype today; nothing to measure.
        // Not skipped via test.skip() so this gate's absence is still
        // visible in the report as a real, passing assertion rather than a
        // silently-skipped test a future reviewer might mistake for "not
        // wired".
        return;
      }

      for (let i = 0; i < compositedHeroCount; i++) {
        const hero = page.locator(".bw-hero--media-behind").nth(i);
        for (const selector of [".bw-hero__heading", ".bw-hero__lede"]) {
          const el = hero.locator(selector);
          if ((await el.count()) === 0) continue;
          const { ratio } = await measureComposedContrast(page, el.first());
          const floor = selector === ".bw-hero__heading" ? 3.0 : 4.5;
          expect(
            ratio,
            `${file} ${selector} inside .bw-hero--media-behind[${i}] measured ${ratio.toFixed(2)}:1, below the WCAG 1.4.3 floor of ${floor}:1`,
          ).toBeGreaterThanOrEqual(floor);
        }
      }
    });
  }
}
