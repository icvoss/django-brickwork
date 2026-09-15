// Phase E gate (#600): L3 torture pack changes measured kit chrome on a white canvas.
//
// Self-contained (no a11y/fixtures generate step): inlines dist/brickwork.css
// and docs/examples/brand-pack/northline-material/tokens.css, then compares
// computed border-radius and box-shadow for card / primary button / modal panel
// with and without data-bw-brand="northline-material".

import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const BRICKWORK_CSS = readFileSync(
  join(ROOT, "src/brickwork/static/brickwork/dist/brickwork.css"),
  "utf8",
);
const PACK_CSS = readFileSync(
  join(ROOT, "docs/examples/brand-pack/northline-material/tokens.css"),
  "utf8",
);

const MARKUP = `
<main style="background:#fff;padding:2rem;min-block-size:100vh;font-family:system-ui">
  <button type="button" class="bw-btn bw-btn--primary" id="probe-btn">Save</button>
  <div class="bw-card" id="probe-card" style="margin-block-start:1rem;max-inline-size:20rem">
    <div class="bw-card__body">Card body</div>
  </div>
  <div class="bw-modal" id="probe-modal" style="margin-block-start:1rem">
    <div class="bw-modal__scrim" aria-hidden="true"></div>
    <div class="bw-modal__panel" id="probe-modal-panel" role="dialog" aria-modal="true" aria-label="Demo">
      <div class="bw-modal__body">Modal body</div>
    </div>
  </div>
</main>
`;

function pageHtml({ brand, includePack }) {
  const brandAttr = brand ? ` data-bw-brand="${brand}"` : "";
  const packBlock = includePack ? `<style>${PACK_CSS}</style>` : "";
  return `<!doctype html>
<html lang="en"${brandAttr} data-theme="light">
<head>
<meta charset="utf-8">
<title>theme-l3-chrome</title>
<style>${BRICKWORK_CSS}</style>
${packBlock}
</head>
<body>${MARKUP}</body>
</html>`;
}

async function measure(page) {
  return page.evaluate(() => {
    const props = ["border-top-left-radius", "box-shadow", "background-color"];
    const read = (id) => {
      const el = document.getElementById(id);
      const cs = getComputedStyle(el);
      return Object.fromEntries(props.map((p) => [p, cs.getPropertyValue(p)]));
    };
    return {
      btn: read("probe-btn"),
      card: read("probe-card"),
      modal: read("probe-modal-panel"),
    };
  });
}

test("northline-material changes measured card, button, and modal chrome", async ({ page }) => {
  // Pack CSS uses :root as well as [data-bw-brand]; only load it for the
  // themed document so the base probe sees package defaults alone.
  await page.setContent(pageHtml({ brand: null, includePack: false }), { waitUntil: "load" });
  const base = await measure(page);

  await page.setContent(pageHtml({ brand: "northline-material", includePack: true }), {
    waitUntil: "load",
  });
  const themed = await measure(page);

  // Button: L3 md radius via --bw-component-button-radius; elevation-1 shadow.
  expect(themed.btn["border-top-left-radius"]).not.toBe(base.btn["border-top-left-radius"]);
  expect(themed.btn["box-shadow"]).not.toBe(base.btn["box-shadow"]);
  expect(themed.btn["box-shadow"]).not.toBe("none");

  // Card: L3 lg radius + elevation-1 (ambient may stack; token change still shows).
  expect(themed.card["border-top-left-radius"]).not.toBe(base.card["border-top-left-radius"]);
  expect(themed.card["box-shadow"]).not.toBe(base.card["box-shadow"]);
  expect(themed.card["box-shadow"]).not.toBe("none");

  // Modal floor: xl radius (pack-authored) + elevation-2 + surface-raised paint.
  expect(themed.modal["border-top-left-radius"]).not.toBe(base.modal["border-top-left-radius"]);
  expect(themed.modal["box-shadow"]).not.toBe(base.modal["box-shadow"]);
  expect(themed.modal["background-color"]).not.toBe(base.modal["background-color"]);
});
