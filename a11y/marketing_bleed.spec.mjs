// Hero width="bleed" composed with atmosphere="soft-stage" (ADR-057 section
// 1a, icvoss/django-brickwork#710). Proves the viewport-escape geometry
// live: a class-presence or computed-style assertion on the CSS declarations
// alone cannot catch a regression where the modifier class stops reaching
// the DOM at all, or where a later rule in the cascade reintroduces the
// marketing rail's max-inline-size. Only a bounding-box measurement against
// window.innerWidth can. The negative control (the plain soft-stage-overlay
// fixture, no bleed) proves the assertion has teeth: it fails if the bleed
// modifier stops doing anything, because the control hero stays narrower
// than the viewport.

import { test, expect } from "@playwright/test";
import { pathToFileURL } from "node:url";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const VIEWPORT_WIDTH = 1440;

for (const theme of ["light", "dark"]) {
  test(`hero width="bleed" spans the viewport under atmosphere="soft-stage" (${theme})`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: VIEWPORT_WIDTH, height: 900 });
    await page.goto(
      pathToFileURL(join(FIXTURES, `hero-bleed-soft-stage-${theme}.html`)).href,
    );

    const hero = page.locator(".bw-hero--bleed.bw-hero--atmosphere-soft-stage");
    await expect(hero).toBeVisible();

    const heroBox = await hero.evaluate((el) => el.getBoundingClientRect());
    expect(Math.abs(heroBox.width - VIEWPORT_WIDTH)).toBeLessThanOrEqual(1);

    const stage = hero.locator(".bw-stage");
    await expect(stage).toHaveCount(1);
    const stageBox = await stage.evaluate((el) => el.getBoundingClientRect());
    expect(Math.abs(stageBox.width - heroBox.width)).toBeLessThanOrEqual(1);
    expect(Math.abs(stageBox.left - heroBox.left)).toBeLessThanOrEqual(1);

    const copy = hero.locator(".bw-hero__copy");
    const copyBox = await copy.evaluate((el) => el.getBoundingClientRect());
    expect(copyBox.left).toBeGreaterThanOrEqual(48);

    // Alignment proof (4.3.1): the bleed hero's CONTENT edge (its own left
    // plus its computed inline-start padding) must sit exactly where the
    // contained hero's content edge sits: cap plus page gutter. Measured on
    // the hero box, not on .bw-hero__copy, because these fixtures centre the
    // copy and a centred child's left edge does not move with symmetric
    // padding. In 4.3.0 the padding was max(cap, gutter), which dropped the
    // gutter on wide viewports and put the content one gutter outside every
    // other band.
    const bleedContentEdge = await hero.evaluate(
      (el) => el.getBoundingClientRect().left + parseFloat(getComputedStyle(el).paddingInlineStart),
    );
    await page.goto(
      pathToFileURL(join(FIXTURES, `soft-stage-overlay-${theme}.html`)).href,
    );
    const containedHero = page.locator(".bw-hero").first();
    await expect(containedHero).toBeVisible();
    const containedContentEdge = await containedHero.evaluate(
      (el) => el.getBoundingClientRect().left + parseFloat(getComputedStyle(el).paddingInlineStart),
    );
    expect(Math.abs(bleedContentEdge - containedContentEdge)).toBeLessThanOrEqual(1);
  });

  test(`hero stays on the marketing rail without width="bleed" (${theme})`, async ({
    page,
  }) => {
    // Negative control: soft-stage-overlay-<theme>.html composes the same
    // atmosphere="soft-stage" hero under the same overlay header, but
    // without width="bleed" (the default "contained"). If the bleed
    // modifier ever stopped doing anything, this fixture and the bleed
    // fixture above would converge and the assertion above would stop
    // proving anything.
    await page.setViewportSize({ width: VIEWPORT_WIDTH, height: 900 });
    await page.goto(
      pathToFileURL(join(FIXTURES, `soft-stage-overlay-${theme}.html`)).href,
    );

    const hero = page.locator(".bw-hero--atmosphere-soft-stage");
    await expect(hero).toBeVisible();
    await expect(hero).not.toHaveClass(/bw-hero--bleed/);

    const heroBox = await hero.evaluate((el) => el.getBoundingClientRect());
    expect(heroBox.width).toBeLessThan(VIEWPORT_WIDTH);
  });
}
