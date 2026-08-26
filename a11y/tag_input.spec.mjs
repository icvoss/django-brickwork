// bwTagInput carrier suite (icvoss/django-brickwork#237): committed tags
// must have exactly one visible representation (the chip), never a second
// copy as comma-joined text in the still-visible floor input.
//
// Against tag-input-js-<theme>.html (a11y/generate_fixtures.py), which
// boots Alpine from node_modules exactly as a host application would (the
// FIXTURE owns Alpine.start(); brickwork never does) and renders two real
// {% include %}'d instances of _tag_input.html, single-line ("skill-tags")
// and multiline ("related-topics"), each pre-filled with two committed tags
// via `value` so the fixture's own load already exercises the 422
// re-render parse path (init() reads the server-rendered value into chips
// BEFORE the carrier takeover moves `name` onto the hidden input). Both
// instances sit inside one real <form>, which the commit-on-submit
// data-loss guard listens on.
//
// Chromium blocks module imports from file:// by default, so this file's
// browser launches with --allow-file-access-from-files (scoped here; the
// axe.spec.mjs run is untouched). A real POST is unavailable under file://,
// so the submit tests intercept the form's submit event in the page
// (preventDefault) and read state back via FormData rather than attempting
// a navigation. Per this repo's own file:// trap, a reload discards
// page.evaluate() state, so every assertion below reads the live DOM after
// an interaction rather than mutating then reloading.
//
// Also covers (icvoss/django-brickwork#244): a root-replacing swap producing
// a fresh, independently-carriered instance (content-only re-init on the
// SAME root was investigated and found unreachable under Alpine v3; see the
// "root-replacing swap" describe block below and tag_input.js's module-level
// Re-init comment for the record), two instances in one form each folding
// into their own carrier on one submit, and dedupe-on-submit (buffer text
// equal to an already-committed tag is not posted twice).

import { test, expect } from "@playwright/test";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const fx = (name) => pathToFileURL(join(FIXTURES, name)).href;

test.use({ launchOptions: { args: ["--allow-file-access-from-files"] } });

async function boot(page) {
  await page.goto(fx("tag-input-js-light.html"));
  await page.waitForFunction(() => !!window.Alpine);
  // The carrier takeover is the ready signal: the visible floor loses its
  // `name` attribute only once bwTagInput's init() has run.
  await page.waitForFunction(() => !document.getElementById("skill-tags").hasAttribute("name"));
}

// Reads the form's posted shape without a real navigation (file:// has no
// server to receive it): intercepting submit and building FormData proves
// exactly what a real POST would serialise, since FormData walks named
// controls the same way the browser's own submission does.
async function interceptSubmit(page) {
  await page.evaluate(() => {
    window.__submitted = null;
    document.getElementById("tag-input-form").addEventListener("submit", (event) => {
      event.preventDefault();
      window.__submitted = Object.fromEntries(new FormData(event.target).entries());
    });
  });
}

const submittedData = (page) => page.evaluate(() => window.__submitted);

// Each tag-input instance's chips live in the sibling chip container inside
// the same .bw-tag-input wrapper as the named floor, so scoping through
// that wrapper distinguishes the single-line and multiline instances.
const chipsFor = (page, floorId) => page.locator(`.bw-tag-input:has(#${floorId}) .bw-combobox__chip`);

test.describe("single-line floor (skill-tags)", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
  });

  test("init parses the server-rendered value into chips and takes over the carrier", async ({ page }) => {
    await expect(chipsFor(page, "skill-tags")).toHaveCount(2);
    // the visible floor no longer carries `name` (the carrier took it over)
    await expect(page.locator("#skill-tags")).not.toHaveAttribute("name");
    // the visible floor no longer shows the committed tags as text
    await expect(page.locator("#skill-tags")).toHaveValue("");
    // the hidden carrier now carries the real name and the comma-joined list
    const carrier = page.locator('input[type="hidden"][name="skill_tags"]');
    await expect(carrier).toHaveCount(1);
    await expect(carrier).toHaveValue("django, python");
  });

  test("Enter commits the buffer as a chip, clears the floor, and updates the carrier; no duplication", async ({
    page,
  }) => {
    await page.locator("#skill-tags").fill("testing");
    await page.locator("#skill-tags").press("Enter");
    await expect(page.locator('input[type="hidden"][name="skill_tags"]')).toHaveValue("django, python, testing");
    await expect(page.locator("#skill-tags")).toHaveValue("");
    const value = await page.locator("#skill-tags").inputValue();
    expect(value).not.toContain("django");
    expect(value).not.toContain("testing");
  });

  test("comma commits the buffer as a chip the same way Enter does", async ({ page }) => {
    await page.locator("#skill-tags").fill("golang");
    await page.locator("#skill-tags").press(",");
    await expect(page.locator('input[type="hidden"][name="skill_tags"]')).toHaveValue("django, python, golang");
    await expect(page.locator("#skill-tags")).toHaveValue("");
  });

  test("the chip remove button removes a tag and updates the carrier", async ({ page }) => {
    await chipsFor(page, "skill-tags").first().locator(".bw-combobox__chip-remove").click();
    await expect(page.locator('input[type="hidden"][name="skill_tags"]')).toHaveValue("python");
    await expect(page.locator("#skill-tags")).toBeFocused(); // removal must not drop focus (BR-BW-JS-006)
  });

  test("Backspace on an empty buffer removes the last committed tag", async ({ page }) => {
    await page.locator("#skill-tags").focus();
    await page.keyboard.press("Backspace");
    await expect(page.locator('input[type="hidden"][name="skill_tags"]')).toHaveValue("django");
  });

  test("submitting with an uncommitted buffer folds it into the carrier as a final tag (data-loss guard)", async ({
    page,
  }) => {
    await interceptSubmit(page);
    await page.locator("#skill-tags").fill("uncommitted-tag");
    await page.locator('button[type="submit"]').click();
    const data = await submittedData(page);
    expect(data.skill_tags).toBe("django, python, uncommitted-tag");
    // the folded tag is now a real chip too, not just carrier text
    await expect(chipsFor(page, "skill-tags")).toHaveCount(3);
  });

  test("submitting with no uncommitted text leaves the carrier as the already-committed list", async ({ page }) => {
    await interceptSubmit(page);
    await page.locator('button[type="submit"]').click();
    const data = await submittedData(page);
    expect(data.skill_tags).toBe("django, python");
  });
});

test.describe("multiline floor (related-topics)", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
  });

  test("init parses the textarea's server-rendered value and takes over the carrier", async ({ page }) => {
    await expect(page.locator("#related-topics")).not.toHaveAttribute("name");
    await expect(page.locator("#related-topics")).toHaveValue("");
    const carrier = page.locator('input[type="hidden"][name="related_topics"]');
    await expect(carrier).toHaveValue("alpha, beta");
  });

  test("Enter commits a chip on the textarea floor without duplicating committed tags", async ({ page }) => {
    await page.locator("#related-topics").fill("gamma");
    await page.locator("#related-topics").press("Enter");
    await expect(page.locator('input[type="hidden"][name="related_topics"]')).toHaveValue("alpha, beta, gamma");
    await expect(page.locator("#related-topics")).toHaveValue("");
  });

  test("submitting the shared form folds the textarea's uncommitted buffer into its own carrier", async ({
    page,
  }) => {
    await interceptSubmit(page);
    await page.locator("#related-topics").fill("delta");
    await page.locator('button[type="submit"]').click();
    const data = await submittedData(page);
    expect(data.related_topics).toBe("alpha, beta, delta");
    // the single-line field's own carrier is unaffected by the other
    // field's uncommitted text
    expect(data.skill_tags).toBe("django, python");
  });
});

// --- root-replacing swap (icvoss/django-brickwork#244) ----------------------
//
// icvoss/django-brickwork#244 was opened against a content-only re-init
// hazard: the SAME root keeping its x-data and getting init() run on it a
// second time (an Alpine re-mount, or an htmx swap that targets content
// inside the root without replacing the root). Empirical investigation
// (source reading of the vendored Alpine plus a runtime probe, recorded on
// the PR) established that shape cannot occur under Alpine v3: initTree()
// stamps every element it walks with `_x_marker` and skips any element that
// already carries one, so calling window.Alpine.initTree() again on an
// already-initialised root never re-runs init(), confirmed by an
// instrumented build showing the branch never executed, and by removing the
// carrier-detect branch entirely and observing no test's behaviour change.
// tag_input.js's module-level "Re-init" comment carries the full record.
//
// What genuinely replaces a mounted tag input is a root-REPLACING swap: the
// whole .bw-tag-input element removed and a fresh one inserted in its place
// (matching sortable.spec.mjs's persistence suite, which proves the same
// shape via a real htmx outerHTML swap). This suite reproduces that with a
// direct DOM replacement, since no htmx endpoint is wired for this fixture,
// and asserts the fresh element gets its own independent carrier while the
// old carrier and its DOM leave together with the old root.

// Server-rendered shape of the "skill-tags" instance BEFORE any JS
// enhancement (mirrors _tag_input.html's single-line branch exactly: `name`
// still on the floor, no carrier, no chips). Hardcoded rather than snapshotted
// from the live page, because the live DOM races Alpine's own init (which
// starts as soon as the module loads, ahead of any awaitable signal a test
// can key off), so a "before enhancement" DOM snapshot cannot be trusted to
// actually predate the carrier takeover. This is exactly the shape a real
// htmx fragment response for this field would carry, since the server
// template never renders the client-only carrier element.
const FRESH_SKILL_TAGS_HTML = `
<div class="bw-tag-input" x-data="bwTagInput()" data-bw-tag-input>
  <div class="bw-tag-input__chips" data-bw-tag-input-chips data-bw-tag-remove-label="Remove"></div>
  <input class="bw-input bw-tag-input__floor" type="text" id="skill-tags" name="skill_tags"
         value="django, python" data-bw-tag-input-floor>
</div>`;

test.describe("root-replacing swap", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
  });

  // Swaps the .bw-tag-input wrapper for a fresh element built from
  // FRESH_SKILL_TAGS_HTML: a genuinely new element with no `_x_marker` and
  // no carrier, which Alpine's own mutation observer initialises exactly
  // once, the same path a real htmx swap uses.
  async function replaceRoot(page) {
    await page.evaluate((html) => {
      const root = document.querySelector(".bw-tag-input:has(#skill-tags)");
      const template = document.createElement("template");
      template.innerHTML = html.trim();
      root.replaceWith(template.content.firstElementChild);
    }, FRESH_SKILL_TAGS_HTML);
  }

  test("the fresh root parses the server-rendered floor value into its own new carrier", async ({ page }) => {
    // the pre-swap root already committed its own carrier from the same
    // server-rendered value; asserting the count stays at 1 after the swap
    // proves the old carrier left the DOM with the old root rather than
    // lingering alongside the fresh one
    await replaceRoot(page);
    // Alpine's mutation observer runs on microtask timing; wait for the
    // fresh root's own init() to complete the carrier takeover
    await page.waitForFunction(() => !document.getElementById("skill-tags").hasAttribute("name"));

    const carriers = page.locator('input[type="hidden"][name="skill_tags"]');
    await expect(carriers).toHaveCount(1); // exactly one carrier: the old root's left with it
    await expect(carriers).toHaveValue("django, python");
    await expect(chipsFor(page, "skill-tags")).toHaveCount(2);
    await expect(page.locator("#skill-tags")).not.toHaveAttribute("name");
  });

  test("the fresh root's floor and submit listeners work independently of the old root's", async ({ page }) => {
    await replaceRoot(page);
    await page.waitForFunction(() => !document.getElementById("skill-tags").hasAttribute("name"));

    await page.locator("#skill-tags").fill("rust");
    await page.locator("#skill-tags").press("Enter");
    const carriers = page.locator('input[type="hidden"][name="skill_tags"]');
    await expect(carriers).toHaveCount(1);
    await expect(carriers).toHaveValue("django, python, rust");

    await interceptSubmit(page);
    await page.locator("#skill-tags").fill("uncommitted-tag");
    await page.locator('button[type="submit"]').click();
    const data = await submittedData(page);
    // only the fresh root's own listener fires; a stale listener left over
    // from the replaced root (there is none, since replaceWith() detaches
    // it) would show up as a duplicate `skill_tags` entry in FormData
    expect(data.skill_tags).toBe("django, python, rust, uncommitted-tag");
  });
});

// --- suggestion 1: two instances, one submit (icvoss/django-brickwork#244) --

test.describe("two tag inputs in one form", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
  });

  test("one user submit folds each field's own uncommitted buffer into its own carrier", async ({ page }) => {
    await interceptSubmit(page);
    await page.locator("#skill-tags").fill("uncommitted-single");
    await page.locator("#related-topics").fill("uncommitted-multi");
    await page.locator('button[type="submit"]').click();
    const data = await submittedData(page);
    expect(data.skill_tags).toBe("django, python, uncommitted-single");
    expect(data.related_topics).toBe("alpha, beta, uncommitted-multi");
  });
});

// --- suggestion 2: dedupe-on-submit (icvoss/django-brickwork#244) -----------
//
// add()'s existing dedupe (this.tags.includes(tag) is a no-op) already
// governs Enter/comma commits; this pins that the same guard governs the
// commit-on-submit fold path, since _commitOnSubmit() reuses _commitBuffer()
// -> add() rather than a separate code path.

test.describe("dedupe on submit", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
  });

  test("buffer text matching an already-committed tag is not duplicated on submit", async ({ page }) => {
    await interceptSubmit(page);
    await page.locator("#skill-tags").fill("django");
    await page.locator('button[type="submit"]').click();
    const data = await submittedData(page);
    expect(data.skill_tags).toBe("django, python");
    await expect(chipsFor(page, "skill-tags")).toHaveCount(2);
  });
});
