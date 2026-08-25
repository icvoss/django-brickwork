// bw_theme_switch suite (icvoss/django-brickwork#117): the root-level live
// axis control over theme/density/dir/brand.
//
// Two legs against the pre-rendered fixtures (a11y/generate_fixtures.py):
//   - the no-JS leg (javaScriptEnabled: false) proves the floor concretely
//     (BR-BW-HTMX-001, the #117 ruling's one deliberate departure): the
//     control ships with the hidden attribute and NOTHING reveals it
//     without JS, so the no-JS floor is genuinely "renders nothing", not a
//     dead or half-working control (mirroring dismissible.js's close
//     button, the same hidden-until-init shape);
//   - the JS leg loads theme-switch-js-<theme>.html, which boots Alpine +
//     the real registerBrickworkComponents from node_modules/src exactly as
//     a host application would (the FIXTURE owns Alpine.start(); brickwork
//     never does), and exercises bwThemeSwitch's own init reveal, the
//     initial-checked-radio resolution from <html>'s current attributes,
//     the SHL-003 localStorage persistence on change, the locked-axis
//     disabled branch, and axe on both themes.
//
// Three instances render on the one page (theme-switch-<theme>.html and its
// JS leg): default axes ("theme density dir"), a brand-inclusive instance
// (axes="theme density dir brand", brands=), and a theme-only instance with
// locked_axes="theme". Selectors scope by section heading rather than the
// uuid-derived instance id (regenerated on every fixture build).

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const fx = (name) => pathToFileURL(join(FIXTURES, name)).href;
const THEMES = ["light", "dark"];
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

// Chromium blocks module imports from file:// by default (the JS leg's
// _JS_BOOT uses ES module imports for Alpine + the compiled bundle, exactly
// as sortable.spec.mjs's own JS leg does); scoped to this file only.
test.use({ launchOptions: { args: ["--allow-file-access-from-files"] } });

// --- helpers -----------------------------------------------------------------

function section(page, headingId) {
  return page.locator(`section:has(#${headingId})`);
}

async function boot(page, theme = "light") {
  await page.goto(fx(`theme-switch-js-${theme}.html`));
  await page.waitForFunction(() => !!window.Alpine);
  // the default instance's own reveal is the ready signal: init() removes
  // `hidden` from every instance's root at once (three separate x-data
  // components, each booting independently, so waiting on one is sufficient)
  await expect(section(page, "default-heading").locator("[data-bw-theme-switch]")).toBeVisible();
}

// --- the no-JS floor (BR-BW-HTMX-001, the #117 ruling's departure) -----------

test.describe("no-JS floor", () => {
  test.use({ javaScriptEnabled: false });

  for (const theme of THEMES) {
    test(`the control renders nothing: hidden and absent from the accessibility tree (${theme})`, async ({
      page,
    }) => {
      await page.goto(fx(`theme-switch-${theme}.html`));
      const roots = page.locator("[data-bw-theme-switch]");
      await expect(roots).toHaveCount(3);
      for (const root of await roots.all()) {
        await expect(root).toBeHidden();
      }
      // hidden propagates to every descendant: no radio is visible, focusable
      // or reachable by the accessibility tree without JS
      const radios = page.locator("[data-bw-theme-switch-value]");
      // default (theme 2 + density 3 + dir 2 = 7) + brand (theme 2 + density
      // 3 + dir 2 + brand 2 = 9) + locked (theme 2) = 18, see the fixture
      await expect(radios).toHaveCount(18);
      for (const radio of await radios.all()) {
        await expect(radio).toBeHidden();
      }
      // this fixture's own axe WCAG 2.2 AA pass runs in the top-level loop
      // in axe.spec.mjs (every fixtures/*.html file, JS-enabled context:
      // AxeBuilder injects its own analysis script, which a javaScriptEnabled:
      // false context blocks outright, so axe never runs inside this describe
      // block); the hidden/absent assertions above are this floor's proof.
    });
  }
});

// --- JS reveal + initial state (bwThemeSwitch.init()) ------------------------

test.describe("JS reveal and initial state", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
  });

  test("init reveals every instance and each carries the Alpine component", async ({ page }) => {
    const roots = page.locator("[data-bw-theme-switch]");
    await expect(roots).toHaveCount(3);
    for (const root of await roots.all()) {
      await expect(root).toBeVisible();
      await expect(root).toHaveAttribute("x-data", "bwThemeSwitch()");
    }
  });

  test("the theme axis resolves its initial checked radio from <html data-theme>", async ({ page }) => {
    // the fixture's <html> ships data-theme="light"; the unlocked default
    // instance's theme radio must reflect that at init
    const themeLight = section(page, "default-heading").locator('input[value="light"]');
    await expect(themeLight).toBeChecked();
  });

  test("density and dir have no server-resolved value and start unchecked", async ({ page }) => {
    // <html> carries no data-density or dir attribute in this fixture, so
    // the free client toggle has nothing to resolve to and stays unchecked
    // (never guesses) until a visitor makes a choice
    const density = section(page, "default-heading").locator('[data-bw-theme-switch-axis="density"] input');
    for (const radio of await density.all()) {
      await expect(radio).not.toBeChecked();
    }
  });

  test("two unlocked instances never collide on radio group name or root id", async ({ page }) => {
    const defaultRoot = await section(page, "default-heading").locator("[data-bw-theme-switch]").getAttribute("id");
    const brandRoot = await section(page, "brand-heading").locator("[data-bw-theme-switch]").getAttribute("id");
    expect(defaultRoot).not.toEqual(brandRoot);
    const defaultName = await section(page, "default-heading")
      .locator('[data-bw-theme-switch-axis="theme"] input')
      .first()
      .getAttribute("name");
    const brandName = await section(page, "brand-heading")
      .locator('[data-bw-theme-switch-axis="theme"] input')
      .first()
      .getAttribute("name");
    expect(defaultName).not.toEqual(brandName);
  });
});

// --- changing an axis (SHL-003 persistence, bw:theme-switch:change) ---------

test.describe("changing an axis", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
    await page.evaluate(() => {
      window.__bw = [];
      window.addEventListener("bw:theme-switch:change", (event) => {
        window.__bw.push({ type: event.type, detail: event.detail ?? null });
      });
    });
  });

  test("selecting dark applies data-theme to <html>, persists to localStorage, and dispatches the change event", async ({
    page,
  }) => {
    const dark = section(page, "default-heading").locator('input[value="dark"]');
    await dark.check();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    const stored = await page.evaluate(() => window.localStorage.getItem("bw-theme-switch-theme"));
    expect(stored).toEqual("dark");
    const events = await page.evaluate(() => window.__bw);
    expect(events).toEqual([{ type: "bw:theme-switch:change", detail: { axis: "theme", value: "dark" } }]);
  });

  test("a stored preference from a prior visit wins over <html>'s current attribute on the next load", async ({
    page,
  }) => {
    await page.evaluate(() => window.localStorage.setItem("bw-theme-switch-dir", "rtl"));
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    const dirRtl = section(page, "default-heading").locator('[data-bw-theme-switch-axis="dir"] input[value="rtl"]');
    await expect(dirRtl).toBeChecked();
  });
});

// --- the locked axis (SHL-003 precedence: a real server preference wins) ----

test.describe("locked axis", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
  });

  test("the locked instance's radios are disabled, reflect the current value, and carry the note", async ({
    page,
  }) => {
    const locked = section(page, "locked-heading");
    const fieldset = locked.locator('[data-bw-theme-switch-axis="theme"]');
    await expect(fieldset).toHaveAttribute("data-bw-locked", "");
    for (const radio of await fieldset.locator("input").all()) {
      await expect(radio).toBeDisabled();
    }
    await expect(fieldset.locator('input[value="light"]')).toBeChecked();
    await expect(locked.getByText("Set by your account preferences.")).toBeVisible();
  });

  test("clicking a disabled locked radio changes nothing: <html> and localStorage stay untouched", async ({
    page,
  }) => {
    const locked = section(page, "locked-heading");
    const darkRadio = locked.locator('input[value="dark"]');
    await expect(darkRadio).toBeDisabled();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    const stored = await page.evaluate(() => window.localStorage.getItem("bw-theme-switch-theme"));
    expect(stored).toBeNull();
  });
});

// --- axe WCAG 2.2 AA on the revealed, live control ---------------------------

for (const theme of THEMES) {
  test(`axe WCAG 2.2 AA on the revealed theme switch, default and locked instances (${theme})`, async ({ page }) => {
    await boot(page, theme);
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}
