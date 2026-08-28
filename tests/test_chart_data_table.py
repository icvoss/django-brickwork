"""Tests for {% bw_chart_data_table %} and _chart_data_table.html (CHT-012's
accessible fallback table, CHT-013's data_table_mode).

Covers the three modes each rendering their documented shape, the closed
data_table_mode vocabulary's error path, the required caption, the semantic
contract (a real <caption>, <th scope="col"> column headers, <th scope="row">
row headers), escaping in every text position the tag feeds, the toggle mode's
no-JS floor, and THE STRUCTURAL ONE: the rendered table is not a descendant of
the role="img" mount element when both are rendered into _chart_card.html.

Two habits this module keeps deliberately, both from this package's recorded
history of tests that could not fail:

1. **Presence before absence.** Where a test asserts something is ABSENT
   (a raw payload, a script tag, a nested table), it first asserts the input
   actually REACHED the render, because a clean result and an unexercised
   code path are indistinguishable from outside. Every escaping test asserts
   the ESCAPED form is present, never merely that the raw form is absent.
2. **Never a one-element fixture for a non-first-element property.** The
   shared fixture below carries three columns and three rows precisely so a
   property about "every cell" or "the row header specifically" is violated
   at a NON-first position, which is where a helper that only handles the
   first element passes vacuously.

Structural assertions parse the output with html.parser (the mechanism
tests/test_chart_card.py already uses and documents), never a substring match:
"is this element inside that one" is a tree question, and a regex answering it
would report on text adjacency instead.
"""

from __future__ import annotations

from html.parser import HTMLParser

import pytest
from django.template import Context, Template
from django.template.exceptions import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from brickwork.templatetags.brickwork_components import _CHART_DATA_TABLE_MODES, bw_chart_data_table

# Three columns and three rows, not one of each: a property about "every
# header cell" or "the row header, not the first column header" is only
# genuinely exercised when it can be violated at a non-first position (a
# recorded lesson in this package: a correctly fixed helper still passed
# vacuously against a one-element fixture).
COLUMNS = ["Month", "Direct", "Referral"]
ROWS = [
    ["January", "120", "45"],
    ["February", "150", "60"],
    ["March", "180", "75"],
]
CAPTION = "Revenue by month and channel"


def _table(**kwargs: object) -> str:
    """Render the tag through the template layer, which is where the escaping
    this component relies on actually happens: calling the Python function
    directly would still render through the same templates, but going via
    {% load %} also proves the tag is registered under the name a consumer
    writes."""
    defaults: dict[str, object] = {"caption": CAPTION, "columns": COLUMNS, "rows": ROWS}
    defaults.update(kwargs)
    return Template(
        "{% load brickwork_components %}"
        "{% bw_chart_data_table caption=caption columns=columns rows=rows "
        "data_table_mode=data_table_mode toggle_label=toggle_label %}"
    ).render(
        Context(
            {
                "caption": defaults["caption"],
                "columns": defaults["columns"],
                "rows": defaults["rows"],
                "data_table_mode": defaults.get("data_table_mode", "hidden"),
                "toggle_label": defaults.get("toggle_label", ""),
            }
        )
    )


# --- structural parsing helpers --------------------------------------------


class _Tree(HTMLParser):
    """A minimal element tree: enough to answer "is X a descendant of Y",
    which is the question the sibling contract turns on and the only question
    a substring match cannot answer honestly."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: dict[str, object] = {"tag": None, "attrs": {}, "children": [], "parent": None}
        self._stack: list[dict[str, object]] = [self.root]
        # Void elements never receive children, so they must not be pushed:
        # an <input> or <br> left on the stack would swallow every following
        # sibling as its own descendant and make a nesting assertion lie.
        self._void = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node: dict[str, object] = {"tag": tag, "attrs": dict(attrs), "children": [], "parent": self._stack[-1]}
        self._stack[-1]["children"].append(node)  # type: ignore[union-attr]
        if tag not in self._void:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node: dict[str, object] = {"tag": tag, "attrs": dict(attrs), "children": [], "parent": self._stack[-1]}
        self._stack[-1]["children"].append(node)  # type: ignore[union-attr]

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index]["tag"] == tag:
                del self._stack[index:]
                return


def _parse(html: str) -> dict[str, object]:
    tree = _Tree()
    tree.feed(html)
    tree.close()
    return tree.root


def _walk(node: dict[str, object]):
    for child in node["children"]:  # type: ignore[union-attr]
        yield child
        yield from _walk(child)


def _find_all(root: dict[str, object], tag: str) -> list[dict[str, object]]:
    return [node for node in _walk(root) if node["tag"] == tag]


def _find_by_attr(root: dict[str, object], attr: str, value: str | None = None) -> list[dict[str, object]]:
    found = []
    for node in _walk(root):
        attrs = node["attrs"]
        if attr in attrs and (value is None or attrs[attr] == value):  # type: ignore[operator]
            found.append(node)
    return found


def _ancestors(node: dict[str, object]) -> list[dict[str, object]]:
    chain = []
    current = node["parent"]
    while current is not None:
        chain.append(current)  # type: ignore[arg-type]
        current = current["parent"]  # type: ignore[index]
    return chain


def _has_class(node: dict[str, object], name: str) -> bool:
    return name in str(node["attrs"].get("class", "")).split()  # type: ignore[union-attr]


# --- the three modes render their documented shape -------------------------


def test_hidden_mode_wraps_the_table_in_the_visually_hidden_clip_wrapper() -> None:
    out = _table(data_table_mode="hidden")
    root = _parse(out)

    tables = _find_all(root, "table")
    assert len(tables) == 1, "the fixture renders exactly one table; a different count means the shape moved"
    # The table is INSIDE the visually-hidden wrapper, asserted as a tree
    # relationship rather than by "both strings appear in the output".
    assert any(_has_class(node, "bw-visually-hidden") for node in _ancestors(tables[0]))
    # And it is not merely hidden by omission: the data really rendered.
    assert "March" in out
    # bw-visually-hidden is the clip-path pattern, never display:none, which
    # would remove the table from the accessibility tree and defeat the entire
    # contract this component exists for. Pinned against the SOURCE stylesheet
    # here rather than the compiled one, because this is a statement about the
    # rule this package authors.
    from pathlib import Path

    css = (Path(__file__).resolve().parent.parent / "frontend" / "src" / "components.css").read_text(encoding="utf-8")
    rule_start = css.index(".bw-visually-hidden {")
    rule = css[rule_start : css.index("}", rule_start)]
    assert "clip-path" in rule, f"bw-visually-hidden must stay a clip pattern, got: {rule!r}"
    assert "display: none" not in rule, (
        "bw-visually-hidden must never become display:none: that removes the fallback table from the "
        f"accessibility tree, which is the whole contract. Rule was: {rule!r}"
    )


def test_visible_mode_renders_the_table_plainly_with_no_wrapper() -> None:
    out = _table(data_table_mode="visible")
    root = _parse(out)

    tables = _find_all(root, "table")
    assert len(tables) == 1
    ancestors = _ancestors(tables[0])
    assert not any(_has_class(node, "bw-visually-hidden") for node in ancestors)
    assert not any(node["tag"] == "details" for node in ancestors)
    # Presence half: the base state is "no wrapper", not "no table".
    assert _has_class(ancestors[0], "bw-chart-data-table")
    assert "March" in out


def test_toggle_mode_renders_the_table_inside_a_native_details_disclosure() -> None:
    out = _table(data_table_mode="toggle")
    root = _parse(out)

    details = _find_all(root, "details")
    assert len(details) == 1, f"toggle mode must render exactly one <details>, found {len(details)}"
    summaries = _find_all(details[0], "summary")
    assert len(summaries) == 1, "a <details> with no <summary> has no accessible, operable trigger"

    tables = _find_all(root, "table")
    assert len(tables) == 1
    assert details[0] in _ancestors(tables[0]), "the table must live inside the disclosure it is toggled by"


def test_toggle_mode_uses_the_supplied_label_as_the_summary_text() -> None:
    out = _table(data_table_mode="toggle", toggle_label="Show the numbers")
    assert "Show the numbers" in out
    # Presence AND the absence of the fallback: without this second half the
    # test passes even if both the label and the default rendered.
    assert "View as table" not in out


def test_toggle_mode_falls_back_to_a_translated_default_when_the_label_is_blank() -> None:
    """A blank toggle_label would otherwise render an unlabelled <summary>:
    a focusable control with no accessible name (WCAG 4.1.2)."""
    out = _table(data_table_mode="toggle", toggle_label="   ")
    root = _parse(out)
    summary = _find_all(root, "summary")[0]
    assert "View as table" in out
    # Scoped to the summary's own subtree, so an occurrence elsewhere in the
    # document could not satisfy this.
    label_spans = [node for node in _walk(summary) if _has_class(node, "bw-disclosure__label")]
    assert label_spans, "the disclosure's label span must exist for the fallback to land in"


# --- the closed vocabulary (CHT-013, ADR-060 rule 2) -----------------------


def test_the_mode_vocabulary_is_exactly_the_three_documented_values() -> None:
    assert frozenset({"hidden", "toggle", "visible"}) == _CHART_DATA_TABLE_MODES


def test_an_unrecognised_mode_raises_naming_the_valid_values() -> None:
    with pytest.raises(TemplateSyntaxError) as excinfo:
        _table(data_table_mode="sideways")
    message = str(excinfo.value)
    assert "sideways" in message, "the error must name the value that was rejected"
    for valid in sorted(_CHART_DATA_TABLE_MODES):
        assert valid in message, f"the error must name the valid value {valid!r} so a caller can fix the call"


@pytest.mark.parametrize("mode", sorted(_CHART_DATA_TABLE_MODES))
def test_every_documented_mode_actually_renders(mode: str) -> None:
    """The other half of the vocabulary gate: a value the tag ACCEPTS must
    also reach a real branch. A mode accepted by the validator but unhandled
    by the template would render nothing at all and raise nowhere."""
    out = _table(data_table_mode=mode)
    assert _find_all(_parse(out), "table"), f"mode {mode!r} rendered no table at all"


# --- the caption is required, and is a real <caption> ----------------------


def test_a_missing_caption_is_a_render_error() -> None:
    with pytest.raises(TemplateSyntaxError):
        bw_chart_data_table(columns=COLUMNS, rows=ROWS)


def test_a_whitespace_only_caption_is_a_render_error() -> None:
    """A requirement that can be met with " " is not a requirement
    (bw_chart_mount's own aria_label precedent)."""
    with pytest.raises(TemplateSyntaxError):
        bw_chart_data_table(caption="   ", columns=COLUMNS, rows=ROWS)


def test_a_non_str_caption_is_coerced_rather_than_raising() -> None:
    """str() before .strip(), so a lazy translation proxy or an int does not
    raise AttributeError from a bare .strip(), which only str has
    (icvoss/django-brickwork#351's own defect, in this tag's shape)."""
    out = bw_chart_data_table(caption=gettext_lazy("Revenue"), columns=COLUMNS, rows=ROWS, data_table_mode="visible")
    assert "Revenue" in out


# --- the rows/columns shape is checked, because the wrong shape is silent --


def test_a_flat_list_passed_as_rows_raises_rather_than_rendering_single_letters() -> None:
    """The silent failure this check exists for: a flat list of values makes
    the template's {% for cell in row %} iterate each STRING's characters,
    rendering a table of single letters that errors nowhere and reads as a
    data bug rather than a call-site one."""
    with pytest.raises(TemplateSyntaxError) as excinfo:
        bw_chart_data_table(caption=CAPTION, columns=COLUMNS, rows=["January", "February"])
    assert "rows[0]" in str(excinfo.value), "the error must name the offending row's index"


def test_a_non_sequence_row_is_caught_at_a_non_first_position() -> None:
    """Violated at index 2, not 0: a check that only inspected rows[0] would
    pass a first-position fixture while letting every later row through."""
    rows = [["January", "120", "45"], ["February", "150", "60"], "March"]
    with pytest.raises(TemplateSyntaxError) as excinfo:
        bw_chart_data_table(caption=CAPTION, columns=COLUMNS, rows=rows)
    assert "rows[2]" in str(excinfo.value)


def test_a_non_sequence_columns_argument_raises() -> None:
    with pytest.raises(TemplateSyntaxError):
        bw_chart_data_table(caption=CAPTION, columns="Month", rows=ROWS)


def test_tuples_are_accepted_everywhere_lists_are() -> None:
    """The check must not narrow the contract to lists only: a queryset's
    values_list() yields tuples, which is an ordinary way to build these."""
    out = bw_chart_data_table(
        caption=CAPTION,
        columns=("Month", "Direct", "Referral"),
        rows=(("January", "120", "45"), ("February", "150", "60")),
        data_table_mode="visible",
    )
    root = _parse(out)
    assert len(_find_all(_find_all(root, "tbody")[0], "tr")) == 2


# --- the semantic contract: caption, scope="col", scope="row" --------------


def test_the_table_carries_a_real_caption_element_holding_the_caption_text() -> None:
    out = _table(data_table_mode="visible")
    root = _parse(out)
    table = _find_all(root, "table")[0]
    captions = _find_all(table, "caption")
    assert len(captions) == 1, "the accessible name must be a real <caption>, not a heading beside the table"
    assert captions[0] in _walk(table)
    assert CAPTION in out


def test_every_column_header_is_a_th_with_scope_col() -> None:
    out = _table(data_table_mode="visible")
    root = _parse(out)
    thead = _find_all(root, "thead")[0]
    headers = _find_all(thead, "th")
    assert len(headers) == len(COLUMNS), f"expected {len(COLUMNS)} column headers, found {len(headers)}"
    # Asserted for EVERY header, not the first: a template that hardcoded
    # scope="col" on only the first cell would pass a first-element check.
    for index, header in enumerate(headers):
        assert header["attrs"].get("scope") == "col", (  # type: ignore[union-attr]
            f"column header {index} ({COLUMNS[index]!r}) carries scope={header['attrs'].get('scope')!r}"  # type: ignore[union-attr]
        )


def test_every_rows_first_cell_is_a_th_with_scope_row_and_the_rest_are_td() -> None:
    out = _table(data_table_mode="visible")
    root = _parse(out)
    tbody = _find_all(root, "tbody")[0]
    body_rows = _find_all(tbody, "tr")
    assert len(body_rows) == len(ROWS), f"expected {len(ROWS)} body rows, found {len(body_rows)}"

    for row_index, tr in enumerate(body_rows):
        row_headers = _find_all(tr, "th")
        cells = _find_all(tr, "td")
        assert len(row_headers) == 1, (
            f"row {row_index} must have exactly one row header, found {len(row_headers)}: a second <th> would "
            "make the row's own coordinate ambiguous"
        )
        assert row_headers[0]["attrs"].get("scope") == "row", (  # type: ignore[union-attr]
            f"row {row_index}'s header carries scope={row_headers[0]['attrs'].get('scope')!r}"  # type: ignore[union-attr]
        )
        assert len(cells) == len(ROWS[row_index]) - 1, (
            f"row {row_index} should render {len(ROWS[row_index]) - 1} data cells beside its header"
        )


def test_the_table_is_inert_with_nothing_focusable_inside_it() -> None:
    """The chart beside it is the interactive surface; this is its transcript.
    A link, button or input in here would put a focus stop inside a
    visually-hidden region in the default mode, which is a keyboard trap by
    any other name."""
    out = _table(data_table_mode="hidden")
    root = _parse(out)
    table = _find_all(root, "table")[0]
    for tag in ("a", "button", "input", "select", "textarea"):
        assert not _find_all(table, tag), f"the fallback table must contain no <{tag}>"
    assert not _find_by_attr(table, "tabindex"), "the fallback table must add no tab stops"


# --- escaping: every consumer value lands in text position and is escaped --

_SCRIPT_PAYLOAD = "<script>alert(1)</script>"
_BREAKOUT_PAYLOAD = '" onmouseover="alert(1)'


@pytest.mark.parametrize("payload", [_SCRIPT_PAYLOAD, _BREAKOUT_PAYLOAD])
def test_a_hostile_caption_is_escaped_in_the_caption_element(payload: str) -> None:
    out = bw_chart_data_table(caption=payload, columns=COLUMNS, rows=ROWS, data_table_mode="visible")
    # PRESENCE first: proving the payload reached the render at all, so a
    # clean result cannot be an unexercised code path in disguise.
    assert "&lt;" in out or "&quot;" in out, "the payload must reach the render in escaped form"
    assert _SCRIPT_PAYLOAD not in out
    root = _parse(out)
    # convert_charrefs=True means the parser hands back the DECODED text, so
    # a payload that survived as live markup would appear as a real <script>
    # element in the tree rather than as text. That is the distinction a
    # substring check cannot draw.
    assert not _find_all(root, "script"), "the payload must never become a live element"
    assert not _find_by_attr(root, "onmouseover"), "the payload must never become a real event-handler attribute"


@pytest.mark.parametrize("payload", [_SCRIPT_PAYLOAD, _BREAKOUT_PAYLOAD])
def test_a_hostile_column_header_is_escaped_at_a_non_first_position(payload: str) -> None:
    """Violated at column index 2, not 0: a template escaping only the first
    header (or a helper handling only the first element) passes a
    first-position check vacuously."""
    columns = ["Month", "Direct", payload]
    out = bw_chart_data_table(caption=CAPTION, columns=columns, rows=ROWS, data_table_mode="visible")
    assert "&lt;" in out or "&quot;" in out
    assert _SCRIPT_PAYLOAD not in out
    root = _parse(out)
    assert not _find_all(root, "script")
    assert not _find_by_attr(root, "onmouseover")
    # And the header really is there, in the position under test.
    headers = _find_all(_find_all(root, "thead")[0], "th")
    assert len(headers) == 3


@pytest.mark.parametrize("payload", [_SCRIPT_PAYLOAD, _BREAKOUT_PAYLOAD])
def test_a_hostile_row_header_is_escaped_at_a_non_first_row(payload: str) -> None:
    """The row header is a <th>, a different interpolation site from the <td>
    below, and it is violated in the LAST row rather than the first."""
    rows = [["January", "120", "45"], ["February", "150", "60"], [payload, "180", "75"]]
    out = bw_chart_data_table(caption=CAPTION, columns=COLUMNS, rows=rows, data_table_mode="visible")
    assert "&lt;" in out or "&quot;" in out
    assert _SCRIPT_PAYLOAD not in out
    root = _parse(out)
    assert not _find_all(root, "script")
    assert not _find_by_attr(root, "onmouseover")
    body_rows = _find_all(_find_all(root, "tbody")[0], "tr")
    assert len(body_rows) == 3, "the hostile row must have rendered, not been dropped"


@pytest.mark.parametrize("payload", [_SCRIPT_PAYLOAD, _BREAKOUT_PAYLOAD])
def test_a_hostile_data_cell_is_escaped_at_a_non_first_cell_of_a_non_first_row(payload: str) -> None:
    rows = [["January", "120", "45"], ["February", "150", "60"], ["March", "180", payload]]
    out = bw_chart_data_table(caption=CAPTION, columns=COLUMNS, rows=rows, data_table_mode="visible")
    assert "&lt;" in out or "&quot;" in out
    assert _SCRIPT_PAYLOAD not in out
    root = _parse(out)
    assert not _find_all(root, "script")
    assert not _find_by_attr(root, "onmouseover")
    last_row_cells = _find_all(_find_all(_find_all(root, "tbody")[0], "tr")[-1], "td")
    assert len(last_row_cells) == 2, "the hostile cell must have rendered in its documented position"


@pytest.mark.parametrize("payload", [_SCRIPT_PAYLOAD, _BREAKOUT_PAYLOAD])
def test_a_hostile_toggle_label_is_escaped_inside_the_summary(payload: str) -> None:
    out = bw_chart_data_table(
        caption=CAPTION, columns=COLUMNS, rows=ROWS, data_table_mode="toggle", toggle_label=payload
    )
    assert "&lt;" in out or "&quot;" in out
    assert _SCRIPT_PAYLOAD not in out
    root = _parse(out)
    assert not _find_all(root, "script")
    assert not _find_by_attr(root, "onmouseover")
    assert _find_all(root, "summary"), "the summary must have rendered for the payload to have a position"


def test_a_plain_ampersand_in_a_caption_is_escaped_exactly_once() -> None:
    """The other direction of the double-escape trap. This tag passes consumer
    values to the template RAW precisely so the template's own auto-escaping
    is the single escape; pre-escaping in Python would show up here as
    "Tom &amp; Jerry" surviving the parser's decode as a literal "&amp;"."""
    out = bw_chart_data_table(caption="Tom & Jerry", columns=COLUMNS, rows=ROWS, data_table_mode="visible")
    assert "Tom &amp; Jerry" in out, "the raw ampersand must be escaped once by the template"
    assert "&amp;amp;" not in out, "a second escape round would double-encode it"


def test_a_safestring_caption_renders_its_markup_because_a_caption_is_text_position() -> None:
    """The position rule, stated as a test rather than left to a comment.

    A caption lands in TEXT position, where Django's auto-escaping honours
    __html__ and a mark_safe value renders as markup. That is the OPPOSITE of
    bw_chart_mount's aria_label, an ATTRIBUTE value, where the safe marker is
    meaningless and escape() runs unconditionally
    (test_safestring_is_escaped_again_because_an_attribute_is_not_markup in
    tests/test_chart_card.py pins that half). Identical-looking values,
    opposite treatment, decided entirely by the position the template puts
    them in.

    This is not a hole: a mark_safe caption is the caller vouching for its own
    markup under exactly the same rule that governs every other text-position
    slot in this package, and an ordinary consumer string (a DB value, a form
    field) is never SafeData and is escaped normally, which the hostile-payload
    tests above pin.
    """
    out = bw_chart_data_table(
        caption=mark_safe("Revenue <em>by month</em>"),  # noqa: S308
        columns=COLUMNS,
        rows=ROWS,
        data_table_mode="visible",
    )
    root = _parse(out)
    caption = _find_all(root, "caption")[0]
    assert _find_all(caption, "em"), "a text-position SafeString renders as markup, by the position rule"

    # And the pre-escaped-entity case round-trips without a second escape,
    # which is the double-escape trap this discipline avoids.
    out_entity = bw_chart_data_table(
        caption=format_html("Tom {} more", "&"), columns=COLUMNS, rows=ROWS, data_table_mode="visible"
    )
    assert "Tom &amp; more" in out_entity
    assert "&amp;amp;" not in out_entity


# --- the no-JS floor holds by construction in toggle mode ------------------


def test_toggle_mode_ships_no_javascript_at_all() -> None:
    """_disclosure.html registers no Alpine component and ships no script, so
    the no-JS floor is not "tested to work", it is unable to break
    (BR-BW-HTMX-001). Asserted over the rendered output: no <script>, no
    inline event handler, and no Alpine directive."""
    out = _table(data_table_mode="toggle")
    root = _parse(out)
    assert not _find_all(root, "script")
    for node in _walk(root):
        for name in node["attrs"]:  # type: ignore[union-attr]
            assert not name.startswith("on"), f"inline event handler {name!r} would make the floor JS-dependent"
            assert not name.startswith("x-"), f"Alpine directive {name!r} would make the floor JS-dependent"
            assert not name.startswith("hx-"), f"htmx attribute {name!r} would make the floor JS-dependent"
    # Presence half: the disclosure really rendered, so "no JS" is a statement
    # about a real <details>, not about an empty string.
    assert _find_all(root, "details")
    assert _find_all(root, "summary")


# --- THE STRUCTURAL ONE: the table is a SIBLING of the role="img" mount ----


def _card_with_mount_and_table(mode: str = "hidden") -> str:
    """A real _chart_card.html render carrying BOTH a populated mount and a
    fallback table, which is the only configuration in which the sibling
    contract can be observed at all."""
    mount = Template("{% load brickwork_components %}{% bw_chart_mount aria_label='Revenue by month' %}").render(
        Context({})
    )
    table = _table(data_table_mode=mode)
    return render_to_string("brickwork/components/_chart_card.html", {"mount": mount, "data_table": table})


@pytest.mark.parametrize("mode", sorted(_CHART_DATA_TABLE_MODES))
def test_the_fallback_table_is_not_a_descendant_of_the_role_img_mount(mode: str) -> None:
    """THE design decision this component exists around
    (icvoss/django-brickwork#326), pinned structurally.

    role="img" makes every descendant of the mount PRESENTATIONAL, so a
    <table> rendered inside the mount is unreachable to assistive technology
    no matter how well formed it is. The table must therefore be a SIBLING of
    the mount, never a descendant. Nesting it renders valid-looking markup,
    errors nowhere, and passes axe (which does not flag a name or a structure
    that is merely ignored), so nothing but this test would catch it.

    Asserted by PARSING and walking the ancestor chain, not by string
    matching: "the mount's markup appears before the table's" is text
    adjacency and would stay true under exactly the nesting this forbids.
    """
    root = _parse(_card_with_mount_and_table(mode))

    # Presence first, both halves: without this, a render that dropped either
    # element would satisfy the nesting assertion vacuously, which is the
    # single most likely way this test rots.
    mounts = _find_by_attr(root, "data-bw-chart-mount")
    assert len(mounts) == 1, f"expected exactly one chart mount in the card, found {len(mounts)}"
    assert mounts[0]["attrs"].get("role") == "img", (  # type: ignore[union-attr]
        "this test is only meaningful while the mount carries role=img; if that changes, the reason for "
        "the sibling rule changes with it and this test must be re-derived, not deleted"
    )
    tables = _find_all(root, "table")
    assert len(tables) == 1, f"expected exactly one fallback table in the card, found {len(tables)}"

    # The contract itself.
    assert mounts[0] not in _ancestors(tables[0]), (
        "the fallback table is a DESCENDANT of the role=img mount, so assistive technology cannot reach it: "
        "role=img makes every descendant presentational. It must be a sibling (CHT-012, "
        "icvoss/django-brickwork#326)."
    )


def test_the_structural_test_would_fail_if_the_table_were_nested_in_the_mount() -> None:
    """The teeth-check, in the suite rather than in a handover note: the same
    assertion, run against markup where the table IS nested inside the mount,
    must fail. Without this, a future refactor that broke _find_all or
    _ancestors would silently turn the test above into one that cannot fail.

    Built from the SERVER TEMPLATE's own shape rather than by cloning a live
    render, so it stays a statement about the markup this package emits.
    """
    nested = (
        '<div class="bw-chart-card">'
        '<div class="bw-chart-card__mount">'
        '<div class="bw-chart-mount" data-bw-chart-mount role="img" aria-label="Revenue by month">'
        '<table><caption>Revenue</caption><tbody><tr><th scope="row">Jan</th><td>1</td></tr></tbody></table>'
        "</div></div></div>"
    )
    root = _parse(nested)
    mount = _find_by_attr(root, "data-bw-chart-mount")[0]
    table = _find_all(root, "table")[0]
    assert mount in _ancestors(table), (
        "the helper must actually detect nesting; if this fails, the sibling test above cannot fail either"
    )


def test_the_card_renders_the_table_even_while_the_mount_shows_a_state() -> None:
    """The fallback sits outside chart_mount's state branching, so a loading
    or error card still carries its transcript: the table's data does not
    depend on the engine having painted."""
    table = _table(data_table_mode="visible")
    out = render_to_string("brickwork/components/_chart_card.html", {"loading": True, "data_table": table})
    root = _parse(out)
    assert _find_all(root, "table"), "the fallback table must survive the loading state"
    # Presence half for the state itself, so this is not passing because
    # loading silently did nothing.
    assert "bw-chart-card__skeleton" in out


def test_the_card_renders_no_fallback_markup_when_no_data_table_is_passed() -> None:
    """The unfilled-block convention: an omitted data_table leaves no empty
    fallback chrome behind, matching every other structural region here."""
    mount = Template("{% load brickwork_components %}{% bw_chart_mount aria_label='Revenue by month' %}").render(
        Context({})
    )
    out = render_to_string("brickwork/components/_chart_card.html", {"mount": mount})
    root = _parse(out)
    assert not _find_all(root, "table")
    assert "bw-chart-data-table" not in out
    # Presence half: the card really rendered.
    assert _find_by_attr(root, "data-bw-chart-mount")
