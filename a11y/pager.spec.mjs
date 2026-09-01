// Prev/next pager geometry (icvoss/django-brickwork#460): a presence-only
// assertion cannot see this defect. The bare-anchor workaround this replaces
// was semantically correct (real anchors, a labelled nav) and passed axe,
// the family boundary and the unstyled-class contract, and still rendered
// as one run-on line of inert grey text: two adjacent inline-flex anchors
// with nothing separating them, styled fg-muted/text-decoration:none by
// shell.css's own deliberate secondary-footer rule. This suite measures the
// rendered layout instead: real separation between the two links, a real
// underline (the "visibly a link" fix), and the single-link degradation
// actually landing at the correct inline edge rather than drifting to
// wherever a bare flex-start default would leave it.
//
// Against sections-<theme>.html (a11y/generate_fixtures.py), which stacks
// every example section including sections/content/pager.html: three
// pagers, two-link then next-only then previous-only, in that order, which
// is exactly the shape needed to prove the single-link degradation is a
// real, distinct rule rather than an artefact of always having a sibling
// present.

import { test, expect } from "@playwright/test";
import { pathToFileURL } from "node:url";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");

const THEMES = ["light", "dark"];

function fixture(theme) {
  return pathToFileURL(join(FIXTURES, `sections-${theme}.html`)).href;
}

// sections/content/pager.html renders three <nav class="bw-pager">
// landmarks in source order: two-link, next-only (first page), previous-only
// (last page). Selecting by position rather than aria-label keeps this
// suite decoupled from the example's own copy.
async function pagerMetrics(page) {
  return page.evaluate(() => {
    const pagers = Array.from(document.querySelectorAll("nav.bw-pager"));
    if (pagers.length < 3) return { count: pagers.length };

    const describe = (pager) => {
      const links = Array.from(pager.querySelectorAll(".bw-pager__link"));
      const pagerRect = pager.getBoundingClientRect();
      return {
        linkCount: links.length,
        rects: links.map((a) => a.getBoundingClientRect()),
        underlines: links.map((a) => getComputedStyle(a).textDecorationLine),
        pagerRight: pagerRect.right,
        pagerLeft: pagerRect.left,
      };
    };

    return {
      count: pagers.length,
      twoLink: describe(pagers[0]),
      nextOnly: describe(pagers[1]),
      previousOnly: describe(pagers[2]),
    };
  });
}

for (const theme of THEMES) {
  test.describe(`bw-pager (${theme})`, () => {
    test(`the fixture carries all three example pagers (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(fixture(theme));
      const m = await pagerMetrics(page);
      // Guards every assertion below from passing vacuously against a
      // fixture that lost the example, per the sibling suite's own pattern
      // (prose_rhythm.spec.mjs's "is missing the ... example" guard).
      expect(m.count, "sections fixture is missing one or more sections/content/pager.html pagers").toBeGreaterThanOrEqual(3);
    });

    test(`the two-link pager separates its links and underlines them (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(fixture(theme));
      const m = await pagerMetrics(page);
      expect(m.count).toBeGreaterThanOrEqual(3);

      const { rects, underlines, linkCount } = m.twoLink;
      expect(linkCount, "the two-link pager should render exactly two links").toBe(2);

      // The defect: two adjacent inline-flex anchors with nothing between
      // them ran together as one line. A real gap between the previous and
      // next link's boxes is the fix.
      const [previous, next] = rects;
      const horizontalGap = next.left - previous.right;
      const verticalGap = next.top - previous.bottom;
      expect(
        Math.max(horizontalGap, verticalGap),
        `previous and next links have no separating gap at 1280px (${theme}): horizontal ${horizontalGap}, vertical ${verticalGap}`,
      ).toBeGreaterThan(0);

      // "Visibly a link": underline, not colour alone (WCAG 1.4.1), the
      // same principle .bw-prose :where(a) applies, at the muted footer
      // tier rather than the accent one.
      for (const decoration of underlines) {
        expect(decoration, `pager link is not underlined (${theme}): ${decoration}`).toContain("underline");
      }
    });

    test(`a lone "next" link sits at the inline end, not the start (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(fixture(theme));
      const m = await pagerMetrics(page);
      expect(m.count).toBeGreaterThanOrEqual(3);

      const { rects, linkCount, pagerRight } = m.nextOnly;
      expect(linkCount, "the next-only pager should render exactly one link").toBe(1);

      // The single-link degradation this issue asks for: the first page of
      // a sequence still reads "next" at the trailing edge, not pinned to
      // wherever a bare flex-start default would leave a solitary child.
      const [next] = rects;
      const gapFromEnd = pagerRight - next.right;
      expect(gapFromEnd, `a lone "next" link should sit flush with the pager's inline end (${theme})`).toBeLessThan(1);
    });

    test(`a lone "previous" link sits at the inline start, not the end (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(fixture(theme));
      const m = await pagerMetrics(page);
      expect(m.count).toBeGreaterThanOrEqual(3);

      const { rects, linkCount, pagerLeft } = m.previousOnly;
      expect(linkCount, "the previous-only pager should render exactly one link").toBe(1);

      const [previous] = rects;
      const gapFromStart = previous.left - pagerLeft;
      expect(gapFromStart, `a lone "previous" link should sit flush with the pager's inline start (${theme})`).toBeLessThan(1);
    });

    test(`the pair collapses to a stacked column at a narrow width (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width: 360, height: 900 });
      await page.goto(fixture(theme));
      const m = await pagerMetrics(page);
      expect(m.count).toBeGreaterThanOrEqual(3);

      const { rects, linkCount } = m.twoLink;
      expect(linkCount).toBe(2);

      // "Stacked at narrow viewports": the two links no longer share a row,
      // proven by the second sitting below the first rather than beside it.
      const [previous, next] = rects;
      expect(
        next.top,
        `the two-link pager did not stack at 360px (${theme}): next.top=${next.top}, previous.bottom=${previous.bottom}`,
      ).toBeGreaterThanOrEqual(previous.bottom);
    });

    test(`direction is stated in the link's own visible text, not the icon alone (${theme})`, async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.goto(fixture(theme));
      const texts = await page.evaluate(() =>
        Array.from(document.querySelectorAll("nav.bw-pager .bw-pager__link")).map((a) => a.textContent.trim()),
      );
      expect(texts.length, "no pager links found to check text against").toBeGreaterThan(0);
      for (const text of texts) {
        // WCAG 2.4.4: the link's purpose must survive being read out of
        // context. "Previous: <title>" / "Next: <title>" is what
        // _pager.html renders (a literal colon, not CSS generated content,
        // so it survives into textContent); a decorative-only icon would
        // fail this.
        expect(/^(Previous|Next):\s*\S/.test(text), `pager link text does not state its direction (${theme}): "${text}"`).toBe(
          true,
        );
      }
    });
  });
}
