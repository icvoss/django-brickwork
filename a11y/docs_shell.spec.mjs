// Docs shell rail geometry (icvoss/django-brickwork#451).
//
// WHY THIS SUITE EXISTS, and why nothing already here caught the defect it
// guards. shell/docs.html's rail is a <details> disclosure below the layout
// breakpoint and a permanent rail above it, and above it the summary is
// hidden because there is nothing left to disclose. Through 3.15.0 the rule
// meant to reveal the rail's content targeted .bw-docs-layout__nav-body, a
// CHILD of the <details>. A closed <details> collapses its content on the
// ::details-content pseudo-element that wraps it, so a display rule on
// something inside that wrapper never gets the chance to apply. The shell
// sets no [open], so a desktop docs page reserved a 16rem grid track and
// rendered a 0px rail inside it, with every link present in the DOM and no
// control anywhere on the page to open one.
//
// Every existing gate passed while that shipped, which is the point:
//   - the template and markup tests pass, because the MARKUP is correct;
//     the nav and its links render on every page.
//   - axe passes, because links that are still in the accessibility tree
//     are not a WCAG violation. A zero-height container is a layout fact,
//     and axe does not measure layout.
//   - the mobile-overflow checks pass, because nothing overflows.
// It was found by a person looking at a rendered page, the second docs-shell
// defect found that way (cf. icvoss/django-brickwork#389). Only a rendered
// geometry assertion closes that gap, so this suite asserts SIZE and
// POSITION rather than presence.
//
// The assertions are deliberately about the rail being USABLE, not about
// any particular CSS mechanism delivering it: a future change that reveals
// the rail some other way should keep this suite green, and any change that
// leaves a desktop reader with no navigation should fail it.

import { test, expect } from "@playwright/test";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");

const THEMES = ["light", "dark"];

// Both sides of --bw-breakpoint-lg (64rem = 1024px at the default root font
// size). 1024 is the boundary itself and is included deliberately: an
// off-by-one in the media query is exactly the kind of regression a pair of
// comfortably-inside widths would miss.
const DESKTOP_WIDTHS = [1024, 1280, 1440];
const NARROW_WIDTHS = [375, 768];

const RAIL = ".bw-docs-layout__nav";
const RAIL_SUMMARY = ".bw-docs-layout__nav-summary";
const RAIL_LINK = ".bw-docs-layout__nav-body a";

function fixture(theme) {
  return pathToFileURL(join(FIXTURES, `docs-${theme}.html`)).href;
}

// The fixture is served with the rail's <details> in its default state,
// which is CLOSED: the shell sets no [open] and this suite must never add
// one, because "closed by default" is the exact precondition the defect
// needed. A fixture stamped [open] would pass against the broken CSS.
async function railMetrics(page) {
  return page.evaluate(
    ([railSel, summarySel, linkSel]) => {
      const rail = document.querySelector(railSel);
      const summary = document.querySelector(summarySel);
      const link = document.querySelector(linkSel);
      const article = document.querySelector("article");
      if (!rail || !summary || !link || !article) {
        return { missing: { rail: !rail, summary: !summary, link: !link, article: !article } };
      }
      const railRect = rail.getBoundingClientRect();
      const linkRect = link.getBoundingClientRect();
      return {
        missing: null,
        railOpen: rail.hasAttribute("open"),
        railHeight: railRect.height,
        summaryDisplay: getComputedStyle(summary).display,
        summaryHeight: summary.getBoundingClientRect().height,
        linkHeight: linkRect.height,
        linkInlineStart: linkRect.x,
        articleInlineStart: article.getBoundingClientRect().x,
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
      };
    },
    [RAIL, RAIL_SUMMARY, RAIL_LINK],
  );
}

for (const theme of THEMES) {
  for (const width of DESKTOP_WIDTHS) {
    test(`docs rail is visible at ${width}px (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(fixture(theme));
      const m = await railMetrics(page);

      expect(m.missing, `fixture docs-${theme}.html is missing an element this suite measures`).toBeNull();

      // The precondition. If a future fixture ships the rail [open], every
      // assertion below would pass against the broken CSS too, so the suite
      // states out loud that it is measuring the closed default.
      expect(m.railOpen, "the docs fixture must keep the rail closed by default: an [open] rail cannot fail this suite").toBe(
        false,
      );

      // The defect itself: the rail measured 0px here, with its summary
      // hidden and no way to open it.
      expect(m.railHeight, `the docs rail has no height at ${width}px, so a reader gets no navigation`).toBeGreaterThan(0);
      expect(m.linkHeight, `the docs rail's links have no height at ${width}px`).toBeGreaterThan(0);

      // The rail is a permanent one at this breakpoint, so the disclosure
      // control is correctly hidden. Asserted so that "reveal the summary
      // again" is a deliberate change rather than a silent way to pass.
      expect(m.summaryDisplay, `the docs rail's summary should be hidden at ${width}px`).toBe("none");

      // order: -1 restores the rail to the visual inline start even though
      // the article is emitted first in source order (ADR-091 decision 3).
      expect(
        m.linkInlineStart,
        `the docs rail should sit at the inline start, before the article, at ${width}px`,
      ).toBeLessThan(m.articleInlineStart);

      expect(m.documentWidth, `the docs page scrolls horizontally at ${width}px`).toBeLessThanOrEqual(m.viewportWidth + 1);
    });
  }

  for (const width of NARROW_WIDTHS) {
    test(`docs rail collapses to an openable disclosure at ${width}px (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(fixture(theme));
      const m = await railMetrics(page);

      expect(m.missing, `fixture docs-${theme}.html is missing an element this suite measures`).toBeNull();

      // Below the breakpoint the disclosure is the whole point: the summary
      // must be visible and must be a real tap target, because here it is
      // the only way to reach the navigation.
      expect(m.summaryDisplay, `the docs rail's summary must be visible at ${width}px`).not.toBe("none");
      expect(m.summaryHeight, `the docs rail's summary must meet the 44px minimum tap target at ${width}px`).toBeGreaterThanOrEqual(
        44,
      );

      expect(m.documentWidth, `the docs page scrolls horizontally at ${width}px`).toBeLessThanOrEqual(m.viewportWidth + 1);
    });
  }

  // The no-JS floor: <details> toggling is native, so the rail must open on
  // a plain click with no JavaScript running at all.
  test.describe("no-JS floor", () => {
    test.use({ javaScriptEnabled: false });

    test(`docs rail opens with no JavaScript at 375px (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 900 });
      await page.goto(fixture(theme));

      const rail = page.locator(RAIL);
      await expect(rail).not.toHaveAttribute("open", /.*/);

      await page.locator(RAIL_SUMMARY).click();

      // The native element's own state, which is what a no-JS reader gets.
      await expect(rail).toHaveAttribute("open", /.*/);
      const height = await rail.evaluate((el) => el.getBoundingClientRect().height);
      expect(height, "the docs rail should expand when its summary is clicked with no JavaScript").toBeGreaterThan(44);
    });
  });
}
