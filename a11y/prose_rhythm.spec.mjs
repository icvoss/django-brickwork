// Prose rhythm regression (icvoss/django-brickwork#461): every per-element
// reset inside .bw-prose used to zero margin with the `margin` shorthand,
// which also zeroed margin-block-start. Every reset is a :where() selector
// (zero specificity) at the same (0,1,0) specificity as the flow rule
// `.bw-prose > * + * { margin-block-start: var(--bw-space-5) }`
// (frontend/src/components.css:4091), and every reset is authored AFTER it,
// so the resets always won the tie and the rhythm collapsed to a 0px gap for
// any adjacent pair the heading-specific rules did not separately override.
// A presence-only assertion (the element exists, axe is clean) cannot see
// this: the DOM and the accessibility tree are correct either way, only the
// rendered gap changes. This suite asserts the actual gap in a real browser.
//
// Against sections-<theme>.html (a11y/generate_fixtures.py), which stacks
// every example section including sections/content/prose-block.html: real
// long-form content with h2/p/h3/ol/blockquote/pre/table/hr, all in one
// document, which is exactly the shape the defect needs to reproduce (a
// single p->p pair proves nothing about ol, blockquote or pre, which the
// original issue report understated).

import { test, expect } from "@playwright/test";
import { pathToFileURL } from "node:url";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");

const THEMES = ["light", "dark"];

// rem -> px at the browser default 16px root, matching --bw-space-* values
// (src/brickwork/static/brickwork/dist/tokens.css).
const SPACE_2 = 8; // --bw-space-2: 0.5rem (li + li, nested list)
const SPACE_3 = 12; // --bw-space-3: 0.75rem (heading's trailing space)
const SPACE_5 = 20; // --bw-space-5: 1.25rem (the flow rule's base rhythm)
const SPACE_10 = 40; // --bw-space-10: 2.5rem (heading's leading space, and hr)

// Locate the long-form prose-block example specifically: sections-<theme>.html
// stacks every example section, and several others (callouts) also carry a
// .bw-prose class on a much shorter fragment. section.bw-content-section is
// the wrapper sections/content/prose-block.html itself renders, and is
// unique in the stacked fixture.
async function proseGaps(page) {
  return page.evaluate(() => {
    const prose = document.querySelector("section.bw-content-section .bw-prose");
    if (!prose) return null;
    const children = Array.from(prose.children);
    const gaps = [];
    for (let i = 1; i < children.length; i++) {
      const prevRect = children[i - 1].getBoundingClientRect();
      const nextRect = children[i].getBoundingClientRect();
      gaps.push({
        prev: children[i - 1].tagName.toLowerCase(),
        next: children[i].tagName.toLowerCase(),
        gap: Math.round((nextRect.top - prevRect.bottom) * 100) / 100,
      });
    }
    return gaps;
  });
}

for (const theme of THEMES) {
  test.describe(`bw-prose vertical rhythm (${theme})`, () => {
    test(`adjacent flow siblings keep a non-zero gap, not just axe-clean markup (${theme})`, async ({
      page,
    }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `sections-${theme}.html`)).href);
      const gaps = await proseGaps(page);
      expect(gaps, `fixture sections-${theme}.html is missing the prose-block example this suite measures`).not.toBeNull();

      // Every adjacency in the stacked example must clear rest-state 0: a
      // reset winning the cascade collapses ALL of these to 0, not just one,
      // which is why the assertion sweeps the whole list rather than picking
      // a single pair.
      for (const { prev, next, gap } of gaps) {
        expect(gap, `${prev} -> ${next} collapsed to ${gap}px`).toBeGreaterThan(0);
      }
    });

    test(`heading rhythm is asymmetric and pinned to its token values (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `sections-${theme}.html`)).href);
      const gaps = await proseGaps(page);

      // A heading belongs to what follows it (frontend/src/components.css
      // :4102-4103): 40px leading, 12px trailing. Pinned to exact token
      // values, not just "greater than zero", so a future change cannot
      // silently flatten the asymmetry while still passing the non-zero
      // sweep above.
      const intoHeading = gaps.filter((g) => g.next === "h3");
      const outOfHeading = gaps.filter((g) => g.prev === "h3");
      expect(intoHeading.length, "fixture has no *->h3 pair to measure").toBeGreaterThan(0);
      expect(outOfHeading.length, "fixture has no h3->* pair to measure").toBeGreaterThan(0);
      for (const { gap } of intoHeading) expect(gap).toBe(SPACE_10);
      for (const { gap } of outOfHeading) expect(gap).toBe(SPACE_3);
    });

    test(`plain paragraph and list/blockquote adjacency use the base rhythm (${theme})`, async ({
      page,
    }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `sections-${theme}.html`)).href);
      const gaps = await proseGaps(page);

      const pToP = gaps.find((g) => g.prev === "p" && g.next === "p");
      const olToBlockquote = gaps.find((g) => g.prev === "ol" && g.next === "blockquote");
      const tableToP = gaps.find((g) => g.prev === "div" && g.next === "p");

      expect(pToP, "fixture has no p->p pair to measure").toBeTruthy();
      expect(olToBlockquote, "fixture has no ol->blockquote pair to measure").toBeTruthy();
      expect(tableToP, "fixture has no table-wrap->p pair to measure").toBeTruthy();

      expect(pToP.gap).toBe(SPACE_5);
      expect(olToBlockquote.gap).toBe(SPACE_5);
      expect(tableToP.gap).toBe(SPACE_5);
    });

    test(`hr keeps its own explicit 40px margin on both sides (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `sections-${theme}.html`)).href);
      const gaps = await proseGaps(page);

      const intoHr = gaps.find((g) => g.next === "hr");
      const outOfHr = gaps.find((g) => g.prev === "hr");
      expect(intoHr, "fixture has no *->hr pair to measure").toBeTruthy();
      expect(outOfHr, "fixture has no hr->* pair to measure").toBeTruthy();
      expect(intoHr.gap).toBe(SPACE_10);
      expect(outOfHr.gap).toBe(SPACE_10);
    });

    test(`the prose block's first child has no leading outer space (${theme})`, async ({ page }) => {
      await page.goto(pathToFileURL(join(FIXTURES, `sections-${theme}.html`)).href);
      const noLeadingSpace = await page.evaluate(() => {
        const prose = document.querySelector("section.bw-content-section .bw-prose");
        const first = prose.firstElementChild;
        const parentRect = prose.getBoundingClientRect();
        const firstRect = first.getBoundingClientRect();
        return Math.round((firstRect.top - parentRect.top) * 100) / 100;
      });
      // The reset that used to supply this (margin: 0 on every element) is
      // gone; .bw-prose > :first-child now does it explicitly instead.
      expect(noLeadingSpace).toBe(0);
    });
  });
}
