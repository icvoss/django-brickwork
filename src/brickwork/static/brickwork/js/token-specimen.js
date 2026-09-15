/**
 * Token specimen progressive enhancement (THM-016,
 * icvoss/django-brickwork#268).
 *
 * Vanilla IIFE: no Alpine, no htmx. Fills resolved computed values and
 * measured contrast ratios on .bw-token-specimen roots. The no-JS floor
 * already shows token names, live swatches, dual theme panes, and the
 * manifest minContrast floor on paired rows.
 *
 * Idempotent: safe if the template includes the script more than once.
 */
(function () {
  "use strict";

  if (window.__bwTokenSpecimenBooted) return;
  window.__bwTokenSpecimenBooted = true;

  function parseChannels(color) {
    if (!color || color === "transparent") return null;
    var m = String(color)
      .trim()
      .match(/^rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)(?:\s*,\s*([0-9.]+))?\s*\)$/i);
    if (!m) {
      m = String(color)
        .trim()
        .match(/^rgba?\(\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)(?:\s*\/\s*([0-9.]+%?))?\s*\)$/i);
    }
    if (!m) return null;
    var alpha = m[4] === undefined ? 1 : parseFloat(m[4]);
    if (typeof m[4] === "string" && m[4].indexOf("%") !== -1) {
      alpha = parseFloat(m[4]) / 100;
    }
    if (alpha === 0) return null;
    return {
      r: Math.min(255, Math.max(0, parseFloat(m[1]))) / 255,
      g: Math.min(255, Math.max(0, parseFloat(m[2]))) / 255,
      b: Math.min(255, Math.max(0, parseFloat(m[3]))) / 255,
    };
  }

  function channelLuminance(c) {
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  }

  function relativeLuminance(rgb) {
    return (
      0.2126 * channelLuminance(rgb.r) +
      0.7152 * channelLuminance(rgb.g) +
      0.0722 * channelLuminance(rgb.b)
    );
  }

  function contrastRatio(fg, bg) {
    var a = relativeLuminance(fg);
    var b = relativeLuminance(bg);
    var lighter = Math.max(a, b);
    var darker = Math.min(a, b);
    return (lighter + 0.05) / (darker + 0.05);
  }

  function enhance(root) {
    if (root.getAttribute("data-bw-token-specimen-ready")) return;
    root.setAttribute("data-bw-token-specimen-ready", "true");

    var rows = root.querySelectorAll(".bw-token-specimen__row");
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var token = row.getAttribute("data-bw-token");
      if (!token) continue;
      var valueEl = row.querySelector("[data-bw-token-resolved]");
      var computed = getComputedStyle(row).getPropertyValue(token).trim();
      if (valueEl && computed) {
        valueEl.textContent = computed;
      }

      var pair = row.getAttribute("data-bw-token-pair");
      var measuredEl = row.querySelector("[data-bw-contrast-measured]");
      if (!pair || !measuredEl) continue;
      var fgRaw = getComputedStyle(row).getPropertyValue(token).trim();
      var bgRaw = getComputedStyle(row).getPropertyValue(pair).trim();
      // Resolve through a probe so color-mix() and var() chains become rgb().
      var probe = document.createElement("span");
      probe.style.color = fgRaw || "var(" + token + ")";
      probe.style.backgroundColor = bgRaw || "var(" + pair + ")";
      probe.style.position = "absolute";
      probe.style.inlineSize = "0";
      probe.style.blockSize = "0";
      probe.style.overflow = "hidden";
      row.appendChild(probe);
      var styles = getComputedStyle(probe);
      var fg = parseChannels(styles.color);
      var bg = parseChannels(styles.backgroundColor);
      row.removeChild(probe);
      if (!fg || !bg) continue;
      var ratio = contrastRatio(fg, bg);
      measuredEl.hidden = false;
      measuredEl.textContent = ratio.toFixed(2) + ":1";
    }
  }

  function enhanceAll() {
    var roots = document.querySelectorAll("[data-bw-token-specimen]");
    for (var i = 0; i < roots.length; i++) {
      enhance(roots[i]);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhanceAll);
  } else {
    enhanceAll();
  }
})();
