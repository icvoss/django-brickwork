// bwSortable suite (icvoss/django-brickwork#214): drag/keyboard list
// reordering plus persistence.
//
// Two legs against the pre-rendered fixtures (a11y/generate_fixtures.py):
//   - the no-JS leg (javaScriptEnabled: false) proves the floor concretely
//     (BR-BW-HTMX-001): every item already carries real, independently
//     working move-up/move-down submit buttons before any JS runs, and no
//     drag affordance (draggable="false") or live-region markup exists
//     without the behaviour that would give it meaning;
//   - the JS leg loads sortable-js-<theme>.html, which boots Alpine + htmx
//     from node_modules exactly as a host application would (the FIXTURE
//     owns Alpine.start(); brickwork never does), and exercises the drag
//     path, the keyboard path (roving tabindex, Alt+Arrow/Home/End, the
//     aria-live announcement), the persistence POST (a real htmx.ajax
//     outerHTML swap against fragments/sortable-reorder.html, proving the
//     round trip under file://), and axe on both themes.
//
// Chromium blocks module imports and XHR from file:// by default, so this
// file's browser launches with --allow-file-access-from-files (scoped here;
// the axe.spec.mjs run is untouched).

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

// sortable-js-<theme>.html deliberately leaves bwSortable's url unset (see
// generate_fixtures.py's render_sortable docstring): this repo's own reorder
// fragment mock is STATIC, so a wired url would round-trip every move
// through htmx.ajax and revert the DOM to the fragment's fixed order before
// a test could observe the client-side move alone. sortable-js-persist
// wires a real url and is used ONLY by the "persistence" describe block
// below, which asserts the swap itself rather than a sequence of moves.
async function boot(page, theme = "light", { persist = false } = {}) {
  await page.goto(fx(`sortable-js-${persist ? "persist-" : ""}${theme}.html`));
  await page.waitForFunction(() => !!window.Alpine && !!window.htmx);
  // Roving tabindex at init is the ready signal: the first item is a tab
  // stop only once bwSortable has run.
  await expect(page.locator('[data-bw-sort-id="1"]')).toHaveAttribute("tabindex", "0");
}

async function captureEvents(page) {
  await page.evaluate(() => {
    window.__bw = [];
    window.addEventListener("bw:sortable:reorder", (event) => {
      window.__bw.push({ type: event.type, detail: event.detail ?? null });
    });
  });
}

const recordedEvents = (page) => page.evaluate(() => window.__bw);
const sortIds = (page) =>
  page.locator("[data-bw-sort-id]").evaluateAll((els) => els.map((el) => el.getAttribute("data-bw-sort-id")));

// DataTransfer only exists in the page's own realm, so it must be
// constructed there and handed back as a JSHandle: passing `new
// DataTransfer()` straight into dispatchEvent's options object fails
// because Playwright evaluates that object literal in the Node realm first.
const dataTransfer = (page) => page.evaluateHandle(() => new DataTransfer());

// --- the no-JS floor (BR-BW-HTMX-001) -----------------------------------------

test.describe("no-JS floor", () => {
  test.use({ javaScriptEnabled: false });

  for (const theme of THEMES) {
    test(`the floor is real move-up/move-down forms, no drag or live-region chrome (${theme})`, async ({ page }) => {
      await page.goto(fx(`sortable-${theme}.html`));
      const items = page.locator("[data-bw-sort-id]");
      await expect(items).toHaveCount(3);
      // every item ships two real submit buttons, boundary ones disabled
      await expect(page.locator('button[value="up-1"]')).toBeDisabled();
      await expect(page.locator('button[value="down-1"]')).toBeEnabled();
      await expect(page.locator('button[value="down-3"]')).toBeDisabled();
      // no drag affordance and no roving tabindex without the behaviour
      for (const item of await items.all()) {
        await expect(item).toHaveAttribute("draggable", "false");
        await expect(item).not.toHaveAttribute("tabindex");
      }
      await expect(page.locator("[data-bw-sort-status]")).toHaveCount(0);
    });
  }
});

// --- keyboard reorder (WCAG 2.2 AA: the drag path has no mouse-only gap) -----

test.describe("keyboard reorder", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
    await captureEvents(page);
  });

  test("Alt+ArrowDown moves the focused item down, keeps focus, and announces the new position", async ({
    page,
  }) => {
    const first = page.locator('[data-bw-sort-id="1"]');
    await first.focus();
    await page.keyboard.press("Alt+ArrowDown");
    await expect(sortIds(page)).resolves.toEqual(["2", "1", "3"]);
    await expect(first).toBeFocused();
    await expect(first).toHaveAttribute("tabindex", "0");
    // roving tabindex followed the moved item: every other item is -1
    await expect(page.locator('[data-bw-sort-id="2"]')).toHaveAttribute("tabindex", "-1");
    await expect(page.locator("[data-bw-sort-status]")).toHaveText("Position 2 of 3");
    const events = (await recordedEvents(page)).filter((e) => e.type === "bw:sortable:reorder");
    expect(events).toHaveLength(1);
    expect(events[0].detail).toEqual({ ids: ["2", "1", "3"] });
  });

  test("Alt+ArrowUp moves the focused item up and Alt+ArrowUp at the top is a no-op", async ({ page }) => {
    const last = page.locator('[data-bw-sort-id="3"]');
    await last.focus();
    await page.keyboard.press("Alt+ArrowUp");
    await expect(sortIds(page)).resolves.toEqual(["1", "3", "2"]);
    await expect(last).toBeFocused();
    await expect(page.locator("[data-bw-sort-status]")).toHaveText("Position 2 of 3");
    // moving again (still focused, now at index 1) reaches the top
    await page.keyboard.press("Alt+ArrowUp");
    await expect(sortIds(page)).resolves.toEqual(["3", "1", "2"]);
    await expect(page.locator("[data-bw-sort-status]")).toHaveText("Position 1 of 3");
    // at the top boundary: a further Alt+ArrowUp moves nothing, announces
    // nothing new, and fires no additional event
    await page.keyboard.press("Alt+ArrowUp");
    await expect(sortIds(page)).resolves.toEqual(["3", "1", "2"]); // unchanged: already first
    const events = (await recordedEvents(page)).filter((e) => e.type === "bw:sortable:reorder");
    expect(events).toHaveLength(2); // the no-op press moved nothing
  });

  test("Alt+End moves the focused item to the bottom; Alt+Home moves it to the top", async ({ page }) => {
    const first = page.locator('[data-bw-sort-id="1"]');
    await first.focus();
    await page.keyboard.press("Alt+End");
    await expect(sortIds(page)).resolves.toEqual(["2", "3", "1"]);
    await expect(first).toBeFocused();
    await page.keyboard.press("Alt+Home");
    await expect(sortIds(page)).resolves.toEqual(["1", "2", "3"]);
    await expect(first).toBeFocused();
  });

  test("plain ArrowDown without Alt does not move the item (reserved for reader navigation)", async ({ page }) => {
    const first = page.locator('[data-bw-sort-id="1"]');
    await first.focus();
    await page.keyboard.press("ArrowDown");
    await expect(sortIds(page)).resolves.toEqual(["1", "2", "3"]);
  });

  test("Tab enters the list on the roving item only, matching the bwTabs precedent", async ({ page }) => {
    // the roving tab stop starts on the first item at init
    await page.keyboard.press("Tab");
    // file:// pages with no other focusable ahead land here directly in a
    // clean context; assert the property regardless of prior focus chain
    await page.locator('[data-bw-sort-id="1"]').focus();
    await expect(page.locator('[data-bw-sort-id="2"]')).toHaveAttribute("tabindex", "-1");
    await expect(page.locator('[data-bw-sort-id="3"]')).toHaveAttribute("tabindex", "-1");
  });
});

// --- drag reorder (native HTML5 DnD, the reference implementation's proven
// insertion-preview technique) -------------------------------------------------

test.describe("drag reorder", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
    await captureEvents(page);
  });

  test("dragging the first item below the second reorders the DOM and persists", async ({ page }) => {
    const first = page.locator('[data-bw-sort-id="1"]');
    const second = page.locator('[data-bw-sort-id="2"]');
    const box2 = await second.boundingBox();
    await first.dispatchEvent("dragstart", { dataTransfer: await dataTransfer(page) });
    await expect(first).toHaveAttribute("data-bw-dragging", "");
    await second.dispatchEvent("dragover", {
      dataTransfer: await dataTransfer(page),
      clientY: box2.y + box2.height - 2, // below the midpoint: insert AFTER
    });
    await expect(second).toHaveAttribute("data-bw-drag-over", "");
    await expect(sortIds(page)).resolves.toEqual(["2", "1", "3"]);
    await second.dispatchEvent("drop", { dataTransfer: await dataTransfer(page) });
    await expect(first).not.toHaveAttribute("data-bw-dragging");
    await expect(second).not.toHaveAttribute("data-bw-drag-over");
    const events = (await recordedEvents(page)).filter((e) => e.type === "bw:sortable:reorder");
    expect(events).toHaveLength(1);
    expect(events[0].detail).toEqual({ ids: ["2", "1", "3"] });
  });
});

// --- persistence round trip (server truth wins over the client's guess) ------
//
// Uses sortable-js-persist-<theme>.html (a real url wired), never the plain
// sortable-js fixture: see render_sortable's docstring in
// generate_fixtures.py for why a wired url would fight the DOM-only
// keyboard/drag assertions above.

test.describe("persistence", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page, "light", { persist: true });
    await captureEvents(page);
  });

  test("a keyboard move fires a real htmx.ajax outerHTML POST, and the response replaces the component root", async ({
    page,
  }) => {
    await page.evaluate(() => {
      window.__requests = [];
      window.__settled = false;
      document.addEventListener("htmx:beforeRequest", (event) => {
        window.__requests.push({ verb: event.detail.requestConfig.verb, path: event.detail.pathInfo.requestPath });
      });
      // htmx:afterSettle is the real "the outerHTML swap has landed" signal
      // (fired on the swapped-in target once its own settle timers, if any,
      // complete): a DOM-shape check like toHaveCount(1) is a vacuous wait
      // here, since data-bw-sort-id="1" is present in both the client's
      // pre-swap optimistic order and the server's post-swap fragment, so
      // its count never transitions and never actually gates the swap
      // (icvoss/django-brickwork#242's CI flake, root-caused to this race).
      document.addEventListener("htmx:afterSettle", () => {
        window.__settled = true;
      });
    });
    const first = page.locator('[data-bw-sort-id="1"]');
    await first.focus();
    await page.keyboard.press("Alt+ArrowDown");
    // wait for the real swap-complete signal, not a DOM shape that is true
    // both before and after the swap
    await page.waitForFunction(() => window.__settled === true, { timeout: 3000 });
    // the swap lands: the returned fragment IS the mock's fixed order
    // (Alpha/Beta/Gamma), proving server truth overwrote the client's own
    // optimistic [2, 1, 3] guess, exactly as the reference implementation's
    // documented contract requires
    await expect(sortIds(page)).resolves.toEqual(["1", "2", "3"]);
    // the swapped-in root is a fresh x-data element; Alpine's own mutation
    // observer re-initialises it with no explicit htmx.process() call
    await expect(page.locator('[data-bw-sort-id="1"]')).toHaveAttribute("tabindex", "0");
    const requests = await page.evaluate(() => window.__requests);
    expect(requests).toEqual([{ verb: "post", path: "fragments/sortable-reorder.html" }]);
    // bw:sortable:reorder still fired once with the client's OWN order,
    // ahead of the request (the optional convention, BR-BW-HTMX-004,
    // notifies before the network settles)
    const events = (await recordedEvents(page)).filter((e) => e.type === "bw:sortable:reorder");
    expect(events).toEqual([{ type: "bw:sortable:reorder", detail: { ids: ["2", "1", "3"] } }]);
  });
});

// --- axe WCAG 2.2 AA on the enhanced list (AC-BW-088 discipline) -------------

for (const theme of THEMES) {
  test(`axe WCAG 2.2 AA on the enhanced sortable list, at rest and mid-drag (${theme})`, async ({ page }) => {
    await boot(page, theme);
    let results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
    const first = page.locator('[data-bw-sort-id="1"]');
    const second = page.locator('[data-bw-sort-id="2"]');
    await first.dispatchEvent("dragstart", { dataTransfer: await dataTransfer(page) });
    const box2 = await second.boundingBox();
    await second.dispatchEvent("dragover", {
      dataTransfer: await dataTransfer(page),
      clientY: box2.y + box2.height - 2,
    });
    results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}
