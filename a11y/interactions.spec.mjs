// Interaction-set suite (0.8.0): disclosure, dropdown, tabs, modal.
//
// Two legs against the pre-rendered fixtures (a11y/generate_fixtures.py):
//   - the no-JS leg (javaScriptEnabled: false) proves every named floor
//     concretely (AC-BW-085/086);
//   - the JS leg loads interactions-js-<theme>.html, which boots Alpine +
//     @alpinejs/focus + htmx from node_modules exactly as a host application
//     would (the FIXTURE owns Alpine.start(); brickwork never does), and
//     exercises the full APG keyboard maps (AC-BW-080/081/083), the bw:
//     event conventions (AC-BW-087), axe on OPEN states in both themes
//     (AC-BW-088), reduced motion (AC-BW-089), and layout-shift discipline
//     (AC-BW-094).
//
// Chromium blocks module imports and XHR from file:// by default, so this
// file's browser launches with --allow-file-access-from-files (scoped here;
// the axe.spec.mjs run is untouched).
//
// AC-BW-093 keyboard-map-to-assertion inventory (04-interfaces section 4b):
//   dropdown: Enter/Space/ArrowDown open+first, ArrowUp open+last ...... "opens from the trigger keys"
//             ArrowDown/ArrowUp wrap, Home/End ......................... "roving focus wraps and jumps"
//             printable typeahead ...................................... "typeahead moves to the next match"
//             Escape / outside click / Tab ............................. "dismissal routes close and restore focus"
//             Enter/Space activates, focus returns on selection ........ "selection activates the item"
//   tabs:     roving tabindex (active 0, rest -1) ...................... "roving tabindex after upgrade"
//             ArrowRight/ArrowLeft wrap, Home/End ...................... "arrows move focus without activating"
//             Enter/Space activates (MANUAL, owner ruling) ............. "Enter activates the focused tab"
//             Tab from active tab enters the active panel (CBH-015) .... "Tab moves into the panel"
//   modal:    focus moves in on open ([data-bw-autofocus]) ............. "open moves focus into the dialog"
//             Tab/Shift+Tab wrap inside the trap ....................... "the trap wraps both directions"
//             Escape / close control / backdrop close; focus returns ... "every dismissal route restores the invoker"
//   disclosure: Tab to summary, Enter/Space toggles (native) ........... no-JS leg, "disclosure floor"

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const fx = (name) => pathToFileURL(join(FIXTURES, name)).href;
const THEMES = ["light", "dark"];
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

test.use({ launchOptions: { args: ["--allow-file-access-from-files"] } });

// --- helpers -----------------------------------------------------------------

async function boot(page, theme = "light") {
  await page.goto(fx(`interactions-js-${theme}.html`));
  await page.waitForFunction(() => !!window.Alpine);
  // bwTabs' upgrade is the ready signal: APG roles exist only once the
  // components are running (the upgrade-at-init doctrine).
  await expect(page.locator('[data-bw-tablist][role="tablist"]')).toBeAttached();
}

async function captureEvents(page) {
  await page.evaluate(() => {
    window.__bw = [];
    for (const name of [
      "bw:dropdown:open",
      "bw:dropdown:close",
      "bw:tabs:change",
      "bw:modal:open",
      "bw:modal:close",
    ]) {
      window.addEventListener(name, (event) => {
        window.__bw.push({ type: event.type, detail: event.detail ?? null });
      });
    }
  });
}

const recordedEvents = (page) => page.evaluate(() => window.__bw);
const activeText = (page) => page.evaluate(() => document.activeElement?.textContent?.trim() ?? "");
const activeId = (page) => page.evaluate(() => document.activeElement?.id ?? "");

const dropdown = (page) => page.locator("details.bw-dropdown");
const ddTrigger = (page) => page.locator("details.bw-dropdown summary");

async function openModal(page) {
  await page.locator("#open-confirm-modal").focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#confirm-reset")).toHaveAttribute("data-bw-open", "");
}

async function settleAnimations(page) {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)));
}

async function armLayoutShiftObserver(page, allowedSelectors) {
  await page.evaluate((allowed) => {
    window.__ls = [];
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const sources = entry.sources ?? [];
        const outside = sources.some((source) => {
          const node = source.node;
          if (!node) return false; // detached: cannot be attributed
          const el = node.nodeType === 1 ? node : node.parentElement;
          if (!el) return false;
          return !allowed.some((sel) => el.closest(sel));
        });
        window.__ls.push({ value: entry.value, outside });
      }
    });
    observer.observe({ type: "layout-shift", buffered: false });
  }, allowedSelectors);
}

const outsideShiftScore = (page) =>
  page.evaluate(() => window.__ls.filter((e) => e.outside).reduce((sum, e) => sum + e.value, 0));

// --- the no-JS floors (AC-BW-085, AC-BW-086, BR-BW-HTMX-006) ------------------

test.describe("no-JS floors", () => {
  test.use({ javaScriptEnabled: false });

  for (const theme of THEMES) {
    test(`dropdown floor is a details disclosure of plain links (${theme})`, async ({ page }) => {
      await page.goto(fx(`interactions-${theme}.html`));
      const dd = page.locator("details.bw-dropdown");
      await expect(dd).toHaveCount(1);
      // no menu semantics without the behaviour that honours them
      await expect(page.locator('[role="menu"], [role="menuitem"], [aria-haspopup]')).toHaveCount(0);
      await expect(page.locator("nav.bw-dropdown__panel")).toBeHidden();
      await ddTrigger(page).click();
      await expect(dd).toHaveAttribute("open");
      const items = page.locator("[data-bw-dropdown-item]");
      await expect(items).toHaveCount(3);
      await expect(items.first()).toHaveAttribute("href", "#dd-new-widget");
    });

    test(`disclosure floor toggles and groups natively (${theme})`, async ({ page }) => {
      await page.goto(fx(`interactions-${theme}.html`));
      const disclosures = page.locator("details.bw-disclosure");
      await expect(disclosures).toHaveCount(3);
      // pointer: the first opens
      await disclosures.nth(0).locator("summary").click();
      await expect(disclosures.nth(0)).toHaveAttribute("open");
      // keyboard: Enter on the second's summary opens it, and the shared
      // name attribute closes the first with zero script (CBH-016)
      await disclosures.nth(1).locator("summary").focus();
      await page.keyboard.press("Enter");
      await expect(disclosures.nth(1)).toHaveAttribute("open");
      await expect(disclosures.nth(0)).not.toHaveAttribute("open");
    });

    test(`tabs floor navigates as real anchors to the server-rendered panel (${theme})`, async ({ page }) => {
      await page.goto(fx(`interactions-${theme}.html`));
      await expect(page.locator("a.bw-tabs__tab")).toHaveCount(3);
      // no APG claims without the keyboard behaviour running
      await expect(page.locator('[role="tab"], [role="tablist"]')).toHaveCount(0);
      await expect(page.locator('a.bw-tabs__tab[aria-current="page"]')).toHaveText(/Overview/);
      await expect(page.locator("#bw-tabpanel-itx-overview")).toBeVisible();
      await expect(page.locator("#bw-tabpanel-itx-details")).toBeHidden();
      // switching tabs is an ordinary navigation; the server renders the
      // lazy tab's content full-page (AC-BW-085)
      await page.locator('a.bw-tabs__tab[data-bw-tab-key="activity"]').click();
      await expect(page).toHaveURL(new RegExp(`interactions-tab-lazy-${theme}\\.html`));
      await expect(page.locator("#bw-tabpanel-itx-activity")).toBeVisible();
      await expect(page.getByText("Priya restocked Alpha")).toBeVisible();
    });

    test(`modal floor is a real page with a working form and exit (${theme})`, async ({ page }) => {
      await page.goto(fx(`interactions-${theme}.html`));
      await page.locator("#open-confirm-modal").click();
      await expect(page).toHaveURL(new RegExp(`interactions-modal-page-${theme}\\.html`));
      // the same content and action, as an ordinary page
      await expect(page.locator(".bw-modal__title")).toHaveText("Reset demo data");
      await expect(page.locator("#confirm-reset-form")).toHaveAttribute("method", "post");
      await page.locator("#confirm-reset-input").fill("RESET");
      await expect(page.locator('button[form="confirm-reset-form"]')).toBeVisible();
      // the close control is a real anchor back out (close_url), never a
      // dead trigger; following it completes the loop
      await page.locator("a.bw-modal__close").click();
      await expect(page).toHaveURL(new RegExp(`interactions-${theme}\\.html`));
    });

    test(`dropdown danger action reaches the confirm page as a plain link (${theme})`, async ({ page }) => {
      await page.goto(fx(`interactions-${theme}.html`));
      await ddTrigger(page).click();
      await page.locator("[data-bw-dropdown-item]", { hasText: "Reset demo data" }).click();
      await expect(page).toHaveURL(new RegExp(`interactions-modal-page-${theme}\\.html`));
    });
  }
});

// --- dropdown keyboard map (AC-BW-081, BR-BW-JS-005/006) ----------------------

test.describe("dropdown keyboard", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
    await captureEvents(page);
  });

  test("opens from the trigger keys with the documented initial focus", async ({ page }) => {
    const trigger = ddTrigger(page);
    for (const [key, expected] of [
      ["Enter", "New widget"],
      [" ", "New widget"],
      ["ArrowDown", "New widget"],
      ["ArrowUp", "Delete demo data"],
    ]) {
      await trigger.focus();
      await page.keyboard.press(key === " " ? "Space" : key);
      await expect(dropdown(page)).toHaveAttribute("data-bw-open", "");
      expect(await activeText(page)).toContain(expected);
      await page.keyboard.press("Escape");
      await expect(dropdown(page)).not.toHaveAttribute("data-bw-open", "");
    }
    // upgraded semantics exist while the behaviour runs
    await expect(trigger).toHaveAttribute("aria-haspopup", "menu");
    await expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  test("roving focus wraps and Home/End jump", async ({ page }) => {
    await ddTrigger(page).focus();
    await page.keyboard.press("Enter");
    expect(await activeText(page)).toContain("New widget");
    await page.keyboard.press("ArrowDown");
    expect(await activeText(page)).toContain("Draft widgets");
    await page.keyboard.press("ArrowDown");
    expect(await activeText(page)).toContain("Delete demo data");
    await page.keyboard.press("ArrowDown"); // wraps
    expect(await activeText(page)).toContain("New widget");
    await page.keyboard.press("ArrowUp"); // wraps back
    expect(await activeText(page)).toContain("Delete demo data");
    await page.keyboard.press("Home");
    expect(await activeText(page)).toContain("New widget");
    await page.keyboard.press("End");
    expect(await activeText(page)).toContain("Delete demo data");
    // the items are reached by arrows, never by Tab: they sit outside the
    // tab order while the menu is open (menuitem tabindex -1)
    await expect(page.locator('[data-bw-dropdown-item][role="menuitem"]').first()).toHaveAttribute("tabindex", "-1");
  });

  test("typeahead moves to the next item starting with the typed character", async ({ page }) => {
    await ddTrigger(page).focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("d");
    expect(await activeText(page)).toContain("Draft widgets");
    await page.keyboard.press("d");
    expect(await activeText(page)).toContain("Delete demo data");
  });

  test("Escape, outside click, and Tab all dismiss; focus returns to the trigger", async ({ page }) => {
    const trigger = ddTrigger(page);
    // Escape returns focus to the trigger (CBH-008, BR-BW-JS-006)
    await trigger.focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Escape");
    await expect(dropdown(page)).not.toHaveAttribute("data-bw-open", "");
    expect(await page.evaluate(() => document.activeElement === document.querySelector("details.bw-dropdown summary"))).toBe(true);
    // outside click closes
    await trigger.focus();
    await page.keyboard.press("Enter");
    await page.locator("#dropdown-demo-heading").click();
    await expect(dropdown(page)).not.toHaveAttribute("data-bw-open", "");
    // Tab closes and continues the tab sequence (never onto a menu item)
    await trigger.focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Tab");
    await expect(dropdown(page)).not.toHaveAttribute("data-bw-open", "");
    expect(await page.evaluate(() => document.querySelector("details.bw-dropdown").contains(document.activeElement))).toBe(false);
  });

  test("selection activates the item, closes the menu, and returns focus", async ({ page }) => {
    await ddTrigger(page).focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Enter"); // activates "New widget" (#dd-new-widget)
    await expect(dropdown(page)).not.toHaveAttribute("data-bw-open", "");
    expect(await page.evaluate(() => document.activeElement === document.querySelector("details.bw-dropdown summary"))).toBe(true);
    const events = await recordedEvents(page);
    expect(events.filter((e) => e.type === "bw:dropdown:open")).toHaveLength(1);
    expect(events.filter((e) => e.type === "bw:dropdown:close")).toHaveLength(1);
  });
});

// --- tabs keyboard map (AC-BW-083, MANUAL activation per owner ruling) --------

test.describe("tabs keyboard", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
    await captureEvents(page);
  });

  test("roving tabindex after upgrade: only the active tab is tabbable", async ({ page }) => {
    await expect(page.locator("#bw-tab-itx-overview")).toHaveAttribute("tabindex", "0");
    await expect(page.locator("#bw-tab-itx-details")).toHaveAttribute("tabindex", "-1");
    await expect(page.locator("#bw-tab-itx-activity")).toHaveAttribute("tabindex", "-1");
    await expect(page.locator("#bw-tab-itx-overview")).toHaveAttribute("aria-selected", "true");
  });

  test("arrows move focus without activating; Enter activates (MANUAL)", async ({ page }) => {
    await page.locator("#bw-tab-itx-overview").focus();
    await page.keyboard.press("ArrowRight");
    expect(await activeId(page)).toBe("bw-tab-itx-details");
    // focus moved, selection did not (no server request per keypress)
    await expect(page.locator("#bw-tab-itx-details")).toHaveAttribute("aria-selected", "false");
    await expect(page.locator("#bw-tabpanel-itx-overview")).toBeVisible();
    await page.keyboard.press("Enter");
    await expect(page.locator("#bw-tab-itx-details")).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("#bw-tabpanel-itx-details")).toBeVisible();
    await expect(page.locator("#bw-tabpanel-itx-overview")).toBeHidden();
    const events = await recordedEvents(page);
    expect(events).toContainEqual({ type: "bw:tabs:change", detail: { id: "itx", key: "details" } });
    expect(events.filter((e) => e.type === "bw:tabs:change")).toHaveLength(1);
  });

  test("arrow focus wraps at both ends; Home and End jump", async ({ page }) => {
    await page.locator("#bw-tab-itx-overview").focus();
    await page.keyboard.press("ArrowLeft"); // wraps to the last
    expect(await activeId(page)).toBe("bw-tab-itx-activity");
    await page.keyboard.press("ArrowRight"); // wraps to the first
    expect(await activeId(page)).toBe("bw-tab-itx-overview");
    await page.keyboard.press("End");
    expect(await activeId(page)).toBe("bw-tab-itx-activity");
    await page.keyboard.press("Home");
    expect(await activeId(page)).toBe("bw-tab-itx-overview");
  });

  test("Tab from the active tab moves into the active panel (CBH-015)", async ({ page }) => {
    await page.locator("#bw-tab-itx-overview").focus();
    await page.keyboard.press("Tab");
    expect(await activeId(page)).toBe("bw-tabpanel-itx-overview");
  });
});

// --- modal keyboard map (AC-BW-080, BR-BW-JS-006/007) -------------------------

test.describe("modal keyboard", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
    await captureEvents(page);
  });

  test("open moves focus into the dialog and the trap wraps both directions", async ({ page }) => {
    await openModal(page);
    // focus lands on [data-bw-autofocus]
    await page.waitForFunction(() => document.activeElement?.id === "confirm-reset-input");
    // the trap never lets focus reach the page behind, in either direction
    for (let i = 0; i < 10; i += 1) {
      await page.keyboard.press("Tab");
      expect(
        await page.evaluate(() =>
          document.querySelector("#confirm-reset .bw-modal__panel").contains(document.activeElement),
        ),
      ).toBe(true);
    }
    for (let i = 0; i < 10; i += 1) {
      await page.keyboard.press("Shift+Tab");
      expect(
        await page.evaluate(() =>
          document.querySelector("#confirm-reset .bw-modal__panel").contains(document.activeElement),
        ),
      ).toBe(true);
    }
  });

  test("every dismissal route closes and returns focus to the invoker", async ({ page }) => {
    // route 1: Escape (CBH-001)
    await openModal(page);
    await page.waitForFunction(() => document.activeElement?.id === "confirm-reset-input");
    await page.keyboard.press("Escape");
    await expect(page.locator("#confirm-reset")).not.toHaveAttribute("data-bw-open", "");
    await page.waitForFunction(() => document.activeElement?.id === "open-confirm-modal");
    // route 2: the visible close control (BR-BW-JS-007)
    await openModal(page);
    await page.locator("#confirm-reset .bw-modal__close").click();
    await expect(page.locator("#confirm-reset")).not.toHaveAttribute("data-bw-open", "");
    await page.waitForFunction(() => document.activeElement?.id === "open-confirm-modal");
    // route 3: backdrop click (backdrop_dismiss=True on this modal, CBH-003)
    await openModal(page);
    await page.locator("#confirm-reset .bw-modal__scrim").click({ position: { x: 10, y: 10 } });
    await expect(page.locator("#confirm-reset")).not.toHaveAttribute("data-bw-open", "");
    await page.waitForFunction(() => document.activeElement?.id === "open-confirm-modal");
    // the three closes carried their documented reasons (AC-BW-087)
    const reasons = (await recordedEvents(page)).filter((e) => e.type === "bw:modal:close").map((e) => e.detail.reason);
    expect(reasons).toEqual(["escape", "close-button", "backdrop"]);
  });
});

// --- bw: event conventions (AC-BW-087, BR-BW-HTMX-004) ------------------------

test.describe("bw: events", () => {
  test("each component emits its documented events at the documented moments, and none before", async ({ page }) => {
    await boot(page);
    await captureEvents(page);
    // no interaction yet: no event has fired
    expect(await recordedEvents(page)).toEqual([]);
    // dropdown open + Escape close
    await ddTrigger(page).focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Escape");
    // tabs manual activation
    await page.locator("#bw-tab-itx-details").click();
    // modal open + Escape close
    await openModal(page);
    await page.keyboard.press("Escape");
    await expect(page.locator("#confirm-reset")).not.toHaveAttribute("data-bw-open", "");
    const events = await recordedEvents(page);
    expect(events.map((e) => e.type)).toEqual([
      "bw:dropdown:open",
      "bw:dropdown:close",
      "bw:tabs:change",
      "bw:modal:open",
      "bw:modal:close",
    ]);
    // the dropdown's instance id is generated (bw-dropdown-<n>) when the
    // markup carries none; open and close must agree on it
    expect(events[0].detail.id).toMatch(/^bw-dropdown/);
    expect(events[1].detail).toEqual(events[0].detail);
    expect(events[2].detail).toEqual({ id: "itx", key: "details" });
    expect(events[3].detail).toEqual({ id: "confirm-reset" });
    expect(events[4].detail).toEqual({ id: "confirm-reset", reason: "escape" });
  });
});

// --- axe on OPEN states, both themes (AC-BW-088) ------------------------------

for (const theme of THEMES) {
  test(`axe WCAG 2.2 AA on open dropdown, activated tab, open disclosure (${theme})`, async ({ page }) => {
    await boot(page, theme);
    await page.locator("#bw-tab-itx-details").click();
    await page.locator("details.bw-disclosure").first().locator("summary").click();
    // open the dropdown last: an outside pointerdown would dismiss it
    await ddTrigger(page).focus();
    await page.keyboard.press("Enter");
    await expect(dropdown(page)).toHaveAttribute("data-bw-open", "");
    await settleAnimations(page);
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });

  test(`axe WCAG 2.2 AA on the open modal over the populated page (${theme})`, async ({ page }) => {
    await boot(page, theme);
    await openModal(page);
    await page.waitForFunction(() => document.activeElement?.id === "confirm-reset-input");
    await settleAnimations(page);
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

// --- reduced motion (AC-BW-089, BR-BW-TOK-009) --------------------------------

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  const neutralised = (styles) => {
    // the global floor: animation-duration/transition-duration forced to
    // 0.001ms (DESIGN.md section 8.4), or no animation at all
    const animOk = styles.animationName === "none" || parseFloat(styles.animationDuration) <= 0.005;
    const transitionOk = parseFloat(styles.transitionDuration) <= 0.005;
    return animOk && transitionOk;
  };

  test("dropdown entrance is neutralised and the component stays operable", async ({ page }) => {
    await boot(page);
    await ddTrigger(page).focus();
    await page.keyboard.press("Enter");
    await expect(dropdown(page)).toHaveAttribute("data-bw-open", "");
    expect(await activeText(page)).toContain("New widget");
    const styles = await page.locator("nav.bw-dropdown__panel").evaluate((el) => {
      const cs = getComputedStyle(el);
      return {
        animationName: cs.animationName.split(",")[0].trim(),
        animationDuration: cs.animationDuration.split(",")[0].trim(),
        transitionDuration: cs.transitionDuration.split(",")[0].trim(),
      };
    });
    expect(neutralised(styles), JSON.stringify(styles)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(dropdown(page)).not.toHaveAttribute("data-bw-open", "");
  });

  test("modal enter and exit render instantly and stay fully operable", async ({ page }) => {
    await boot(page);
    await openModal(page);
    const styles = await page.locator("#confirm-reset .bw-modal__panel").evaluate((el) => {
      const cs = getComputedStyle(el);
      return {
        animationName: cs.animationName.split(",")[0].trim(),
        animationDuration: cs.animationDuration.split(",")[0].trim(),
        transitionDuration: cs.transitionDuration.split(",")[0].trim(),
      };
    });
    expect(neutralised(styles), JSON.stringify(styles)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(page.locator("#confirm-reset")).not.toHaveAttribute("data-bw-open", "");
    await page.waitForFunction(() => document.activeElement?.id === "open-confirm-modal");
  });

  test("disclosure still toggles with its grid animation neutralised", async ({ page }) => {
    await boot(page);
    const first = page.locator("details.bw-disclosure").first();
    await first.locator("summary").click();
    await expect(first).toHaveAttribute("open");
    const styles = await first.locator(".bw-disclosure__panel").evaluate((el) => {
      const cs = getComputedStyle(el);
      return {
        animationName: cs.animationName.split(",")[0].trim(),
        animationDuration: cs.animationDuration.split(",")[0].trim(),
        transitionDuration: cs.transitionDuration.split(",")[0].trim(),
      };
    });
    expect(neutralised(styles), JSON.stringify(styles)).toBe(true);
  });
});

// --- layout-shift discipline (AC-BW-094, BR-BW-HTMX-009) ----------------------

test.describe("layout shift", () => {
  test("the tabs lazy swap shifts nothing outside the swapped panel", async ({ page }) => {
    await boot(page);
    await armLayoutShiftObserver(page, ["#bw-tabpanel-itx-activity", "#bw-tabpanel-itx-overview", ".bw-tabs"]);
    // activate the lazy tab: the panel reveals its space-reserving skeleton,
    // htmx fires on revealed and swaps in the real content
    await page.locator("#bw-tab-itx-activity").click();
    await expect(page.getByText("Priya restocked Alpha")).toBeVisible();
    await page.waitForTimeout(400); // let any late layout-shift entries land
    expect(await outsideShiftScore(page)).toBe(0);
  });

  test("opening and closing the modal shifts nothing outside the modal root", async ({ page }) => {
    await boot(page);
    await armLayoutShiftObserver(page, ["#bw-modal-root"]);
    await openModal(page);
    await page.keyboard.press("Escape");
    await expect(page.locator("#confirm-reset")).not.toHaveAttribute("data-bw-open", "");
    await page.waitForTimeout(400);
    expect(await outsideShiftScore(page)).toBe(0);
  });
});
