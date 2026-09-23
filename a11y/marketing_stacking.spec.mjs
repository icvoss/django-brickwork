// Soft-stage atmosphere composed with media_placement="behind" (BR-BW-MKT-007
// rule 3, ADR-057 section 1a). Proves paint order live: the isolated stacking
// context fix (frontend/src/marketing.css, .bw-stage at z-index: -1 inside an
// isolate root) must keep the decorative .bw-stage layer, then .bw-hero__media,
// both behind .bw-hero__copy and its scrim. A computed-style or class-presence
// assertion cannot catch a stacking regression (the old child-lifting rule
// still emitted the right classes; it painted media over copy anyway), so
// this uses document.elementFromPoint at the heading's centre, which only a
// correct paint order can satisfy.

import { test, expect } from "@playwright/test";
import { pathToFileURL } from "node:url";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");

for (const theme of ["light", "dark"]) {
  test(`soft-stage keeps copy above media and stage under media_placement="behind" (${theme})`, async ({
    page,
  }) => {
    await page.goto(
      pathToFileURL(join(FIXTURES, `soft-stage-media-behind-${theme}.html`)).href,
    );

    const hero = page.locator(".bw-hero--atmosphere-soft-stage.bw-hero--media-behind");
    await expect(hero).toBeVisible();

    const stage = hero.locator(".bw-stage");
    await expect(stage).toHaveCount(1);

    const stageZIndex = await stage.evaluate((el) => getComputedStyle(el).zIndex);
    expect(stageZIndex).toBe("-1");

    const heading = hero.locator(".bw-hero__heading");
    await expect(heading).toBeVisible();

    const hitInsideCopy = await heading.evaluate((el) => {
      const rect = el.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const hit = document.elementFromPoint(x, y);
      const copy = el.closest(".bw-hero__copy");
      return Boolean(hit && copy && copy.contains(hit));
    });
    expect(hitInsideCopy).toBe(true);

    const hitOutsideMediaAndStage = await heading.evaluate((el) => {
      const rect = el.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const hit = document.elementFromPoint(x, y);
      const media = el.closest(".bw-hero")?.querySelector(".bw-hero__media");
      const stageEl = el.closest(".bw-hero")?.querySelector(".bw-stage");
      const hitIsMedia = Boolean(media && hit && (hit === media || media.contains(hit)));
      const hitIsStage = Boolean(stageEl && hit && (hit === stageEl || stageEl.contains(hit)));
      return !hitIsMedia && !hitIsStage;
    });
    expect(hitOutsideMediaAndStage).toBe(true);
  });
}
