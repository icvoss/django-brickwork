// bwTooltip focus suite (icvoss/django-brickwork#355): the enhanced bubble
// must open on keyboard/touch focus, not just hover, when the trigger block
// contains a focusable element (_tooltip.html's own documented usage, e.g.
// a real <button> in the trigger block).
//
// Against feedback-js-<theme>.html (a11y/generate_fixtures.py), which boots
// Alpine from node_modules exactly as a host application would (the FIXTURE
// owns Alpine.start(); brickwork never does) and renders the real
// _tooltip.html extended with a button trigger
// (`aria-label="More info"`, bubble id "feedback-tip"). The bubble starts
// hidden; this fixture is the JS-boot leg with the tooltip in its closed
// rest state (feedback-tooltip-open-<theme>.html is the separate,
// statically-stamped OPEN state axe.spec.mjs already covers).
//
// Chromium blocks module imports from file:// by default, so this file's
// browser launches with --allow-file-access-from-files (scoped here; the
// axe.spec.mjs run is untouched).

import { test, expect } from "@playwright/test";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const fx = (name) => pathToFileURL(join(FIXTURES, name)).href;

test.use({ launchOptions: { args: ["--allow-file-access-from-files"] } });

async function boot(page) {
  await page.goto(fx("feedback-js-light.html"));
  await page.waitForFunction(() => !!window.Alpine);
}

const trigger = (page) => page.getByRole("button", { name: "More info" });
const bubble = (page) => page.locator("#feedback-tip");

test.describe("tooltip focus (#355)", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
  });

  test("the bubble is hidden at rest", async ({ page }) => {
    await expect(bubble(page)).toBeHidden();
  });

  test("focusing the inner trigger button opens the bubble", async ({ page }) => {
    await trigger(page).focus();
    await expect(bubble(page)).toBeVisible();
  });

  test("moving focus away from the trigger closes the bubble", async ({ page }) => {
    await trigger(page).focus();
    await expect(bubble(page)).toBeVisible();
    // Tab moves focus to the next focusable element on the page, which is
    // outside the trigger subtree, so this must close the bubble.
    await page.keyboard.press("Tab");
    await expect(bubble(page)).toBeHidden();
  });

  test("hover still opens the bubble (unchanged path)", async ({ page }) => {
    await trigger(page).hover();
    await expect(bubble(page)).toBeVisible();
  });

  test("Escape closes the bubble while the trigger is focused", async ({ page }) => {
    await trigger(page).focus();
    await expect(bubble(page)).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(bubble(page)).toBeHidden();
    // Escape leaves focus on the trigger (a tooltip is not a dialog and
    // never traps or moves focus itself).
    await expect(trigger(page)).toBeFocused();
  });
});
