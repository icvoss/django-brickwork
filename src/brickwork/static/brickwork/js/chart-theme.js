/**
 * CHT-006 chart adapter: token read + engine-shaped theme recipes.
 *
 * Split at the ADR-082 Decision 9 seam:
 *   - Neutral half: brickworkChartTokens(el) resolves --bw-color-chart-* via
 *     getComputedStyle. Picks no charting engine.
 *   - Engine-shaped half: brickworkChartTheme("chartjs"|"apexcharts", ...) maps
 *     that bundle into a plain options object. No Chart.js / ApexCharts /
 *     ECharts import (CHT-011); the consumer mounts their own engine.
 *
 * Tooltip series swatch suppression is part of each recipe's specified output
 * (icvoss/django-brickwork#301, ADR-082 sixth amendment): Chart.js
 * plugins.tooltip.displayColors = false; ApexCharts tooltip.marker.show =
 * false. Series-against-tooltip-bg is resolved by that suppression, not by
 * re-solving the palette.
 *
 * Load as an ES module from {% static "brickwork/js/chart-theme.js" %}.
 */
"use strict";

/** CSS custom-property names the adapter reads (ADR-082 Decision 1). */
export const CHART_TOKEN_NAMES = Object.freeze({
  series: Object.freeze([
    "--bw-color-chart-1",
    "--bw-color-chart-2",
    "--bw-color-chart-3",
    "--bw-color-chart-4",
    "--bw-color-chart-5",
    "--bw-color-chart-6",
    "--bw-color-chart-7",
    "--bw-color-chart-8",
  ]),
  axis: "--bw-color-chart-axis",
  grid: "--bw-color-chart-grid",
  axisLabel: "--bw-color-chart-axis-label",
  tooltipBg: "--bw-color-chart-tooltip-bg",
  tooltipText: "--bw-color-chart-tooltip-text",
  tooltipBorder: "--bw-color-chart-tooltip-border",
});

/** Engines with a conforming recipe in this module. */
export const SUPPORTED_ENGINES = Object.freeze(["chartjs", "apexcharts"]);

function readProp(styles, name) {
  return String(styles.getPropertyValue(name) || "").trim();
}

function isResolvedTokens(value) {
  return (
    value != null &&
    typeof value === "object" &&
    Array.isArray(value.series) &&
    value.tooltip != null &&
    typeof value.tooltip === "object"
  );
}

/**
 * Resolve the chart token vocabulary from a live element (usually
 * document.documentElement, or the chart card root after a theme switch).
 *
 * @param {Element} [el=document.documentElement]
 * @returns {{
 *   series: string[],
 *   axis: string,
 *   grid: string,
 *   axisLabel: string,
 *   tooltip: { bg: string, text: string, border: string },
 * }}
 */
export function brickworkChartTokens(el) {
  const root =
    el ||
    (typeof document !== "undefined" ? document.documentElement : null);
  if (!root || typeof getComputedStyle !== "function") {
    throw new TypeError(
      "brickworkChartTokens(el) needs a DOM element with getComputedStyle available",
    );
  }
  const styles = getComputedStyle(root);
  return {
    series: CHART_TOKEN_NAMES.series.map((name) => readProp(styles, name)),
    axis: readProp(styles, CHART_TOKEN_NAMES.axis),
    grid: readProp(styles, CHART_TOKEN_NAMES.grid),
    axisLabel: readProp(styles, CHART_TOKEN_NAMES.axisLabel),
    tooltip: {
      bg: readProp(styles, CHART_TOKEN_NAMES.tooltipBg),
      text: readProp(styles, CHART_TOKEN_NAMES.tooltipText),
      border: readProp(styles, CHART_TOKEN_NAMES.tooltipBorder),
    },
  };
}

function resolveTokens(elOrTokens) {
  return isResolvedTokens(elOrTokens)
    ? elOrTokens
    : brickworkChartTokens(elOrTokens);
}

/**
 * Chart.js-shaped options fragment. Merge into new Chart(ctx, { type, data, options }).
 * Consumer assigns tokens.series onto datasets; this fragment owns chrome + tooltip.
 *
 * @param {Element|object} elOrTokens
 * @returns {object}
 */
export function brickworkChartThemeChartJs(elOrTokens) {
  const t = resolveTokens(elOrTokens);
  return {
    color: t.series.slice(),
    scales: {
      x: {
        border: { color: t.axis },
        grid: { color: t.grid },
        ticks: { color: t.axisLabel },
      },
      y: {
        border: { color: t.axis },
        grid: { color: t.grid },
        ticks: { color: t.axisLabel },
      },
    },
    plugins: {
      tooltip: {
        // #301 / ADR-082: suppress the default series colour swatch inside the tooltip.
        displayColors: false,
        backgroundColor: t.tooltip.bg,
        titleColor: t.tooltip.text,
        bodyColor: t.tooltip.text,
        borderColor: t.tooltip.border,
        borderWidth: 1,
      },
    },
  };
}

/**
 * ApexCharts-shaped options fragment. Spread into new ApexCharts(el, { ...theme, series }).
 *
 * @param {Element|object} elOrTokens
 * @returns {object}
 */
export function brickworkChartThemeApexCharts(elOrTokens) {
  const t = resolveTokens(elOrTokens);
  // t.tooltip is intentionally unused here: ApexCharts has no first-class
  // tooltip bg/text/border options. Consumers style .apexcharts-tooltip from
  // --bw-color-chart-tooltip-* (CHT-017); see INTEGRATION.md section 5a.
  return {
    colors: t.series.slice(),
    grid: { borderColor: t.grid },
    xaxis: {
      axisBorder: { color: t.axis },
      axisTicks: { color: t.axis },
      labels: { style: { colors: t.axisLabel } },
    },
    yaxis: {
      labels: { style: { colors: t.axisLabel } },
    },
    tooltip: {
      // #301 / ADR-082: suppress the default series colour marker inside the tooltip.
      marker: { show: false },
      fillSeriesColor: false,
    },
  };
}

/**
 * CHT-006 entry: return an engine-shaped theme for a supported engine.
 *
 * @param {"chartjs"|"apexcharts"} engine
 * @param {Element|object} [elOrTokens]
 * @returns {object}
 */
export function brickworkChartTheme(engine, elOrTokens) {
  const key = String(engine || "").toLowerCase();
  if (key === "chartjs" || key === "chart.js") {
    return brickworkChartThemeChartJs(elOrTokens);
  }
  if (key === "apexcharts" || key === "apex") {
    return brickworkChartThemeApexCharts(elOrTokens);
  }
  throw new Error(
    'brickworkChartTheme(engine): supported engines are "chartjs" and "apexcharts"; ' +
      "an engine that cannot suppress its tooltip series swatch is not a supported " +
      "adapter target (icvoss/django-brickwork#301).",
  );
}
