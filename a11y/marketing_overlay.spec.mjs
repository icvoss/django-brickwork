// Marketing header overlay PE (ADR-105, icvoss/django-brickwork#565).
//
// Against marketing-overlay-js-<theme>.html fixtures, which inline
// marketing-overlay.js. Asserts data-bw-overlay-ready, scroll and panel
// context attributes. Contrast of stamped states is covered by axe.spec.mjs.

import { test, expect } from "@playwright/test";
import { pathToFileURL } from "node:url";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");

for (const theme of ["light", "dark"]) {
  test(`overlay PE boots and follows scroll/context (${theme})`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto(
      pathToFileURL(join(FIXTURES, `marketing-overlay-js-${theme}.html`)).href,
    );

    const header = page.locator(".bw-marketing-header--overlay");
    await expect(header).toHaveAttribute("data-bw-overlay-ready", "");
    await expect(header).toHaveAttribute("data-bw-scrolled", "false");
    await expect(header).toHaveAttribute("data-bw-nav-context", "dark");

    await page.evaluate(() => {
      const light = document.querySelector(
        '.bw-marketing__content [data-bw-nav-context="light"]',
      );
      if (!light) return;
      const top = light.getBoundingClientRect().top + window.scrollY;
      window.scrollTo(0, Math.max(0, top - 40));
    });
    await expect(header).toHaveAttribute("data-bw-scrolled", "true");
    await expect(header).toHaveAttribute("data-bw-nav-context", "light");

    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(header).toHaveAttribute("data-bw-scrolled", "false");
    await expect(header).toHaveAttribute("data-bw-nav-context", "dark");
  });
}
