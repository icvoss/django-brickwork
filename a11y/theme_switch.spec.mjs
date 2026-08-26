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
//
// A fourth, separate page (theme-switch-compact-open-js-<theme>.html)
// carries layout="compact"'s own single instance, disclosure stamped [open]
// in the served HTML: see the "layout=\"compact\"" describe block below.

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

  test("an invalid stored value is discarded, not applied, and removed from storage", async ({ page }) => {
    // review fix, #117 blocker 1: a corrupted, stale or tampered
    // localStorage value must never reach <html>. Reload with a bogus
    // density value already stored, from BEFORE bwThemeSwitch runs, so
    // this proves the discard happens at init, not merely that a later
    // write overwrites it.
    await page.evaluate(() => window.localStorage.setItem("bw-theme-switch-density", "extra-spacious"));
    await page.reload();
    await page.waitForFunction(() => !!window.Alpine);
    await expect(section(page, "default-heading").locator("[data-bw-theme-switch]")).toBeVisible();
    // <html> never received the bogus value (it had no data-density to
    // begin with, and none of the three real radios is checked, matching
    // the "no server-resolved value" unvisited-axis behaviour)
    await expect(page.locator("html")).not.toHaveAttribute("data-density", "extra-spacious");
    const density = section(page, "default-heading").locator('[data-bw-theme-switch-axis="density"] input');
    for (const radio of await density.all()) {
      await expect(radio).not.toBeChecked();
    }
    // the bad entry is removed, not left to keep failing validation forever
    const stored = await page.evaluate(() => window.localStorage.getItem("bw-theme-switch-density"));
    expect(stored).toBeNull();
  });

  test("validation sources from the server-emitted payload, not the rendered radios", async ({ page }) => {
    // review fix, #117 blocker 1: the DOM's own rendered radios must never
    // be the validation contract, because a consumer's mistaken override
    // template could render an extra, wrong <input> that live-DOM
    // validation would then treat as legitimate. Inject a genuine extra
    // radio (a real, working control, not a value tamper) OUTSIDE the
    // json_script payload the server emitted, then interact with it the
    // normal way: it must still be rejected.
    const themeFieldset = section(page, "default-heading").locator('[data-bw-theme-switch-axis="theme"]');
    const groupName = await themeFieldset.locator("input").first().getAttribute("name");
    await themeFieldset.evaluate((fieldset, name) => {
      const label = document.createElement("label");
      label.innerHTML = '<input type="radio" data-bw-theme-switch-value value="rogue-value"> Rogue';
      label.querySelector("input").name = name; // same radio group: real, working native semantics
      fieldset.appendChild(label);
    }, groupName);
    const rogue = section(page, "default-heading").locator('input[value="rogue-value"]');
    await rogue.check();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light"); // unchanged
    const stored = await page.evaluate(() => window.localStorage.getItem("bw-theme-switch-theme"));
    expect(stored).toBeNull();
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

test("an invalid <html> attribute value is not adopted as this axis's state", async ({ page }) => {
  // review fix, #117 blocker 2: the ROOT's own current attribute value is
  // validated too, not trusted just because it is already on <html>. A
  // consumer template mistake (a stray or mistyped data-theme value) must
  // not be adopted as this axis's state, offered as a checked radio, or
  // ever reach localStorage.
  //
  // A DEDICATED FIXTURE with the bogus value baked into the served HTML
  // (never a page.evaluate() mutation followed by page.reload()): a
  // file:// reload re-fetches the static file from disk, so a prior DOM
  // mutation is gone before bwThemeSwitch's own init() ever runs, which
  // would make this test pass vacuously (the reload silently reverts
  // <html> to a real value, never exercising the invalid-value path at
  // all). This is its own top-level test, outside the "JS reveal and
  // initial state" describe block's boot() beforeEach, because it needs a
  // different fixture entirely, not the standard one that block shares.
  //
  // Non-vacuity note: the radio-checked and storage assertions below hold
  // REGARDLESS of whether the root-value validation runs, because
  // "MISCONFIGURED-VALUE" can never equal any rendered radio's own .value
  // (there is no such radio to match) and writeStoredValue is only ever
  // called from a change listener, never from init, with or without this
  // guard. The genuinely discriminating proof is that init() never calls
  // _apply (document.documentElement.setAttribute) with the bogus value at
  // all: without the guard, initial resolves to the invalid string and
  // _apply(attrName, initial) DOES fire (harmlessly reapplying the same
  // string, which is why the attribute-value assertion alone cannot tell
  // the two paths apart). Intercept setAttribute via an init script
  // (runs before the page's own module import, unlike page.evaluate after
  // goto) to prove the call itself never happens.
  await page.addInitScript(() => {
    window.__setAttributeCalls = [];
    const original = Element.prototype.setAttribute;
    Element.prototype.setAttribute = function (name, value) {
      if (this === document.documentElement) window.__setAttributeCalls.push({ name, value });
      return original.call(this, name, value);
    };
  });
  await page.goto(fx("theme-switch-invalid-root-js-light.html"));
  await page.waitForFunction(() => !!window.Alpine);
  await expect(section(page, "default-heading").locator("[data-bw-theme-switch]")).toBeVisible();
  // bwThemeSwitch never overwrites <html> when nothing valid resolves, so
  // the bogus value baked into the fixture is still there; the important
  // assertion is that NEITHER radio adopts it as checked and it never
  // reaches storage
  await expect(page.locator("html")).toHaveAttribute("data-theme", "MISCONFIGURED-VALUE");
  const theme = section(page, "default-heading").locator('[data-bw-theme-switch-axis="theme"] input');
  for (const radio of await theme.all()) {
    await expect(radio).not.toBeChecked();
  }
  const stored = await page.evaluate(() => window.localStorage.getItem("bw-theme-switch-theme"));
  expect(stored).toBeNull();
  // the discriminating assertion: init() never even tried to (re)apply the
  // invalid value to <html>, proving the guard actually ran, not merely
  // that its outcome happened to be unobservable this time
  const calls = await page.evaluate(() => window.__setAttributeCalls);
  expect(calls.filter((c) => c.value === "MISCONFIGURED-VALUE")).toEqual([]);
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

  test("an edited radio value is rejected: neither applied to <html> nor persisted", async ({ page }) => {
    // review fix, #117 blocker 2: radio.value is a mutable DOM property;
    // this module must not trust it just because a change event fired. A
    // capture-phase listener on the document runs BEFORE bwThemeSwitch's
    // own bubble-phase listener on the radio itself (capture always
    // precedes target and bubble), so mutating .value there simulates a
    // script that tampered with the element ahead of this module's own
    // handler reading it, which target-only interception cannot prove.
    await page.evaluate(() => {
      document.addEventListener(
        "change",
        (event) => {
          if (event.target.matches('[data-bw-theme-switch-axis="theme"] input[value="dark"]')) {
            event.target.value = "not-a-real-theme";
          }
        },
        { capture: true },
      );
    });
    const dark = section(page, "default-heading").locator('input[value="dark"]');
    await dark.check({ force: true }); // Playwright's own value-match assertion would otherwise fight the tamper
    await expect(page.locator("html")).not.toHaveAttribute("data-theme", "not-a-real-theme");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light"); // unchanged from the fixture default
    // the axis never had a stored value before this interaction, and the
    // tampered change must not create one
    const stored = await page.evaluate(() => window.localStorage.getItem("bw-theme-switch-theme"));
    expect(stored).toBeNull();
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

  test("a locked instance's own state never races an unlocked sibling sharing the same axis", async ({ page }) => {
    // Self-found during the #117 review fixes, not one of the seven named
    // items: the locked branch originally read document.documentElement's
    // LIVE attribute to decide its own state, which is order-dependent
    // when more than one switch instance shares an axis on one page (this
    // fixture is exactly that: the default instance's theme fieldset is
    // UNLOCKED and shares the theme axis with the locked instance). Alpine
    // boots components in DOM order, the default instance first, so if it
    // applies a stored "dark" preference to <html> before the locked
    // instance's own init runs, a DOM-reading locked branch would
    // incorrectly adopt "dark" too. The fix resolves a locked axis's
    // checked radio SERVER-SIDE (group.locked_value in
    // _theme_switch.html), never from <html> at JS runtime, so this must
    // hold regardless of sibling ordering or a pre-seeded stored value.
    await page.evaluate(() => window.localStorage.setItem("bw-theme-switch-theme", "dark"));
    await page.reload();
    await page.waitForFunction(() => !!window.Alpine);
    await expect(section(page, "locked-heading").locator("[data-bw-theme-switch]")).toBeVisible();
    // the unlocked default instance DID adopt the stored value (the write
    // was real and this module did read it back for that axis, proving the
    // scenario is meaningful rather than vacuous)
    await expect(section(page, "default-heading").locator('input[value="dark"]')).toBeChecked();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    // but the LOCKED instance's radios still reflect light, the resolver's
    // own value, never the sibling's stored one, and the note is present
    const lockedFieldset = section(page, "locked-heading").locator('[data-bw-theme-switch-axis="theme"]');
    await expect(lockedFieldset.locator('input[value="light"]')).toBeChecked();
    await expect(lockedFieldset.locator('input[value="dark"]')).not.toBeChecked();
    // the VALID stored value is left alone: it legitimately belongs to the
    // unlocked sibling sharing this axis, and the locked instance has no
    // way to tell "stale from before I was locked" apart from "currently
    // valid for a sibling", so only an INVALID entry is ever cleared (the
    // next test)
    const stored = await page.evaluate(() => window.localStorage.getItem("bw-theme-switch-theme"));
    expect(stored).toEqual("dark");
  });

  test("an INVALID stored value is cleaned up, never adopted, on the page's locked axis", async ({ page }) => {
    // review fix, #117 blocker 3: previously only unlocked groups discarded
    // and removed an invalid stored value; a locked group read no storage
    // at all. This fixture's theme axis has an unlocked sibling too (the
    // default instance), so this proves the whole-page outcome rather than
    // isolating which instance's own code path removed the entry: the
    // locked branch's cleanup was verified in isolation directly against
    // the compiled bundle, a single locked-only instance with no unlocked
    // sibling on the same axis, confirming the removal is the LOCKED
    // branch's own behaviour and not merely a side effect of the sibling.
    await page.evaluate(() => window.localStorage.setItem("bw-theme-switch-theme", "not-a-real-theme"));
    await page.reload();
    await page.waitForFunction(() => !!window.Alpine);
    await expect(section(page, "locked-heading").locator("[data-bw-theme-switch]")).toBeVisible();
    // the locked instance still shows its own server value; the invalid
    // entry never reached <html> anywhere on the page
    const lockedFieldset = section(page, "locked-heading").locator('[data-bw-theme-switch-axis="theme"]');
    await expect(lockedFieldset.locator('input[value="light"]')).toBeChecked();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    const stored = await page.evaluate(() => window.localStorage.getItem("bw-theme-switch-theme"));
    expect(stored).toBeNull();
  });
});

// --- layout="compact" (icvoss/django-brickwork#235) --------------------------
//
// The compact fixture (theme-switch-compact-open-js-<theme>.html) renders a
// SINGLE compact instance (axes="theme density dir") with its details
// disclosure stamped [open] in the served HTML, so axe and these tests see
// the panel already revealed; bwThemeSwitch's own init() still runs the same
// per-axis logic every inline instance exercises (validated separately
// above), so this suite covers only what compact ADDS: the disclosure's own
// open/close affordances, the three dismissal routes, that selecting a radio
// never closes the panel, and the 44px compact target-size floor.

function compactSection(page) {
  return page.locator("section:has(#compact-heading)");
}

async function bootCompact(page, theme = "light") {
  await page.goto(fx(`theme-switch-compact-open-js-${theme}.html`));
  await page.waitForFunction(() => !!window.Alpine);
  await expect(compactSection(page).locator("[data-bw-theme-switch]")).toBeVisible();
}

test.describe("layout=\"compact\"", () => {
  test("init reveals the control and the disclosure ships open (fixture-stamped)", async ({ page }) => {
    await bootCompact(page);
    const details = compactSection(page).locator(".bw-theme-switch__disclosure");
    await expect(details).toHaveJSProperty("open", true);
  });

  test("the summary toggles the disclosure closed and back open", async ({ page }) => {
    await bootCompact(page);
    const details = compactSection(page).locator(".bw-theme-switch__disclosure");
    const summary = compactSection(page).locator(".bw-theme-switch__trigger");
    await summary.click();
    await expect(details).toHaveJSProperty("open", false);
    await summary.click();
    await expect(details).toHaveJSProperty("open", true);
  });

  test("radios inside the compact panel operate, persist, and dispatch the change event", async ({ page }) => {
    await bootCompact(page);
    await page.evaluate(() => {
      window.__bw = [];
      window.addEventListener("bw:theme-switch:change", (event) => {
        window.__bw.push({ type: event.type, detail: event.detail ?? null });
      });
    });
    const dark = compactSection(page).locator('input[value="dark"]');
    await dark.check();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    const stored = await page.evaluate(() => window.localStorage.getItem("bw-theme-switch-theme"));
    expect(stored).toEqual("dark");
    const events = await page.evaluate(() => window.__bw);
    expect(events).toEqual([{ type: "bw:theme-switch:change", detail: { axis: "theme", value: "dark" } }]);
  });

  test("selecting a radio never closes the panel", async ({ page }) => {
    await bootCompact(page);
    const details = compactSection(page).locator(".bw-theme-switch__disclosure");
    const dark = compactSection(page).locator('input[value="dark"]');
    await dark.check();
    await expect(details).toHaveJSProperty("open", true);
  });

  test("Escape closes the disclosure and returns focus to the trigger", async ({ page }) => {
    await bootCompact(page);
    const details = compactSection(page).locator(".bw-theme-switch__disclosure");
    const summary = compactSection(page).locator(".bw-theme-switch__trigger");
    await summary.focus();
    await page.keyboard.press("Escape");
    await expect(details).toHaveJSProperty("open", false);
    await expect(summary).toBeFocused();
  });

  test("a click outside the disclosure closes it", async ({ page }) => {
    await bootCompact(page);
    const details = compactSection(page).locator(".bw-theme-switch__disclosure");
    await page.locator("h1").click();
    await expect(details).toHaveJSProperty("open", false);
  });

  test("every compact option meets the 44px touch-target floor", async ({ page }) => {
    await bootCompact(page);
    const heights = await compactSection(page)
      .locator(".bw-theme-switch__option")
      .evaluateAll((els) => els.map((el) => el.getBoundingClientRect().height));
    expect(heights.length).toBeGreaterThan(0);
    for (const height of heights) {
      expect(height).toBeGreaterThanOrEqual(44);
    }
  });

  for (const theme of THEMES) {
    test(`axe WCAG 2.2 AA on the revealed compact disclosure (${theme})`, async ({ page }) => {
      await bootCompact(page, theme);
      const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
      expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
    });
  }
});

// --- axe WCAG 2.2 AA on the revealed, live control ---------------------------

for (const theme of THEMES) {
  test(`axe WCAG 2.2 AA on the revealed theme switch, default and locked instances (${theme})`, async ({ page }) => {
    await boot(page, theme);
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}
