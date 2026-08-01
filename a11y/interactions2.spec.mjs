// Interaction-set suite II (0.9.0): toast, combobox, dismissible.
//
// Two legs against the pre-rendered fixtures (a11y/generate_fixtures.py):
//   - the no-JS leg (javaScriptEnabled: false) proves the floors concretely:
//     the toast's floor is the messages banner alert (STA-008), the
//     combobox's floor is the operable native select (BR-BW-HTMX-006), and
//     the dismissible surfaces ship no dead close control;
//   - the JS leg loads toasts-js-<theme>.html / comboboxes-js-<theme>.html,
//     which boot Alpine + htmx from node_modules exactly as a host
//     application would (the FIXTURE owns Alpine.start(); brickwork never
//     does). Deliveries are REAL htmx swaps of static OOB fragments
//     (AC-BW-091), the combobox server filter is a REAL debounced hx-get
//     against a static option fragment (AC-BW-092), and axe runs on the
//     JS-only open states in both themes (the interactions.spec.mjs
//     precedent). Layout-shift discipline is AC-BW-094; the token-owned
//     motion assertion is AC-BW-090.
//
// Chromium blocks module imports and XHR from file:// by default, so this
// file's browser launches with --allow-file-access-from-files (scoped here;
// the axe.spec.mjs run is untouched).
//
// AC-BW-093 keyboard-map-to-assertion inventory (04-interfaces section 4b):
//   combobox closed: ArrowDown first-or-current, ArrowUp last,
//             Alt+ArrowDown without moving, typing opens ....... "closed-state openers"
//                                                            + "server mode debounces"
//   combobox open: ArrowDown/ArrowUp move active with wrap,
//             aria-activedescendant tracks ...................... "arrows move the active option"
//             Enter selects (single: select and close) .......... "Enter selects and closes"
//             Enter toggles and stays open (multiple) ........... "multiple mode"
//             Escape closes; when already closed clears query ... "Escape closes then clears"
//             Tab closes without selecting and continues ........ "Tab closes without selecting"
//             Home/End keep native caret behaviour .............. "Tab closes without selecting"
//   combobox multiple: Backspace with empty query removes chip .. "multiple mode"
//             chip remove control (enforced label, focus kept) .. "chip remove control"
//   combobox allow_create: non-matching query reveals the create
//             affordance as the final option, activating emits
//             bw:combobox:create { query } and creates nothing else "allow_create"
//   toast controls: close by pointer, Enter and Space ........... "close control dismisses"
//             the action link is an ordinary tab stop, Enter .... "action link"
//             timer pause on hover and focus-within ............. "timer pauses"
//   dismissible: close revealed at init, Enter activates ........ "close controls are revealed"

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const fx = (name) => pathToFileURL(join(FIXTURES, name)).href;
const THEMES = ["light", "dark"];
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

test.use({ launchOptions: { args: ["--allow-file-access-from-files"] } });

// --- helpers -----------------------------------------------------------------

async function bootToasts(page, theme = "light") {
  await page.goto(fx(`toasts-js-${theme}.html`));
  await page.waitForFunction(() => !!window.Alpine && !!window.htmx);
  // bwDismissible's reveal is the ready signal: the alert close control
  // exists only hidden until the components are running (upgrade-at-init).
  await expect(page.locator(".bw-alert__close")).toBeVisible();
}

async function bootComboboxes(page, theme = "light") {
  await page.goto(fx(`comboboxes-js-${theme}.html`));
  await page.waitForFunction(() => !!window.Alpine && !!window.htmx);
  // bwCombobox's handover is the ready signal: the enhanced field is only
  // revealed (and the floor select only hidden) once init has run.
  await expect(page.locator(".bw-combobox__field").first()).toBeVisible();
  await expect(page.locator("#id_colour")).toBeHidden();
}

const TOAST_EVENTS = ["bw:toast:show", "bw:toast:dismiss", "bw:dismiss"];
const COMBOBOX_EVENTS = ["bw:combobox:open", "bw:combobox:close", "bw:combobox:select", "bw:combobox:create"];

async function captureEvents(page, names) {
  await page.evaluate((eventNames) => {
    window.__bw = [];
    for (const name of eventNames) {
      window.addEventListener(name, (event) => {
        window.__bw.push({ type: event.type, detail: event.detail ?? null, at: performance.now() });
      });
    }
  }, names);
}

const recordedEvents = (page) => page.evaluate(() => window.__bw);
const activeId = (page) => page.evaluate(() => document.activeElement?.id ?? "");

// The colour combobox (single, server filter) and the tags combobox
// (multiple, client filter, chips) by their enhanced inputs.
const colourRoot = (page) => page.locator(".bw-combobox", { has: page.locator("#id_colour_combobox") });
const tagsRoot = (page) => page.locator(".bw-combobox", { has: page.locator("#id_tags_combobox") });

// Deliver a toast through the REAL wired path: the delivery button's htmx
// GET fetches the intent's OOB fragment and htmx performs the swap-oob
// append into #bw-toast-region (plus the ordinary status-line main swap).
async function sendToast(page, intent) {
  const region = page.locator("#bw-toast-region");
  const before = await region.locator("[data-bw-toast]").count();
  // Keyboard activation: with a tall stack the fixed region can overlap
  // the delivery row, so a pointer click would hit a toast instead; Enter
  // on the focused button is the same native activation without the
  // hit-test, and htmx still cancels the native submit.
  await page.locator(`#toast-demo-form button[value="${intent}"]`).focus();
  await page.keyboard.press("Enter");
  await expect(region.locator("[data-bw-toast]")).toHaveCount(before + 1);
}

// Deliver a fragment that has no dedicated button (short/action) through
// htmx's own request pipeline; the response's OOB wrapper is processed
// exactly as for any htmx response.
function deliverFragment(page, file) {
  return page.evaluate(
    (name) => window.htmx.ajax("GET", `fragments/${name}`, { target: "#toast-demo-status", swap: "outerHTML" }),
    file,
  );
}

// The auto-dismiss duration override goes onto the PAGE as a style tag, so
// bwToast still discovers the duration via getComputedStyle on the token; a
// component that used its JS fallback constant instead would ignore this and
// only time out at 4000ms, failing the bounded expectations below (the
// AC token-read proof: override and observe).
async function overrideToastDuration(page, name, value) {
  await page.addStyleTag({ content: `#bw-toast-region { --bw-duration-toast-${name}: ${value}; }` });
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

// --- the no-JS floors (BR-BW-HTMX-001/006, STA-008) ---------------------------

test.describe("no-JS floors", () => {
  test.use({ javaScriptEnabled: false });

  for (const theme of THEMES) {
    test(`toast floor is the messages banner, never a toast (${theme})`, async ({ page }) => {
      await page.goto(fx(`toasts-flash-${theme}.html`));
      // the plain-POST redirect state: the same feedback as a banner alert
      await expect(page.locator(".bw-alert", { hasText: "Demo data saved." }).first()).toBeVisible();
      await expect(page.locator("[data-bw-toast]")).toHaveCount(0);
      // the shipped region is present (stable id, BR-BW-HTMX-005) but an
      // empty region paints nothing on the floor
      await expect(page.locator("#bw-toast-region")).toBeAttached();
      await expect(page.locator("#bw-toast-region")).toBeHidden();
      await expect(page.locator(".bw-toast-region__more")).toBeHidden();
    });

    test(`dismissible floor shows no dead close control (${theme})`, async ({ page }) => {
      await page.goto(fx(`toasts-${theme}.html`));
      await expect(page.locator("#dismissible-demo .bw-alert")).toBeVisible();
      await expect(page.locator("#dismissible-demo .bw-badge")).toBeVisible();
      // both close controls ship WITH the hidden attribute; only init reveals
      const closes = page.locator("[data-bw-dismiss]");
      await expect(closes).toHaveCount(2);
      for (const close of await closes.all()) {
        await expect(close).toBeHidden();
      }
    });

    test(`combobox floor is the operable native select; the enhanced field stays hidden (${theme})`, async ({ page }) => {
      await page.goto(fx(`comboboxes-${theme}.html`));
      // the floor select IS the form control and works natively
      const colour = page.locator("select#id_colour");
      await expect(colour).toBeVisible();
      await colour.selectOption("green");
      await expect(colour).toHaveValue("green");
      const tags = page.locator("select#id_tags");
      await expect(tags).toBeVisible();
      await expect(tags).toHaveAttribute("multiple", "");
      // the enhanced chrome (combobox role set included) stays inert inside
      // its hidden wrapper; aria-activedescendant only ever arrives at init
      for (const field of await page.locator(".bw-combobox__field").all()) {
        await expect(field).toBeHidden();
      }
      for (const input of await page.locator('[role="combobox"]').all()) {
        await expect(input).toBeHidden();
      }
      await expect(page.locator("[aria-activedescendant]")).toHaveCount(0);
    });
  }
});

// --- toast delivery (AC-BW-091, BR-BW-HTMX-007) -------------------------------

test.describe("toast delivery", () => {
  test.beforeEach(async ({ page }) => {
    await bootToasts(page);
    await captureEvents(page, TOAST_EVENTS);
  });

  test("a toast arrives via the OOB append into the region and announces politely", async ({ page }) => {
    await expect(page.locator("#bw-toast-region")).toHaveAttribute("aria-live", "polite");
    await sendToast(page, "success");
    // the wrapper landed inside the stable region and the toast entered
    const toast = page.locator("#bw-toast-region .bw-toast--success");
    await expect(toast).toHaveCount(1);
    await expect(toast).toHaveAttribute("data-bw-visible", "");
    // the ordinary main swap rode alongside the OOB wrapper
    await expect(page.locator("#toast-demo-status")).toHaveText("Sent a success toast.");
    // the close control is always rendered (CBH-012)
    await expect(toast.locator(".bw-toast__close")).toBeVisible();
    const shows = (await recordedEvents(page)).filter((e) => e.type === "bw:toast:show");
    expect(shows).toHaveLength(1);
    expect(shows[0].detail.intent).toBe("success");
    expect(shows[0].detail.id).toBeTruthy();
  });

  test("there is no client-side creation API and events mint nothing", async ({ page }) => {
    // no creation function of any kind on the window (BR-BW-HTMX-007)
    const exposed = await page.evaluate(() =>
      ["showToast", "createToast", "addToast", "toast", "bwToast", "bwCreateToast"].filter((name) => name in window),
    );
    expect(exposed).toEqual([]);
    // the bw: events are notifications, never a creation path
    // (BR-BW-HTMX-004): forging them creates nothing
    await page.evaluate(() => {
      const detail = { id: "forged", intent: "success", message: "forged" };
      window.dispatchEvent(new CustomEvent("bw:toast:show", { detail }));
      document.dispatchEvent(new CustomEvent("bw:toast:create", { bubbles: true, detail }));
      document.getElementById("bw-toast-region").dispatchEvent(new CustomEvent("bw:toast:show", { detail }));
    });
    await page.waitForTimeout(250); // bounded settle: nothing may react
    await expect(page.locator("[data-bw-toast]")).toHaveCount(0);
  });

  test("arrival never steals focus", async ({ page }) => {
    await page.locator('#toast-demo-form button[value="info"]').focus();
    await deliverFragment(page, "toast-oob-info.html");
    await expect(page.locator("#bw-toast-region .bw-toast--info")).toHaveAttribute("data-bw-visible", "");
    // the activeElement is unchanged after the append (BR-BW-JS-006)
    expect(await page.evaluate(() => document.activeElement?.value)).toBe("info");
  });
});

// --- toast timers (WCAG 2.2.1, the 4b duration tokens) ------------------------

test.describe("toast timers", () => {
  test.beforeEach(async ({ page }) => {
    await bootToasts(page);
    await captureEvents(page, TOAST_EVENTS);
  });

  test("auto-dismiss reads the duration from the CSS token, not a JS constant", async ({ page }) => {
    await overrideToastDuration(page, "short", "120ms");
    // the override is visible exactly where the component reads the token
    expect(
      await page.evaluate(() =>
        getComputedStyle(document.getElementById("bw-toast-region"))
          .getPropertyValue("--bw-duration-toast-short")
          .trim(),
      ),
    ).toBe("120ms");
    await deliverFragment(page, "toast-oob-short.html");
    // gone well before the 4000ms JS fallback constant could ever fire
    await expect(page.locator("[data-bw-toast]")).toHaveCount(0, { timeout: 3000 });
    const events = await recordedEvents(page);
    const show = events.find((e) => e.type === "bw:toast:show");
    const dismiss = events.find((e) => e.type === "bw:toast:dismiss");
    expect(dismiss.detail.reason).toBe("timeout");
    expect(dismiss.at - show.at).toBeLessThan(2500);
  });

  test("the timer pauses on hover and on focus-within, then resumes", async ({ page }) => {
    await overrideToastDuration(page, "short", "800ms");
    await deliverFragment(page, "toast-oob-short.html");
    const toast = page.locator("[data-bw-toast]");
    await expect(toast).toHaveAttribute("data-bw-visible", "");
    await toast.hover();
    // paused is public state (BR-BW-JS-004); read it through Alpine
    await page.waitForFunction(() => window.Alpine.$data(document.querySelector("[data-bw-toast]")).paused === true);
    await page.waitForTimeout(1300); // well past the 800ms duration
    await expect(toast).toHaveCount(1); // hover held it (WCAG 2.2.1)
    // focus-within takes over the pause before the pointer leaves
    await toast.locator(".bw-toast__close").focus();
    await page.mouse.move(0, 0);
    await page.waitForFunction(() => window.Alpine.$data(document.querySelector("[data-bw-toast]")).paused === true);
    await page.waitForTimeout(1100);
    await expect(toast).toHaveCount(1); // focus-within held it
    // releasing focus resumes from the REMAINING time and it times out
    await page.evaluate(() => document.activeElement.blur());
    await expect(page.locator("[data-bw-toast]")).toHaveCount(0, { timeout: 3000 });
    expect((await recordedEvents(page)).find((e) => e.type === "bw:toast:dismiss").detail.reason).toBe("timeout");
  });

  test("persistent never auto-dismisses within the observation window", async ({ page }) => {
    await deliverFragment(page, "toast-oob-success.html"); // duration persistent
    const toast = page.locator("[data-bw-toast]");
    await expect(toast).toHaveAttribute("data-bw-visible", "");
    await page.waitForTimeout(1500); // bounded observation window
    await expect(toast).toHaveCount(1);
    expect((await recordedEvents(page)).filter((e) => e.type === "bw:toast:dismiss")).toEqual([]);
  });
});

// --- toast controls and the stack (CBH-011/012, AC-BW-093) --------------------

test.describe("toast controls", () => {
  test.beforeEach(async ({ page }) => {
    await bootToasts(page);
    await captureEvents(page, TOAST_EVENTS);
  });

  test('the close control dismisses with reason "dismiss" by pointer, Enter and Space', async ({ page }) => {
    await sendToast(page, "success");
    await page.locator(".bw-toast__close").click();
    await expect(page.locator("[data-bw-toast]")).toHaveCount(0);
    await sendToast(page, "info");
    await page.locator(".bw-toast__close").focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("[data-bw-toast]")).toHaveCount(0);
    await sendToast(page, "warning");
    await page.locator(".bw-toast__close").focus();
    await page.keyboard.press("Space");
    await expect(page.locator("[data-bw-toast]")).toHaveCount(0);
    // dismissing from inside never drops focus to <body> (BR-BW-JS-006)
    expect(await page.evaluate(() => document.activeElement !== document.body)).toBe(true);
    const reasons = (await recordedEvents(page))
      .filter((e) => e.type === "bw:toast:dismiss")
      .map((e) => e.detail.reason);
    expect(reasons).toEqual(["dismiss", "dismiss", "dismiss"]);
  });

  test("the action link is an ordinary tab stop and Enter activates it", async ({ page }) => {
    await deliverFragment(page, "toast-oob-action.html");
    const toast = page.locator("#toast-with-action");
    await expect(toast).toHaveAttribute("data-bw-visible", "");
    const action = toast.locator(".bw-toast__action");
    await expect(action).toHaveText("View widgets");
    // an ordinary tab stop: Tab continues from the action to the close
    await action.focus();
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => document.activeElement?.className ?? "")).toContain("bw-toast__close");
    // Enter activates the link (no shortcuts, no interception)
    await action.focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/#toast-action-target$/);
    await expect(toast).toHaveCount(1); // activating the action is not a dismissal
  });

  test('the stack collapses beyond three with "+N more" and expands on demand', async ({ page }) => {
    for (const intent of ["success", "info", "warning", "danger"]) {
      await sendToast(page, intent);
    }
    const toasts = page.locator("#bw-toast-region [data-bw-toast]");
    await expect(toasts).toHaveCount(4);
    // afterbegin prepends: newest first, and only danger carries role=alert
    await expect(toasts.first()).toHaveClass(/bw-toast--danger/);
    await expect(toasts.first()).toHaveAttribute("role", "alert");
    expect(await toasts.nth(1).getAttribute("role")).toBeNull();
    // the three newest stay visible; the oldest hides behind the control
    await expect(toasts.nth(0)).toBeVisible();
    await expect(toasts.nth(1)).toBeVisible();
    await expect(toasts.nth(2)).toBeVisible();
    await expect(toasts.nth(3)).toBeHidden();
    await expect(toasts.nth(3)).toHaveClass(/bw-toast--success/);
    const more = page.locator(".bw-toast-region__more");
    await expect(more).toBeVisible();
    await expect(more.locator("[data-bw-toast-more-count]")).toHaveText("1");
    // expanding reveals every toast and hands focus to the revealed one
    // (the activated control hides, so focus must not drop, BR-BW-JS-006)
    await more.click();
    for (let i = 0; i < 4; i += 1) {
      await expect(toasts.nth(i)).toBeVisible();
    }
    await expect(more).toBeHidden();
    expect(await page.evaluate(() => document.activeElement?.closest("[data-bw-toast]")?.className ?? "")).toContain(
      "bw-toast--success",
    );
    // a further arrival never re-collapses the stack under the user
    await deliverFragment(page, "toast-oob-action.html");
    await expect(toasts).toHaveCount(5);
    for (let i = 0; i < 5; i += 1) {
      await expect(toasts.nth(i)).toBeVisible();
    }
    await expect(more).toBeHidden();
  });

  test("dismissal drains the overflow and prunes emptied delivery wrappers", async ({ page }) => {
    for (const intent of ["success", "info", "warning", "danger"]) {
      await sendToast(page, intent);
    }
    await expect(page.locator(".bw-toast-region__more")).toBeVisible();
    await page.locator("#bw-toast-region [data-bw-toast]").first().locator(".bw-toast__close").click();
    await expect(page.locator("#bw-toast-region [data-bw-toast]")).toHaveCount(3);
    // back at the threshold: the overflow control disarms, everything shows
    await expect(page.locator(".bw-toast-region__more")).toBeHidden();
    for (const toast of await page.locator("#bw-toast-region [data-bw-toast]").all()) {
      await expect(toast).toBeVisible();
    }
    // the dismissed toast's OOB wrapper was pruned: no inert delivery divs
    expect(
      await page.evaluate(
        () =>
          Array.from(document.getElementById("bw-toast-region").children).filter(
            (child) =>
              !child.hasAttribute("data-bw-toast") &&
              !child.classList.contains("bw-toast-region__more") &&
              !child.querySelector("[data-bw-toast]"),
          ).length,
      ),
    ).toBe(0);
  });
});

// --- combobox keyboard map (AC-BW-092/093, CBH-018..022) ----------------------

test.describe("combobox keyboard", () => {
  test.beforeEach(async ({ page }) => {
    await bootComboboxes(page);
    await captureEvents(page, COMBOBOX_EVENTS);
  });

  test("closed-state openers: ArrowDown first, ArrowUp last, Alt+ArrowDown without moving", async ({ page }) => {
    const root = colourRoot(page);
    const input = page.locator("#id_colour_combobox");
    await input.focus();
    await page.keyboard.press("ArrowDown");
    await expect(root).toHaveAttribute("data-bw-open", "");
    await expect(input).toHaveAttribute("aria-expanded", "true");
    await expect(input).toHaveAttribute("aria-activedescendant", "bw-listbox-id_colour-opt-0");
    await expect(page.locator("#bw-listbox-id_colour-opt-0")).toHaveAttribute("data-bw-active", "");
    await page.keyboard.press("Escape");
    await expect(root).not.toHaveAttribute("data-bw-open", "");
    await expect(input).toHaveAttribute("aria-expanded", "false");
    await page.keyboard.press("ArrowUp");
    await expect(root).toHaveAttribute("data-bw-open", "");
    await expect(input).toHaveAttribute("aria-activedescendant", "bw-listbox-id_colour-opt-3");
    await page.keyboard.press("Escape");
    await page.keyboard.press("Alt+ArrowDown");
    await expect(root).toHaveAttribute("data-bw-open", "");
    expect(await input.getAttribute("aria-activedescendant")).toBeNull();
    // focus never left the input: options are aria-activedescendant
    // targets, never tab stops or focus targets
    expect(await activeId(page)).toBe("id_colour_combobox");
    expect((await recordedEvents(page)).filter((e) => e.type === "bw:combobox:open")).toHaveLength(3);
  });

  test("arrows move the active option with wrap; aria-activedescendant tracks every move", async ({ page }) => {
    const input = page.locator("#id_colour_combobox");
    await input.focus();
    await page.keyboard.press("ArrowDown"); // open, opt-0 active
    for (const [key, suffix] of [
      ["ArrowDown", "opt-1"],
      ["ArrowDown", "opt-2"],
      ["ArrowDown", "opt-3"],
      ["ArrowDown", "opt-0"], // wraps forward
      ["ArrowUp", "opt-3"], // wraps back
    ]) {
      await page.keyboard.press(key);
      await expect(input).toHaveAttribute("aria-activedescendant", `bw-listbox-id_colour-${suffix}`);
      await expect(page.locator(`#bw-listbox-id_colour-${suffix}`)).toHaveAttribute("data-bw-active", "");
    }
    // exactly one option carries the active marker at any moment
    expect(await page.locator("#bw-listbox-id_colour [data-bw-active]").count()).toBe(1);
  });

  test("Enter selects and closes (single); the floor select mirrors; reopening resumes on the selection", async ({ page }) => {
    const root = colourRoot(page);
    const input = page.locator("#id_colour_combobox");
    // the enhanced input never joins the form submission (name=q, form="")
    await expect(input).toHaveAttribute("form", "");
    // init reflected the floor's CURRENT selection into the input (a native
    // single select always has a value; here its first option, Red)
    await expect(input).toHaveValue("Red");
    await expect(page.locator("#id_colour")).toHaveValue("red");
    await input.focus();
    await page.keyboard.press("ArrowDown"); // open, Red active
    await page.keyboard.press("ArrowDown"); // Green
    await page.keyboard.press("Enter");
    await expect(root).not.toHaveAttribute("data-bw-open", "");
    await expect(input).toHaveValue("Green");
    // the floor select stays the submitted control and carries the state
    await expect(page.locator("#id_colour")).toHaveValue("green");
    const select = (await recordedEvents(page)).find((e) => e.type === "bw:combobox:select");
    expect(select.detail).toEqual({ value: "green", label: "Green" });
    // ArrowDown reopens with the CURRENT selection active, not the first
    await page.keyboard.press("ArrowDown");
    await expect(input).toHaveAttribute("aria-activedescendant", "bw-listbox-id_colour-opt-1");
    await expect(page.locator("#bw-listbox-id_colour-opt-1")).toHaveAttribute("aria-selected", "true");
  });

  test("Escape closes; Escape when already closed clears the query but not the selection", async ({ page }) => {
    const root = colourRoot(page);
    const input = page.locator("#id_colour_combobox");
    await input.focus();
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter"); // select Green
    await page.keyboard.press("ArrowDown"); // reopen
    await page.keyboard.press("Escape");
    await expect(root).not.toHaveAttribute("data-bw-open", "");
    await expect(input).toHaveValue("Green"); // closing does not clear
    await page.keyboard.press("Escape"); // already closed: clears the query
    await expect(input).toHaveValue("");
    // the query is not the selection: form state lives on the floor
    await expect(page.locator("#id_colour")).toHaveValue("green");
    expect((await recordedEvents(page)).filter((e) => e.type === "bw:combobox:close")).toHaveLength(2);
  });

  test("Tab closes without selecting and continues; Home and End keep the native caret", async ({ page }) => {
    const root = colourRoot(page);
    const input = page.locator("#id_colour_combobox");
    await input.focus();
    await page.keyboard.press("ArrowDown"); // open, Red active
    await page.keyboard.press("Tab");
    await expect(root).not.toHaveAttribute("data-bw-open", "");
    expect(await activeId(page)).not.toBe("id_colour_combobox"); // the sequence continued
    expect((await recordedEvents(page)).filter((e) => e.type === "bw:combobox:select")).toEqual([]);
    // Home/End: native caret movement, the popup and active option
    // untouched. The input already holds the init-reflected selection label
    // ("Red"), so typing APPENDS and End lands on the full value's length.
    await input.focus();
    await input.pressSequentially("abc");
    await expect(root).toHaveAttribute("data-bw-open", ""); // typing opens
    await expect(input).toHaveValue(/abc$/);
    await page.keyboard.press("Home");
    expect(await page.evaluate(() => document.getElementById("id_colour_combobox").selectionStart)).toBe(0);
    await expect(root).toHaveAttribute("data-bw-open", "");
    await page.keyboard.press("End");
    expect(
      await page.evaluate(() => {
        const el = document.getElementById("id_colour_combobox");
        return el.selectionStart === el.value.length && el.value.length > 0;
      }),
    ).toBe(true);
  });

  test("server mode debounces to exactly one request and dims the listbox in flight (AC-BW-092)", async ({ page }) => {
    const root = colourRoot(page);
    await page.evaluate(() => {
      window.__requests = [];
      window.__inflight = null;
      document.addEventListener("htmx:beforeRequest", () => window.__requests.push(performance.now()));
      // htmx applies the hx-indicator class before send: capture the
      // in-flight marker synchronously (a file:// response is too fast to
      // sample afterwards)
      document.addEventListener("htmx:beforeSend", () => {
        const listbox = document.getElementById("bw-listbox-id_colour");
        window.__inflight = { marked: listbox.classList.contains("htmx-request") };
      });
    });
    const input = page.locator("#id_colour_combobox");
    await input.focus();
    // three keystrokes inside one --bw-debounce-search window
    await input.pressSequentially("gre", { delay: 40 });
    await expect(root).toHaveAttribute("data-bw-open", ""); // typing opens
    // the debounced request lands and the option-list swap replaces the list
    await expect(page.locator("#bw-listbox-id_colour .bw-combobox__option")).toHaveText(["Green"]);
    await page.waitForTimeout(700); // an undebounced extra request would land here
    expect(await page.evaluate(() => window.__requests.length)).toBe(1);
    expect(await page.evaluate(() => window.__inflight?.marked)).toBe(true);
    // the empty-message row is kept across the swap (CMP-029)
    expect(await page.locator("#bw-listbox-id_colour .bw-combobox__empty").count()).toBe(1);
    // the in-flight marker drives the standard dim treatment (STA-006):
    // probe with transitions off so the computed value is the settled one
    const dim = await page.evaluate(() => {
      const listbox = document.getElementById("bw-listbox-id_colour");
      listbox.style.transition = "none";
      listbox.classList.add("htmx-request");
      const opacity = getComputedStyle(listbox).opacity;
      listbox.classList.remove("htmx-request");
      listbox.style.transition = "";
      return { opacity, token: getComputedStyle(listbox).getPropertyValue("--bw-htmx-indicator-opacity").trim() };
    });
    expect(parseFloat(dim.opacity)).toBeLessThan(1);
    expect(parseFloat(dim.opacity)).toBeCloseTo(parseFloat(dim.token), 2);
  });

  test("multiple mode: chips render from the floor, Enter toggles and stays open, Backspace removes the last chip", async ({ page }) => {
    const root = tagsRoot(page);
    const input = page.locator("#id_tags_combobox");
    // chips rehydrated from the floor's initial selections at init
    await expect(root.locator(".bw-combobox__chip")).toHaveText([/Alpha/, /Beta/]);
    await expect(page.locator("#id_tags")).toHaveValues(["alpha", "beta"]);
    await expect(page.locator("#bw-listbox-id_tags")).toHaveAttribute("aria-multiselectable", "true");
    await input.focus();
    await page.keyboard.press("ArrowDown"); // opens with the current selection (Alpha) active
    await expect(root).toHaveAttribute("data-bw-open", "");
    await expect(input).toHaveAttribute("aria-activedescendant", "bw-listbox-id_tags-opt-0");
    // Enter on a selected option toggles it OFF and the popup stays open
    await page.keyboard.press("Enter");
    await expect(root).toHaveAttribute("data-bw-open", "");
    await expect(root.locator(".bw-combobox__chip")).toHaveText([/Beta/]);
    await expect(page.locator("#id_tags")).toHaveValues(["beta"]);
    // arrow on to Gamma and toggle it ON: still open, floor mirrors
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    await expect(input).toHaveAttribute("aria-activedescendant", "bw-listbox-id_tags-opt-2");
    await page.keyboard.press("Enter");
    await expect(root).toHaveAttribute("data-bw-open", "");
    await expect(root.locator(".bw-combobox__chip")).toHaveText([/Beta/, /Gamma/]);
    await expect(page.locator("#id_tags")).toHaveValues(["beta", "gamma"]);
    const select = (await recordedEvents(page)).find((e) => e.type === "bw:combobox:select");
    expect(select.detail).toEqual({ value: "gamma", label: "Gamma" });
    await expect(page.locator("#bw-listbox-id_tags-opt-2")).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("#bw-listbox-id_tags-opt-0")).toHaveAttribute("aria-selected", "false");
    // Backspace with an empty query removes the LAST chip
    await page.keyboard.press("Backspace");
    await expect(root.locator(".bw-combobox__chip")).toHaveText([/Beta/]);
    await expect(page.locator("#id_tags")).toHaveValues(["beta"]);
  });

  test("chip remove control: enforced translated label, pointer removal, focus stays on the input", async ({ page }) => {
    const root = tagsRoot(page);
    const beta = root.locator(".bw-combobox__chip", { hasText: "Beta" });
    const remove = beta.locator(".bw-combobox__chip-remove");
    // the per-chip accessible name is enforced (ICO-008)
    await expect(remove).toHaveAttribute("aria-label", "Remove Beta");
    await remove.click();
    await expect(root.locator(".bw-combobox__chip")).toHaveText([/Alpha/]);
    await expect(page.locator("#id_tags")).toHaveValues(["alpha"]);
    // removal never drops focus (BR-BW-JS-006)
    expect(await activeId(page)).toBe("id_tags_combobox");
  });

  test("client mode filters without requests and reveals the empty message", async ({ page }) => {
    const root = tagsRoot(page);
    const input = page.locator("#id_tags_combobox");
    await page.evaluate(() => {
      window.__requests = [];
      document.addEventListener("htmx:beforeRequest", () => window.__requests.push(1));
    });
    await input.focus();
    await input.pressSequentially("al");
    await expect(root).toHaveAttribute("data-bw-open", ""); // typing opens
    await expect(page.locator("#bw-listbox-id_tags-opt-0")).toBeVisible(); // Alpha
    await expect(page.locator("#bw-listbox-id_tags-opt-1")).toBeHidden(); // Beta
    await expect(page.locator("#bw-listbox-id_tags-opt-2")).toBeHidden(); // Gamma
    await expect(root.locator(".bw-combobox__empty")).toBeHidden();
    await input.pressSequentially("zzz"); // no match at all
    await expect(page.locator("#bw-listbox-id_tags-opt-0")).toBeHidden();
    await expect(root.locator(".bw-combobox__empty")).toBeVisible(); // CMP-029
    await page.waitForTimeout(500); // a wrongly scheduled server call would land here
    expect(await page.evaluate(() => window.__requests.length)).toBe(0);
  });

  test("allow_create: a non-matching query reveals the create affordance as the final option; activating it emits bw:combobox:create and creates nothing else (CBH-021)", async ({ page }) => {
    const root = page.locator(".bw-combobox", { has: page.locator("#id_skills_combobox") });
    const input = page.locator("#id_skills_combobox");
    const listbox = page.locator("#bw-listbox-id_skills");
    const create = page.locator("#bw-listbox-id_skills-create");
    // an empty query never reveals the affordance; single mode reflects the
    // floor's current (first-option) selection into the input at init, so
    // it is cleared first (fill replaces, pressSequentially would append)
    await input.focus();
    await expect(create).toBeHidden();
    await input.fill("");
    // a query nothing matches reveals it, filled with the query, as the
    // FINAL option in the listbox
    await input.pressSequentially("Rust");
    await expect(root).toHaveAttribute("data-bw-open", "");
    await expect(create).toBeVisible();
    await expect(create.locator("[data-bw-combobox-create-query]")).toHaveText("Rust");
    const optionIds = await listbox.locator('[role="option"]:visible').evaluateAll((els) => els.map((el) => el.id));
    expect(optionIds[optionIds.length - 1]).toBe("bw-listbox-id_skills-create");
    // activating it emits bw:combobox:create with { query } and mutates
    // neither the floor select's options nor its current value: no option
    // is created, no selection changes (the floor still carries whatever
    // it held before the affordance was activated)
    const before = await page.evaluate(() => document.getElementById("id_skills").outerHTML);
    const [event] = await Promise.all([
      page.evaluate(
        () =>
          new Promise((resolve) => {
            window.addEventListener("bw:combobox:create", (e) => resolve(e.detail), { once: true });
          }),
      ),
      create.click(),
    ]);
    expect(event).toEqual({ query: "Rust" });
    expect(await page.evaluate(() => document.getElementById("id_skills").outerHTML)).toBe(before);
  });
});

// --- dismissible (04-interfaces 4b Dismissible section, CMP-010/012) ----------

test.describe("dismissible", () => {
  test.beforeEach(async ({ page }) => {
    await bootToasts(page);
    await captureEvents(page, ["bw:dismiss"]);
  });

  test("close controls are revealed at init and dismissal removes the surface with bw:dismiss", async ({ page }) => {
    const alertClose = page.locator(".bw-alert__close");
    const badgeClose = page.locator(".bw-badge__close");
    await expect(alertClose).toBeVisible();
    await expect(badgeClose).toBeVisible();
    // pointer on the alert; keyboard (a native button, Enter) on the badge
    await alertClose.click();
    await expect(page.locator("#dismissible-demo .bw-alert")).toHaveCount(0);
    await badgeClose.focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("#dismissible-demo .bw-badge")).toHaveCount(0);
    const events = (await recordedEvents(page)).filter((e) => e.type === "bw:dismiss");
    expect(events).toHaveLength(2);
    for (const event of events) {
      expect(event.detail.id).toBeTruthy();
    }
  });

  test("focus returns to the previous focusable element when focus was inside", async ({ page }) => {
    await page.locator(".bw-alert__close").focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("#dismissible-demo .bw-alert")).toHaveCount(0);
    // the previous focusable in document order is the last delivery button
    expect(await page.evaluate(() => document.activeElement !== document.body)).toBe(true);
    expect(await page.evaluate(() => document.activeElement?.value)).toBe("danger");
  });
});

// --- reduced motion (BR-BW-TOK-009) -------------------------------------------

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  // The reducedMotion context option alone does not reliably reach a
  // file:// document's matchMedia/CSS evaluation in this Chromium build; an
  // explicit emulateMedia call is needed (the interactions.spec.mjs note).
  test.beforeEach(async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
  });

  test("dismissal removes instantly under reduced motion", async ({ page }) => {
    await bootToasts(page);
    // the global floor collapses the [data-bw-dismissing] exit to an
    // instant swap: probe the marked state's computed duration
    const styles = await page.locator("#dismissible-demo .bw-alert").evaluate((el) => {
      el.setAttribute("data-bw-dismissing", "");
      const duration = getComputedStyle(el).transitionDuration.split(",")[0].trim();
      el.removeAttribute("data-bw-dismissing");
      return duration;
    });
    expect(parseFloat(styles)).toBeLessThanOrEqual(0.005);
    await page.locator(".bw-alert__close").click();
    await expect(page.locator("#dismissible-demo .bw-alert")).toHaveCount(0, { timeout: 700 });
  });

  test("toast timers still run under reduced motion", async ({ page }) => {
    await bootToasts(page);
    await captureEvents(page, TOAST_EVENTS);
    await overrideToastDuration(page, "short", "120ms");
    await deliverFragment(page, "toast-oob-short.html");
    // the motion is neutralised but the wall-clock timer is unchanged
    await expect(page.locator("[data-bw-toast]")).toHaveCount(0, { timeout: 3000 });
    expect((await recordedEvents(page)).find((e) => e.type === "bw:toast:dismiss").detail.reason).toBe("timeout");
  });
});

// --- axe on the JS-only open states, both themes (AC-BW-088 discipline) -------

for (const theme of THEMES) {
  test(`axe WCAG 2.2 AA on the toast stack, collapsed and expanded (${theme})`, async ({ page }) => {
    await bootToasts(page, theme);
    for (const intent of ["success", "info", "warning", "danger"]) {
      await sendToast(page, intent);
    }
    await expect(page.locator(".bw-toast-region__more")).toBeVisible();
    await settleAnimations(page);
    let results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
    // expanded: every intent visible, the overflow control retired
    await page.locator(".bw-toast-region__more").click();
    await expect(page.locator("#bw-toast-region [data-bw-toast]").nth(3)).toBeVisible();
    await settleAnimations(page);
    results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });

  test(`axe WCAG 2.2 AA on the open combobox with active option and chips (${theme})`, async ({ page }) => {
    await bootComboboxes(page, theme);
    await page.locator("#id_colour_combobox").focus();
    await page.keyboard.press("ArrowDown"); // open with the first option active
    await expect(colourRoot(page)).toHaveAttribute("data-bw-open", "");
    await expect(page.locator("#id_colour_combobox")).toHaveAttribute(
      "aria-activedescendant",
      "bw-listbox-id_colour-opt-0",
    );
    await settleAnimations(page);
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

// --- layout-shift discipline (AC-BW-094, BR-BW-HTMX-009) ----------------------

test.describe("layout shift", () => {
  test("appending a toast shifts nothing outside the region", async ({ page }) => {
    await bootToasts(page);
    // let the page's own post-boot settle finish (htmx injects its
    // indicator stylesheet at init and the document reflows once) before
    // arming, so the measurement isolates the append itself
    await page.waitForTimeout(400);
    await armLayoutShiftObserver(page, ["#bw-toast-region"]);
    // the canonical OOB-only delivery (hx-swap none: the response is
    // processed for its OOB wrapper alone), so the measurement isolates the
    // toast append itself; the demo form's status-line main swap is that
    // form's own reflow, not the append this AC governs
    await page.evaluate(() =>
      window.htmx.ajax("GET", "fragments/toast-oob-info.html", { target: "#toast-demo-status", swap: "none" }),
    );
    await expect(page.locator("#bw-toast-region .bw-toast--info")).toHaveAttribute("data-bw-visible", "");
    await settleAnimations(page);
    await page.waitForTimeout(400); // let any late layout-shift entries land
    expect(await outsideShiftScore(page)).toBe(0);
  });

  test("the option-list swap shifts nothing outside the combobox", async ({ page }) => {
    await bootComboboxes(page);
    await armLayoutShiftObserver(page, [".bw-combobox"]);
    const input = page.locator("#id_colour_combobox");
    await input.focus();
    await input.pressSequentially("gre", { delay: 40 });
    await expect(page.locator("#bw-listbox-id_colour .bw-combobox__option")).toHaveText(["Green"]);
    await page.waitForTimeout(400);
    expect(await outsideShiftScore(page)).toBe(0);
  });
});

// --- AC-BW-090: motion timing stays token-owned in the new CSS ----------------

// A raw duration or easing literal is only ever legitimate as the VALUE of a
// --bw-* custom property (the token definition itself); every use site must
// go through var(). The built stylesheet is minified with comments stripped,
// so the built scan scopes by SELECTOR (the toast/combobox/dismissible class
// families) while the authored source scan scopes by the section comment
// banners the task names. ADJUSTMENT POINT: if the CSS lane renames the
// section banners, update the two markers in the source-scan test below.

const RAW_TIME = /(^|[\s(,:])\d*\.?\d+(ms|s)(?![\w-])/;

function rawMotionLiterals(cssBody) {
  const offenders = [];
  for (const declaration of cssBody.split(";")) {
    const colon = declaration.indexOf(":");
    if (colon === -1) continue;
    const property = declaration.slice(0, colon).trim();
    const value = declaration.slice(colon + 1);
    if (property.startsWith("--")) continue; // token definitions ARE the literals
    if (RAW_TIME.test(value) || value.includes("cubic-bezier(")) {
      offenders.push(declaration.trim());
    }
  }
  return offenders;
}

test.describe("AC-BW-090 token-owned motion", () => {
  test("the built brickwork.css toast/combobox/dismissible rules carry no raw ms or cubic-bezier literals", async () => {
    const css = readFileSync(join(HERE, "..", "src/brickwork/static/brickwork/dist/brickwork.css"), "utf8");
    const scope = /bw-toast|bw-combobox|data-bw-dismissing|bw-badge__close/;
    const offenders = [];
    // innermost-block matching: rules inside @media resolve here too, and
    // keyframe step selectors (0%, to) never match the scope
    for (const match of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const [, selector, body] = match;
      if (!scope.test(selector)) continue;
      offenders.push(...rawMotionLiterals(body).map((decl) => `${selector.trim()} { ${decl} }`));
    }
    expect(offenders).toEqual([]);
  });

  test("the authored toast/combobox/dismissible sections carry no raw ms or cubic-bezier literals", async () => {
    const src = readFileSync(join(HERE, "..", "frontend/src/components.css"), "utf8");
    const start = src.indexOf("/* --- Toast region");
    const end = src.indexOf("/* --- Dark-theme resets");
    expect(start).toBeGreaterThan(-1); // banner markers: see the note above
    expect(end).toBeGreaterThan(start);
    const section = src.slice(start, end).replace(/\/\*[\s\S]*?\*\//g, "");
    expect(rawMotionLiterals(section)).toEqual([]);
  });
});
