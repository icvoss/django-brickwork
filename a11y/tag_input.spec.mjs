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
// Also covers (icvoss/django-brickwork#244): re-init on the same root (an
// Alpine re-mount / content-only swap, reproduced with the real
// window.Alpine.initTree() API rather than a synthetic shortcut), two
// instances in one form each folding into their own carrier on one submit,
// and dedupe-on-submit (buffer text equal to an already-committed tag is
// not posted twice).

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

// --- re-init on the same root (icvoss/django-brickwork#244) -----------------
//
// A root-REPLACING swap (whole .bw-tag-input element out and back in) yields
// a fresh x-data element, which Alpine's own mutation observer initialises
// exactly once (sortable.spec.mjs's persistence suite already proves that
// path). The bug this guards against is the OTHER swap shape: content stays,
// the SAME root keeps its x-data and gets initialised a second time (an
// Alpine re-mount, or an htmx swap that targets content inside the root
// without replacing the root). window.Alpine.initTree() is Alpine's own
// public API for running init() on a tree (it is what Alpine calls
// internally when a new node is observed); calling it again on the SAME,
// already-initialised root reproduces that second-init path directly,
// without inventing a shortcut around the real code.

test.describe("re-init on the same root", () => {
  test.beforeEach(async ({ page }) => {
    await boot(page);
  });

  test("a second init() re-syncs from the carrier instead of wiping chips or duplicating the carrier", async ({
    page,
  }) => {
    // commit one more tag first, so re-init must preserve state beyond what
    // the server originally rendered, not just replay the initial value
    await page.locator("#skill-tags").fill("testing");
    await page.locator("#skill-tags").press("Enter");
    await expect(page.locator('input[type="hidden"][name="skill_tags"]')).toHaveValue("django, python, testing");

    await page.evaluate(() => {
      window.Alpine.initTree(document.querySelector(".bw-tag-input:has(#skill-tags)"));
    });

    // exactly one carrier remains, still holding the real name
    const carriers = page.locator('input[type="hidden"][name="skill_tags"]');
    await expect(carriers).toHaveCount(1);
    await expect(carriers).toHaveValue("django, python, testing");
    // chips match the carrier, rebuilt from it rather than wiped
    await expect(chipsFor(page, "skill-tags")).toHaveCount(3);
    // the floor is still the unnamed buffer, not re-carrying `name`
    await expect(page.locator("#skill-tags")).not.toHaveAttribute("name");
  });

  test("a subsequent commit after re-init updates the one surviving carrier", async ({ page }) => {
    await page.evaluate(() => {
      window.Alpine.initTree(document.querySelector(".bw-tag-input:has(#skill-tags)"));
    });
    await page.locator("#skill-tags").fill("rust");
    await page.locator("#skill-tags").press("Enter");
    const carriers = page.locator('input[type="hidden"][name="skill_tags"]');
    await expect(carriers).toHaveCount(1);
    await expect(carriers).toHaveValue("django, python, rust");
  });

  test("re-init does not stack a second submit listener (no double-fold of the buffer)", async ({ page }) => {
    await page.evaluate(() => {
      window.Alpine.initTree(document.querySelector(".bw-tag-input:has(#skill-tags)"));
    });
    await interceptSubmit(page);
    await page.locator("#skill-tags").fill("uncommitted-tag");
    await page.locator('button[type="submit"]').click();
    const data = await submittedData(page);
    // a stacked listener would still only fold once into the SAME carrier
    // value (idempotent), but a second, DIFFERENT carrier created by a
    // repeated takeover would show up as a duplicate `skill_tags` entry in
    // the posted form data; FormData.entries() would then yield more than
    // one, so asserting the single value also proves there is one carrier
    expect(data.skill_tags).toBe("django, python, uncommitted-tag");
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
