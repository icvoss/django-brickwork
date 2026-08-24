"""bwSortable bundle-contract tests (icvoss/django-brickwork#214).

bwSortable ships no brickwork-owned template: the DOM (a consumer's own
<ul>/<li> list) is consumer-owned, per sortable.js's own "DOM contract"
comment, so there is no {% bw_sortable %} tag to exercise the way
test_dropdown.py exercises {% bw_dropdown %}. What IS covered here is the
same static leg every other Alpine behaviour in this package carries in its
own test module (test_dropdown.py, test_components.py, test_modal.py,
test_tabs.py, test_toast.py, test_slide_over.py, test_combobox.py): the
compiled bundle must carry the semver-public component name (BR-BW-JS-004)
and its documented bw:-namespaced event name (BR-BW-HTMX-004), so a rename
or a dropped registration line is caught here rather than only at runtime.
"""

from __future__ import annotations

from pathlib import Path

_DIST_JS = Path(__file__).resolve().parent.parent / "src/brickwork/static/brickwork/dist/brickwork.js"


def test_bundle_registers_bwsortable_and_emits_the_reorder_event() -> None:
    # AC-BW-033/AC-BW-087-style static leg: the compiled bundle carries the
    # semver-public component name and its documented bw: event name.
    bundle = _DIST_JS.read_text()
    assert "bwSortable" in bundle
    assert "bw:sortable:reorder" in bundle


def test_bundle_never_starts_alpine_for_sortable() -> None:
    # BR-BW-JS-002: bwSortable never calls Alpine.start() itself; the host
    # owns initialisation. Covered package-wide already by
    # test_components.py::test_bundle_never_starts_alpine_and_ships_no_sui_namespace,
    # re-asserted here so this file stands alone as bwSortable's contract
    # record.
    bundle = _DIST_JS.read_text()
    assert "Alpine.start(" not in bundle
