// ADR-095's emitted-project gate. The fixtures are rendered through the
// starter's own settings, URLs and views by generate_startsite_fixtures.py,
// then loaded here as self-contained documents. This is intentionally a
// separate Playwright invocation so its reporter statistics can prove this
// specific gate ran, rather than borrowing a non-zero count from the larger
// package-wide a11y suite.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readdirSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures", "startsite");
const expectedFixtures = [
  "landing-light.html",
  "landing-dark.html",
  "dashboard-light.html",
  "dashboard-dark.html",
  "docs-home-light.html",
  "docs-home-dark.html",
];
const fixtures = readdirSync(FIXTURES).filter((file) => file.endsWith(".html")).sort();
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

test("emitted startsite fixtures cover every page in both themes", () => {
  expect(fixtures).toEqual(expectedFixtures.sort());
});

for (const fixture of fixtures) {
  test(`emitted startsite ${fixture} passes axe WCAG 2.2 AA`, async ({ page }) => {
    await page.goto(pathToFileURL(join(FIXTURES, fixture)).href);
    await page.evaluate(() =>
      Promise.all(
        document
          .getAnimations()
          .filter((animation) => animation.effect?.getTiming().iterations !== Infinity)
          .map((animation) => animation.finished),
      ),
    );
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}
