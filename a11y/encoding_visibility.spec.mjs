// Browser-level COL-030 redeeming-label visibility (icvoss/django-brickwork#342).
//
// Python's tests/_encoding_contract.py helpers catch markup-level hiding
// (aria-hidden, hidden, inert, inline display:none / visibility:hidden) but
// cannot resolve a class selector against a real cascade. A stylesheet rule
// such as `.bw-gauge__label{display:none}` leaves those helpers green while
// the numeric label is invisible. This suite closes that gap: load the
// existing a11y fixtures under a real layout engine and assert the
// redeeming text labels are displayed and visible.
//
// The check is stated once (labelCascadeVisibility / assertRedeemingLabelsVisible)
// and applied across every colour-encoded family member whose shipped
// fixtures carry a redeeming label: gauge, ranked list, sparkline, and
// progress (show_value). axe over the same fixtures is complementary; it
// does not know the arc/bar/line colour is meaning that text must redeem.

import { test, expect } from "@playwright/test";
import { existsSync, readdirSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "fixtures");
const fx = (name) => pathToFileURL(join(FIXTURES, name)).href;
const THEMES = ["light", "dark"];

// Family members with redeeming labels in the generated a11y fixtures.
// Selectors are scoped so empty / loading / header chrome cannot satisfy
// the property (matched-the-wrong-thing: an empty head .bw-ranked-list__value
// must not count as a redeeming label).
const FAMILY = [
  {
    name: "gauge",
    fixture: (theme) => `gauge-${theme}.html`,
    // Numeric / gauge_label text that redeems the threshold-coloured arc.
    selector: ".bw-gauge__label",
  },
  {
    name: "ranked-list",
    fixture: (theme) => `ranked-list-${theme}.html`,
    // Populated-row label and value only (not the aria-hidden column head).
    selector: ".bw-ranked-list__row .bw-ranked-list__label, .bw-ranked-list__row .bw-ranked-list__value",
  },
  {
    name: "sparkline",
    fixture: (theme) => `sparkline-${theme}.html`,
    // Visible label and value that redeem the stroke colour / shape.
    selector: ".bw-sparkline__label, .bw-sparkline__value",
  },
  {
    name: "progress",
    fixture: (theme) => `feedback-${theme}.html`,
    // show_value determinate percent text (indeterminate has none).
    selector: ".bw-progress__value",
  },
];

test("encoding-visibility fixtures were generated", () => {
  expect(
    existsSync(FIXTURES) && readdirSync(FIXTURES).some((f) => f.endsWith(".html")),
    `${FIXTURES} contains no .html fixtures; run npm run a11y:fixtures first`,
  ).toBe(true);
  for (const member of FAMILY) {
    for (const theme of THEMES) {
      const name = member.fixture(theme);
      expect(existsSync(join(FIXTURES, name)), `missing fixture ${name}`).toBe(true);
    }
  }
});

/**
 * Read cascade-resolved visibility for every matching redeeming label.
 *
 * A label is cascade-visible when getComputedStyle reports it is displayed
 * and visibility is not hidden, and getBoundingClientRect is non-zero.
 * Text content must still be present: an empty node that paints a box is
 * not a redeeming label.
 */
function labelCascadeVisibility(page, selector) {
  return page.locator(selector).evaluateAll((els) =>
    els.map((el) => {
      const cs = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      const text = (el.textContent || "").replace(/\s+/g, " ").trim();
      const displayed = cs.display !== "none" && cs.visibility !== "hidden";
      const hasBox = rect.width > 0 && rect.height > 0;
      return {
        text,
        display: cs.display,
        visibility: cs.visibility,
        width: rect.width,
        height: rect.height,
        displayed,
        hasBox,
        cascadeVisible: displayed && hasBox && text.length > 0,
      };
    }),
  );
}

async function assertRedeemingLabelsVisible(page, selector) {
  const reports = await labelCascadeVisibility(page, selector);
  expect(
    reports.length,
    `expected at least one redeeming label matching ${selector}`,
  ).toBeGreaterThan(0);
  for (const [i, report] of reports.entries()) {
    expect(
      report.cascadeVisible,
      `${selector}[${i}] must be cascade-visible ` +
        `(display=${report.display}, visibility=${report.visibility}, ` +
        `box=${report.width}x${report.height}, text=${JSON.stringify(report.text)})`,
    ).toBe(true);
  }
}

for (const member of FAMILY) {
  for (const theme of THEMES) {
    test(`${member.name} redeeming labels are cascade-visible (${theme})`, async ({ page }) => {
      await page.goto(fx(member.fixture(theme)));
      await assertRedeemingLabelsVisible(page, member.selector);
    });
  }
}

// Teeth check (icvoss/django-brickwork#342): the positive path above can be
// satisfied by "elements exist" alone if the helper ever stops reading the
// cascade. Inject the EXACT stylesheet mutation that left the Python
// encoding-contract helpers green, keep the labels present in the DOM with
// their text intact (matched-the-wrong-thing: pattern still matches), and
// require the cascade property to fail. Prefer a real failing assertion
// path over a comment-only control.
test("teeth: stylesheet display:none on gauge labels fails the cascade-visibility property", async ({
  page,
}) => {
  await page.goto(fx("gauge-light.html"));
  const before = await labelCascadeVisibility(page, ".bw-gauge__label");
  expect(before.length).toBeGreaterThan(0);
  expect(before.every((r) => r.cascadeVisible)).toBe(true);

  // Genuine cascade contest via a real <style> tag, not an inline style=
  // attribute (inline hiding is already covered by the Python helpers).
  await page.addStyleTag({ content: ".bw-gauge__label{display:none}" });

  const after = await labelCascadeVisibility(page, ".bw-gauge__label");
  expect(after.length).toBe(before.length);
  // Labels still match and still carry redeeming text: a vacuous "no
  // matches" or "empty text" failure would not prove the cascade read.
  expect(after.every((r) => r.text.length > 0)).toBe(true);
  expect(after.every((r) => r.display === "none")).toBe(true);
  expect(after.every((r) => !r.cascadeVisible)).toBe(true);

  await expect(
    assertRedeemingLabelsVisible(page, ".bw-gauge__label"),
  ).rejects.toThrow(/cascade-visible/);
});
