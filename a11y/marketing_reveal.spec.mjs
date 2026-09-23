// Section reveal motion under reduced motion (BR-BW-MKT-009, MOT-003).
//
// Against marketing-reveal-<theme>.html fixtures. The no-JS, no-preference
// export IS the resting state (no boot required: this is CSS only), so this
// spec only needs to prove the prefers-reduced-motion: reduce floor actually
// suppresses movement on the compiled stylesheet, which axe.spec.mjs and the
// no-JS suite do not check (they run without emulating reduced motion).

import { test, expect } from "@playwright/test";
import { pathToFileURL } from "node:url";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");

test.describe("section reveal, reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  // The reducedMotion context option alone does not reliably reach a
  // file:// document's matchMedia/CSS evaluation in this Chromium build; an
  // explicit emulateMedia call is needed (the interactions.spec.mjs note).
  test.beforeEach(async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
  });

  for (const theme of ["light", "dark"]) {
    test(`.bw-section--reveal-enter has no animation under reduced motion (${theme})`, async ({
      page,
    }) => {
      await page.goto(
        pathToFileURL(join(FIXTURES, `marketing-reveal-${theme}.html`)).href,
      );

      const band = page.locator(".bw-section--reveal-enter");
      await expect(band).toBeVisible();

      const style = await band.evaluate((el) => {
        const computed = getComputedStyle(el);
        return {
          animationName: computed.animationName,
          transform: computed.transform,
        };
      });
      expect(style.animationName).toBe("none");
      expect(["none", "matrix(1, 0, 0, 1, 0, 0)"]).toContain(style.transform);
    });
  }
});

test.describe("section reveal, no preference", () => {
  for (const theme of ["light", "dark"]) {
    test(`.bw-section--reveal-enter carries the enter animation without reduced motion (${theme})`, async ({
      page,
    }) => {
      await page.emulateMedia({ reducedMotion: "no-preference" });
      await page.goto(
        pathToFileURL(join(FIXTURES, `marketing-reveal-${theme}.html`)).href,
      );

      const band = page.locator(".bw-section--reveal-enter");
      await expect(band).toBeVisible();

      const animationName = await band.evaluate(
        (el) => getComputedStyle(el).animationName,
      );
      expect(animationName).toBe("bw-reveal-enter");
    });
  }
});
