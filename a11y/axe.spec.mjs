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
    // the real, settled state is what WCAG governs. Only FINITE animations are
    // awaited: an infinitely-iterating Animation's .finished promise never
    // settles by spec, so waiting on it would hang forever. The skeleton
    // shimmer, the spinner, and the indeterminate progress sweep (all
    // `infinite`) are steady-state loops, not entrance transitions, so
    // analyzing while they run is correct: that IS their settled state.
    await pw.evaluate(() =>
      Promise.all(
        document
          .getAnimations()
          .filter((a) => a.effect?.getTiming().iterations !== Infinity)
          .map((a) => a.finished),
      ),
    );
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

    // BR-BW-MKT-002's no-JS render floor: every marketing page renders and
    // functions with neither Alpine nor htmx loaded. The marketing shell
    // needs no JS at all (BR-BW-HTMX-001), so this is mostly a structural
    // check: the shell chrome, the FAQ's native <details> accordion, and the
    // hero's single <h1> are all present with JavaScript disabled.
    test(`landing page renders the marketing shell with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `landing-${theme}.html`)).href);
      await expect(page.locator("#bw-main")).toBeVisible();
      await expect(page.locator("header.bw-marketing-header")).toBeVisible();
      await expect(page.locator("footer.bw-marketing-footer")).toBeVisible();
      // exactly one h1, in the hero
      await expect(page.locator("h1")).toHaveCount(1);
      // the nav and header actions are real anchors
      await expect(page.locator(".bw-marketing-header__nav a").first()).toBeVisible();
      await expect(page.locator(".bw-marketing-header__actions a").first()).toBeVisible();
    });

    // The nav renderers (#102/#82): both sibling renderers are real-anchor
    // renders over the same NavItem tree (no JS-only triggers), the compact
    // renderers light the active AREA, and the exact aria-current lives in
    // the contextual tier's ordinary bw_nav render.
    test(`nav renderers are real anchors with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `nav-renderers-${theme}.html`)).href);
      await expect(page.locator("a.bw-nav-header__link").first()).toBeVisible();
      await expect(page.locator("a.bw-nav-rail__link").first()).toBeVisible();
      // ancestor-active treatments on the compact renderers (child route active)
      await expect(page.locator(".bw-nav-header__link--active-ancestor")).toHaveCount(1);
      await expect(page.locator(".bw-nav-rail__link--active-ancestor")).toHaveCount(1);
      // exactly one exact-active marker, in the contextual tier
      await expect(page.locator('[aria-current="page"]')).toHaveCount(1);
      await expect(page.locator('.bw-nav-two-tier .bw-nav__link[aria-current="page"]')).toHaveCount(1);
      // the rail badge chip and the external affordance render server-side
      await expect(page.locator(".bw-nav-rail__badge")).toHaveText("2");
      await expect(page.locator(".bw-nav-header__external")).toHaveCount(1);
    });

    test(`pricing page's FAQ accordion works with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `pricing-${theme}.html`)).href);
      // the pricing table rendered its tiers server-side
      await expect(page.locator(".bw-pricing-tier")).toHaveCount(3);
      // the FAQ is native <details>/<summary> (BR-BW-MKT-004): clicking the
      // summary opens it with JS disabled, no scripting required
      const firstItem = page.locator("details.bw-disclosure").first();
      await expect(page.locator("details.bw-disclosure")).toHaveCount(3);
      await expect(firstItem).not.toHaveAttribute("open");
      await firstItem.locator("summary").click();
      await expect(firstItem).toHaveAttribute("open");
    });

    test(`about page renders its prose body with JS disabled (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `about-${theme}.html`)).href);
      await expect(page.locator("h1")).toHaveCount(1);
      await expect(page.locator(".bw-section-stack")).toContainText("Our story");
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

// The mobile-first floor for the example sections (3.1.0, plan Phase 6a gate 3).
//
// ADR-057 section 1: "a section that only works at desktop width is not a
// shipped section". axe does not measure this, and neither does a render test,
// so a section that scrolls the page sideways on a phone passes every other
// gate in this repo.
//
// It caught three real defects on the way in, all of which passed axe and the
// full pytest suite:
//   - .bw-hero__copy sized to its content instead of its container, because
//     .bw-hero sets align-items other than stretch.
//   - a <pre>'s <code> child painted outside its own scroll container.
//   - a one-word hero heading ("Documentation") at the fixed 60px display size
//     measured 406px and had no wrap opportunity.
//
// 320px is included (icvoss/django-brickwork#125 fixed it): the shipped
// marketing header used to overflow a 320px viewport by 6px (identical on
// landing-*.html, so it predated these sections). Widened here per the
// issue's own suggested follow-up once the header wraps instead of
// overflowing.
const MOBILE_WIDTHS = [320, 360, 375, 414];

for (const theme of THEMES) {
  for (const width of MOBILE_WIDTHS) {
    test(`sections do not scroll the page sideways at ${width}px (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(pathToFileURL(join(FIXTURES, `sections-${theme}.html`)).href);

      const result = await page.evaluate(() => ({
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        // Name the culprits, so a failure is actionable rather than a bare
        // number. Only elements whose parent is NOT itself overflowing are
        // reported: those are the root causes, not the cascade above them.
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
        `page scrolls horizontally at ${width}px; root causes: ${JSON.stringify(result.offenders)}`,
      ).toBeLessThanOrEqual(result.viewportWidth + 1);
    });
  }
}

// icvoss/django-brickwork#125 regression: the marketing header specifically,
// on the landing-*.html fixtures the issue itself reproduced against (326px
// scrollWidth at a 320px viewport, from .bw-marketing-header__actions and its
// bw_button both sitting at right edge 326). Asserted directly against the
// header element, not just the document, so a future regression here fails
// on this test rather than only on the broader sweep above.
for (const theme of THEMES) {
  test(`marketing header does not overflow a 320px viewport (${theme})`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 900 });
    await page.goto(pathToFileURL(join(FIXTURES, `landing-${theme}.html`)).href);

    const result = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      headerRight: document.querySelector(".bw-marketing-header")?.getBoundingClientRect().right ?? 0,
      actionsRight: document.querySelector(".bw-marketing-header__actions")?.getBoundingClientRect().right ?? 0,
    }));

    expect(result.documentWidth, "marketing header scrolls the page sideways at 320px").toBeLessThanOrEqual(
      result.viewportWidth + 1,
    );
    expect(result.headerRight, ".bw-marketing-header overflows the 320px viewport").toBeLessThanOrEqual(
      result.viewportWidth + 1,
    );
    expect(
      result.actionsRight,
      ".bw-marketing-header__actions overflows the 320px viewport",
    ).toBeLessThanOrEqual(result.viewportWidth + 1);
  });
}
