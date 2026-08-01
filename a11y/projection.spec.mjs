// Tailwind projection proof (AC-BW-095, the dynamic half).
//
// projection-<theme>.html is a CONSUMER page: no brickwork.css, no component
// classes, only utilities from a REAL Tailwind 4 build over the shipped
// dist/tailwind-theme.css fragment (compiled at fixture-generation time by
// a11y/build-projection-css.mjs), with dist/tokens.css inlined alongside.
// Because every projected value is a var(--bw-*) reference, the SAME compiled
// CSS must restyle when data-theme flips or a data-bw-brand override lands on
// <html>: no rebuild, no second stylesheet. That is what these tests observe.
//
// Computed values are compared probe-to-probe: a probe element styled inline
// with the token var (or a literal) is read through the very same
// getComputedStyle serialisation as the utility-styled card, so colour
// serialisation differences (oklch vs rgb) can never produce a false result.
// The pages carry no scripts and no animations, so no settling is needed;
// both theme variants also join the axe gate via axe.spec.mjs's fixture walk.

import { test, expect } from "@playwright/test";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const fx = (name) => pathToFileURL(join(FIXTURES, name)).href;
const THEMES = ["light", "dark"];

// The computed value PROP resolves to for an inline declaration set on a probe
// attached to <body> (the same cascade the card sees). `styles` lets a probe
// carry companion declarations (e.g. font-size alongside line-height, since
// the line-height tokens are unitless ratios).
function probeComputed(page, prop, value, styles = {}) {
  return page.evaluate(
    ([p, v, extra]) => {
      const el = document.createElement("div");
      for (const [k, val] of Object.entries(extra)) el.style.setProperty(k, val);
      el.style.setProperty(p, v);
      document.body.appendChild(el);
      const out = getComputedStyle(el).getPropertyValue(p);
      el.remove();
      return out;
    },
    [prop, value, styles],
  );
}

const cardComputed = (page, prop) =>
  page.locator("#projection-card").evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);

const bodyComputed = (page, prop) =>
  page.evaluate((p) => getComputedStyle(document.body).getPropertyValue(p), prop);

for (const theme of THEMES) {
  test(`consumer utilities resolve through the live tokens (${theme})`, async ({ page }) => {
    await page.goto(fx(`projection-${theme}.html`));
    // bg-accent is EXACTLY the current --bw-color-accent, and actually paints
    const bg = await cardComputed(page, "background-color");
    expect(bg).toBe(await probeComputed(page, "background-color", "var(--bw-color-accent)"));
    expect(bg).not.toBe("rgba(0, 0, 0, 0)");
    // text-fg-on-accent pairs the on-accent foreground with it
    expect(await cardComputed(page, "color")).toBe(await probeComputed(page, "color", "var(--bw-color-fg-on-accent)"));
    // rounded-md is the radius step, not Tailwind's default --radius-md
    const radius = await cardComputed(page, "border-top-left-radius");
    expect(radius).toBe(await probeComputed(page, "border-top-left-radius", "var(--bw-size-radius-md)"));
    expect(radius).not.toBe("0px");
    // shadow-3 carries the elevation ladder value: Tailwind composes
    // box-shadow from its ring/inset slots, so the elevation's serialisation
    // must appear within the composed computed list (and something must paint)
    const shadow = await cardComputed(page, "box-shadow");
    expect(shadow).not.toBe("none");
    expect(shadow).toContain(await probeComputed(page, "box-shadow", "var(--bw-elevation-3)"));
    // text-body-lg is the type role pair: size plus its line-height companion
    // (the line-height tokens are unitless, so the probe carries the role's
    // font-size too, exactly as the utility does)
    expect(await cardComputed(page, "font-size")).toBe(
      await probeComputed(page, "font-size", "var(--bw-text-body-lg-size)"),
    );
    expect(await cardComputed(page, "line-height")).toBe(
      await probeComputed(page, "line-height", "var(--bw-text-body-lg-line-height)", {
        "font-size": "var(--bw-text-body-lg-size)",
      }),
    );
    // the page canvas runs through the projection too
    expect(await bodyComputed(page, "background-color")).toBe(
      await probeComputed(page, "background-color", "var(--bw-color-surface)"),
    );
  });

  test(`p-4 padding is 4 x the --bw-size-space-1 base (${theme})`, async ({ page }) => {
    await page.goto(fx(`projection-${theme}.html`));
    // --spacing projects the DYNAMIC base only (the space scale is authored
    // as Tailwind --spacing multiples of 0.25rem, DESIGN.md 6.1), so p-4
    // must equal calc(4 * space-1) exactly, on every side
    const expected = await probeComputed(page, "padding-top", "calc(4 * var(--bw-size-space-1))");
    expect(parseFloat(expected)).toBeGreaterThan(0);
    for (const side of ["padding-top", "padding-right", "padding-bottom", "padding-left"]) {
      expect(await cardComputed(page, side)).toBe(expected);
    }
  });

  test(`a data-bw-brand override on <html> recolours the utilities (${theme})`, async ({ page }) => {
    // the fixture bakes an inert [data-bw-brand="proof"] override of
    // --bw-color-accent; stamping the attribute on the ROOT element (the
    // shell's brand hook: derived tokens compute at :root) must recolour the
    // consumer utility with no rebuild
    await page.goto(fx(`projection-${theme}.html`));
    const before = await cardComputed(page, "background-color");
    await page.evaluate(() => document.documentElement.setAttribute("data-bw-brand", "proof"));
    const after = await cardComputed(page, "background-color");
    expect(after).not.toBe(before);
    expect(after).toBe(await probeComputed(page, "background-color", "oklch(0.5 0.2 300)"));
  });
}

test("flipping data-theme to dark restyles the same compiled CSS", async ({ page }) => {
  // one page load, one stylesheet: the light fixture flipped to dark must
  // repaint to the dark token values with no rebuild and no navigation
  await page.goto(fx("projection-light.html"));
  const lightBg = await cardComputed(page, "background-color");
  const lightCanvas = await bodyComputed(page, "background-color");
  await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
  const darkBg = await cardComputed(page, "background-color");
  expect(darkBg).not.toBe(lightBg);
  expect(darkBg).toBe(await probeComputed(page, "background-color", "var(--bw-color-accent)"));
  const darkCanvas = await bodyComputed(page, "background-color");
  expect(darkCanvas).not.toBe(lightCanvas);
  expect(darkCanvas).toBe(await probeComputed(page, "background-color", "var(--bw-color-surface)"));
});
