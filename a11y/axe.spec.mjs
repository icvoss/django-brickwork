// axe-core accessibility gate (WCAG 2.2 AA) + the no-JS floor assertion.
//
// Runs against the pre-rendered fixtures (a11y/generate_fixtures.py renders the
// REAL testapp pages through the full shell in light + dark). This is the
// load-bearing differentiator: 0/22 competitor admin templates ship a tested
// a11y guarantee. axe finds ~57% of issues, so this pairs with the keyboard +
// no-JS checks below; manual AT review remains a release-gate step on top.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readdirSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const pages = readdirSync(FIXTURES).filter((f) => f.endsWith(".html"));

// WCAG 2.2 AA tag set. axe maps these to the rule subset that gates the build.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

for (const page of pages) {
  test(`axe WCAG 2.2 AA: ${page}`, async ({ page: pw }) => {
    await pw.goto(pathToFileURL(join(FIXTURES, page)).href);
    // Settle CSS entrance animations (e.g. the account-menu panel's
    // bw-fade-in-up, 200ms, which plays on load whenever a fixture renders
    // the disclosure already open) before analyzing. Evaluating mid-animation
    // samples transient opacity/position, which axe correctly, but
    // misleadingly, reports as a steady-state contrast/target-size defect;
    // the real, settled state is what WCAG governs.
    await pw.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)));
    const results = await new AxeBuilder({ page: pw }).withTags(WCAG_TAGS).analyze();
    // Fail with the concrete violations so a regression is actionable.
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

// Both theme variants get the behavioural floor, not just light: a dark-only
// regression (a hidden control, a broken disclosure) must fail the gate too.
const THEMES = ["light", "dark"];

// The no-JS floor (BR-BW-HTMX-001): with JavaScript disabled, the shell must
// still render a complete, navigable document, the skip link and nav links must
// be real anchors, and the native <details> disclosures must work.
test.describe("no-JS floor", () => {
  test.use({ javaScriptEnabled: false });

  for (const theme of THEMES) {
    test(`shell renders and is navigable with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `list-${theme}.html`)).href);
      // skip link is a real anchor to the main region
      const skip = page.locator("a.bw-skip-link");
      await expect(skip).toHaveAttribute("href", "#bw-main");
      await expect(page.locator("#bw-main")).toBeVisible();
      // nav links are real anchors (not JS-only widgets)
      await expect(page.locator("a.bw-nav__link").first()).toBeVisible();
      // the mobile drawer is a native <details> (works with no JS)
      await expect(page.locator("details.bw-drawer")).toHaveCount(1);
      // the records data table rendered rows server-side (scoped to its wrap:
      // the page also carries the definition-variant facts table)
      await expect(page.locator("#widgets-table table.bw-data-table tbody tr")).toHaveCount(2);
      // breadcrumbs render server-side with the current page marked
      await expect(page.locator("ol.bw-breadcrumbs__list li").first()).toBeVisible();
      await expect(page.locator('.bw-breadcrumbs__current[aria-current="page"]')).toBeVisible();
      // the account menu is a native <details>: clicking the summary opens it
      // with JS disabled (disclosure behaviour is HTML, not scripting)
      const menu = page.locator("details.bw-account-menu");
      await expect(menu).toHaveCount(1);
      await expect(page.locator("nav.bw-account-menu__panel")).toBeHidden();
      await page.locator("summary.bw-account-menu__trigger").click();
      await expect(menu).toHaveAttribute("open");
      await expect(page.locator("nav.bw-account-menu__panel")).toBeVisible();
      // the consumer's own property switcher in the nav slot (#21, AC-BW-078)
      // is a native <details> too: it opens with JS disabled
      const switcher = page.locator("aside.bw-sidebar details.bw-sidebar__switcher-trigger");
      await expect(switcher).toHaveCount(1);
      await switcher.locator("summary").click();
      await expect(switcher).toHaveAttribute("open");
      // the filter bar is a plain GET form (TBL-003 no-JS floor)
      await expect(page.locator("form.bw-filter-bar")).toHaveAttribute("method", "get");
    });

    test(`dashboard pattern renders server-side with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `dashboard-${theme}.html`)).href);
      // three stat tiles, rendered entirely server-side
      await expect(page.locator(".bw-stat")).toHaveCount(3);
      // a delta's directional meaning is glyph + text, never colour alone
      // (BR-BW-TPL-007): the trend text labels are present in the DOM
      await expect(page.getByText("One more than last week")).toHaveCount(1);
      // the recent-activity table rendered its rows server-side
      await expect(page.locator("#activity-table table.bw-data-table tbody tr")).toHaveCount(2);
    });

    test(`form errors are present and wired with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `form-errors-${theme}.html`)).href);
      const input = page.locator('input[aria-invalid="true"]').first();
      await expect(input).toHaveCount(1);
      const describedBy = await input.getAttribute("aria-describedby");
      expect(describedBy).toBeTruthy();
      // the referenced error container exists and carries the message
      const errorId = describedBy.split(" ").find((id) => id.endsWith("_errors"));
      await expect(page.locator(`#${errorId}`)).toContainText("not allowed");
      // the drawn checkbox (bw-checkbox) is present and natively toggleable:
      // a real <input type="checkbox"> changes state without any scripting
      const checkbox = page.locator('input[type="checkbox"].bw-checkbox');
      await expect(checkbox).toHaveCount(1);
      await expect(checkbox).not.toBeChecked();
      await checkbox.check();
      await expect(checkbox).toBeChecked();
    });
  }
});

// Keyboard: the skip link is the first focusable element and targets main.
for (const theme of THEMES) {
  test(`skip link is the first tab stop (${theme})`, async ({ page }) => {
    await page.goto(pathToFileURL(join(FIXTURES, `list-${theme}.html`)).href);
    await page.keyboard.press("Tab");
    const focusedHref = await page.evaluate(() => document.activeElement?.getAttribute("href"));
    expect(focusedHref).toBe("#bw-main");
  });
}
