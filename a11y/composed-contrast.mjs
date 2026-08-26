// Shared composited-contrast measurement (WCAG 1.4.3, ADR-057/#118), used by
// axe.spec.mjs (named surfaces) and archetypes.spec.mjs (auto-discovered
// composited-surface sweep). Extracted from the two near-identical copies
// those files carried (icvoss/django-brickwork#239 contention audit) so a
// future fix to the measurement lands once, not twice.
//
// Measures the worst-case composited contrast ratio between an element's own
// text colour and the page pixels actually behind it, across the element's
// full rendered box (its full vertical extent, so a defect that only shows up
// partway down a wrapped line is still caught).
//
// The element is screenshotted in place (not re-rendered in isolation), so
// what is measured is exactly what a reader sees: real glyphs already
// composited over the real scrim over the real media. Anti-aliased glyph
// edges blend towards the text colour and would otherwise register as a
// falsely dark (or light) "background" pixel a handful of times per row;
// taking the per-row MODE of the non-glyph pixels is robust to that, because
// the true background fills the overwhelming majority of every row that has
// any background at all (line-height leading, inter-word gaps, the insides
// of open letterforms), while the anti-aliasing tail is never the most
// frequent colour in a row.
//
// The pixel-walk glyphThreshold (40) is tuned against a devicePixelRatio of
// 1: at a higher DPR the same CSS pixel maps to more device pixels and the
// glyph/background split this threshold assumes no longer holds without
// re-tuning. Callers get devicePixelRatio asserted here rather than
// discovering a silent mis-measurement later.
export async function measureComposedContrast(page, locator) {
  const dpr = await page.evaluate(() => window.devicePixelRatio);
  if (dpr !== 1) {
    throw new Error(
      `measureComposedContrast's pixel-walk heuristic (glyphThreshold tuned for devicePixelRatio 1) ` +
        `is not valid at devicePixelRatio ${dpr}; this context needs its own tuning before this helper ` +
        `can be trusted here`,
    );
  }

  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  const textColourCss = await locator.evaluate((el) => getComputedStyle(el).color);
  const [tr, tg, tb] = await page.evaluate((css) => {
    const canvas = document.createElement("canvas");
    canvas.width = 1;
    canvas.height = 1;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = css;
    ctx.fillRect(0, 0, 1, 1);
    const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data;
    return [r, g, b];
  }, textColourCss);

  const screenshot = await page.screenshot({
    clip: { x: box.x, y: box.y, width: box.width, height: box.height },
  });

  return page.evaluate(
    async ({ pngBase64, textColour, glyphThreshold }) => {
      const img = new Image();
      img.src = `data:image/png;base64,${pngBase64}`;
      await img.decode();
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0);
      const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;

      const relLum = ([r, g, b]) => {
        const channel = (c) => {
          c /= 255;
          return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
        };
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
      };
      const ratio = (a, b) => {
        const lA = relLum(a);
        const lB = relLum(b);
        return (Math.max(lA, lB) + 0.05) / (Math.min(lA, lB) + 0.05);
      };
      const colourDistance = ([r1, g1, b1], [r2, g2, b2]) =>
        Math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2);

      let worstRatio = Infinity;
      let worstBackground = null;
      for (let y = 0; y < canvas.height; y++) {
        const rowCounts = new Map();
        for (let x = 0; x < canvas.width; x++) {
          const idx = (y * canvas.width + x) * 4;
          const pixel = [data[idx], data[idx + 1], data[idx + 2]];
          if (colourDistance(pixel, textColour) < glyphThreshold) continue;
          const key = pixel.join(",");
          rowCounts.set(key, (rowCounts.get(key) ?? 0) + 1);
        }
        if (rowCounts.size === 0) continue;
        const [modeKey] = [...rowCounts.entries()].sort((a, b) => b[1] - a[1])[0];
        const modeRgb = modeKey.split(",").map(Number);
        const rowRatio = ratio(textColour, modeRgb);
        if (rowRatio < worstRatio) {
          worstRatio = rowRatio;
          worstBackground = modeRgb;
        }
      }
      return { ratio: worstRatio, background: worstBackground };
    },
    { pngBase64: screenshot.toString("base64"), textColour: [tr, tg, tb], glyphThreshold: 40 },
  );
}
