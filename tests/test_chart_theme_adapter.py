"""CHT-006 chart adapter: shipped module + tooltip swatch suppression (#301).

The close condition on icvoss/django-brickwork#301 is a real adapter artefact
with a test that the returned theme object suppresses the engine tooltip
series swatch. Series-against-tooltip-bg is resolved by that suppression
(ADR-082 sixth amendment), not by a palette floor.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_ADAPTER = _ROOT / "src" / "brickwork" / "static" / "brickwork" / "js" / "chart-theme.js"

_FIXTURE_TOKENS = {
    "series": [f"series-{i}" for i in range(1, 9)],
    "axis": "axis",
    "grid": "grid",
    "axisLabel": "axis-label",
    "tooltip": {
        "bg": "tooltip-bg",
        "text": "tooltip-text",
        "border": "tooltip-border",
    },
}

_NODE_PROBE = """\
import { pathToFileURL } from "node:url";
const {
  brickworkChartTheme,
  CHART_TOKEN_NAMES,
  SUPPORTED_ENGINES,
} = await import(pathToFileURL(process.argv[1]).href);
const tokens = JSON.parse(process.argv[2]);
const chartjs = brickworkChartTheme("chartjs", tokens);
const apex = brickworkChartTheme("apexcharts", tokens);
let unsupported = null;
try {
  brickworkChartTheme("echarts", tokens);
} catch (err) {
  unsupported = String(err && err.message ? err.message : err);
}
console.log(JSON.stringify({
  supportedEngines: SUPPORTED_ENGINES,
  seriesNames: CHART_TOKEN_NAMES.series,
  chartjsDisplayColors: chartjs.plugins.tooltip.displayColors,
  chartjsTooltipBg: chartjs.plugins.tooltip.backgroundColor,
  chartjsSeries: chartjs.color,
  apexMarkerShow: apex.tooltip.marker.show,
  apexFillSeriesColor: apex.tooltip.fillSeriesColor,
  apexColors: apex.colors,
  unsupported,
}));
"""


def test_chart_theme_adapter_ships_beside_other_static_js() -> None:
    assert _ADAPTER.is_file(), f"missing shipped adapter at {_ADAPTER}"
    text = _ADAPTER.read_text(encoding="utf-8")
    assert "brickworkChartTheme" in text
    assert "brickworkChartTokens" in text
    assert "displayColors: false" in text
    assert "show: false" in text
    assert "getComputedStyle" in text


def test_adapter_vocabulary_matches_adr_082_token_names() -> None:
    """A rename in the CSS without updating the adapter is a silent off-brand chart."""
    text = _ADAPTER.read_text(encoding="utf-8")
    expected = [f"--bw-color-chart-{i}" for i in range(1, 9)] + [
        "--bw-color-chart-axis",
        "--bw-color-chart-grid",
        "--bw-color-chart-axis-label",
        "--bw-color-chart-tooltip-bg",
        "--bw-color-chart-tooltip-text",
        "--bw-color-chart-tooltip-border",
    ]
    missing = [name for name in expected if name not in text]
    assert not missing, f"adapter no longer names chart tokens: {missing}"


@pytest.mark.skipif(
    subprocess.run(["node", "--version"], capture_output=True).returncode != 0,
    reason="node required to execute the shipped ESM adapter",
)
def test_engine_recipes_suppress_tooltip_series_swatch() -> None:
    """#301 close condition: returned theme objects include suppression."""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", _NODE_PROBE, str(_ADAPTER), json.dumps(_FIXTURE_TOKENS)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["supportedEngines"] == ["chartjs", "apexcharts"]
    assert payload["seriesNames"] == [f"--bw-color-chart-{i}" for i in range(1, 9)]
    assert payload["chartjsDisplayColors"] is False
    assert payload["chartjsTooltipBg"] == "tooltip-bg"
    assert payload["chartjsSeries"] == _FIXTURE_TOKENS["series"]
    assert payload["apexMarkerShow"] is False
    assert payload["apexFillSeriesColor"] is False
    assert payload["apexColors"] == _FIXTURE_TOKENS["series"]
    assert payload["unsupported"] and "not a supported" in payload["unsupported"]
