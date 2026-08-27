"""The quoted-figure helper must report the ref it measured, not the tree it ran in.

The counts themselves are gated elsewhere (``test_positioning.py`` checks the
shipped manifest against ``docs/POSITIONING.md``). What is tested here is the
property the helper exists for: a figure read from the working tree instead of
the ref it was asked for is the defect it prevents.

The fixture is a throwaway git repository built in a tmpdir, carrying two
commits whose token counts differ on every axis. It is constructed rather than
pinned to this repository's own history on purpose: every ``actions/checkout``
step in ``ci.yml`` takes the default ``fetch-depth: 1``, so real refs would be
absent in CI and the whole module would skip. **A skipped test is green**,
which is the failure mode this file is meant to be immune to, so the fixture
carries its own history and depends on nothing outside the tmpdir.

Two differing commits is the load-bearing part (#286: the fixture must be able
to express the violation). A helper that ignored its ref argument and read the
checkout would agree with at most one of them, so it fails rather than passing
by coincidence.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from token_figures import figures  # noqa: E402

# Deliberately different on every axis the helper reports, so no assertion
# below can be satisfied by the wrong commit.
_OLD = {
    "css": ":root{--bw-a:1;--bw-b:2;}",
    "manifest": {
        "overridable": ["--bw-a", "--bw-b"],
        "loadBearing": [{"name": "--bw-a"}],
        "contrastPairs": [],
    },
}
_NEW = {
    "css": ":root{--bw-a:1;--bw-b:2;--bw-c:3;}[data-theme=dark]{--bw-a:9;}",
    "manifest": {
        "overridable": ["--bw-a", "--bw-b", "--bw-c"],
        "loadBearing": [{"name": "--bw-a"}, {"name": "--bw-c", "conditional": True}],
        "contrastPairs": [{"fg": "--bw-a", "bg": "--bw-b"}],
    },
}


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A throwaway repo with two commits whose token counts differ."""
    root = tmp_path_factory.mktemp("token-figures-fixture")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")

    css = root / "src/brickwork/static/brickwork/dist/tokens.css"
    manifest = css.parent / "token-manifest.json"
    css.parent.mkdir(parents=True)

    for state, message in ((_OLD, "old"), (_NEW, "new")):
        css.write_text(state["css"])
        manifest.write_text(json.dumps(state["manifest"]))
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", message)
    return root


@pytest.fixture(scope="module")
def refs(repo: Path) -> tuple[str, str]:
    log = _git(repo, "log", "--format=%H").splitlines()
    return log[1], log[0]  # oldest first


def _figures_in(repo: Path, ref: str) -> dict[str, object]:
    """Run the helper with ``repo`` as the working directory."""
    original = Path.cwd()
    try:
        os.chdir(repo)
        return figures(ref)
    finally:
        os.chdir(original)


def test_the_two_fixture_commits_really_do_differ(repo: Path, refs: tuple[str, str]) -> None:
    """Guard the fixture itself: if these agree, every test below is vacuous."""
    old, new = (_figures_in(repo, r) for r in refs)
    for key in ("unique", "overridable", "load_bearing", "contrast_pairs"):
        assert old[key] != new[key], (
            f"{key} is equal across the fixture commits, so this fixture can no "
            "longer catch a helper that ignores its ref argument"
        )


def test_figures_report_the_ref_they_were_asked_for(repo: Path, refs: tuple[str, str]) -> None:
    """The ref travels with the numbers; that is the whole point of the helper."""
    for ref in refs:
        result = _figures_in(repo, ref)
        assert result["ref"] == ref
        assert result["sha"], "no sha resolved, so the figure carries no provenance"
        assert ref.startswith(str(result["sha"]))


def test_figures_read_the_requested_ref_not_the_working_tree(repo: Path, refs: tuple[str, str]) -> None:
    """The defect this helper exists to prevent, asserted directly.

    The working tree is left at the newer commit throughout. If ``figures()``
    ever reads the checkout instead of the ref it was given, the older ref
    comes back with the newer commit's numbers.
    """
    old_ref, new_ref = refs
    old = _figures_in(repo, old_ref)
    new = _figures_in(repo, new_ref)

    assert old["unique"] == 2
    assert old["overridable"] == 2
    assert old["load_bearing"] == 1
    assert old["contrast_pairs"] == 0

    assert new["unique"] == 3
    assert new["overridable"] == 3
    assert new["load_bearing"] == 2
    assert new["contrast_pairs"] == 1


def test_unconditional_excludes_flagged_entries(repo: Path, refs: tuple[str, str]) -> None:
    """``unconditional`` is the load-bearing subset without a conditional flag."""
    new = _figures_in(repo, refs[1])
    assert new["load_bearing"] == 2
    assert new["unconditional"] == 1


def test_an_unknown_ref_fails_loudly_rather_than_falling_back(repo: Path) -> None:
    """A silent fallback to the working tree is the failure mode to avoid."""
    with pytest.raises(SystemExit):
        _figures_in(repo, "definitely-not-a-ref")


def test_the_printed_output_carries_the_ref(repo: Path, refs: tuple[str, str]) -> None:
    """The command's OUTPUT is the product, not the dict it returns internally.

    Everything above tests ``figures()``. What a person actually copies into a
    pull request body is what ``main()`` prints, so that path gets its own
    check: a helper whose return value carried the ref while its output did
    not would satisfy every other test here and fail at the only moment that
    matters.
    """
    old_ref, new_ref = refs
    script = Path(__file__).resolve().parents[1] / "scripts" / "token_figures.py"
    result = subprocess.run(
        [sys.executable, str(script), old_ref],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert old_ref[:7] in result.stdout, "the ref does not appear in the output"
    assert "unique --bw-*   2" in result.stdout
    assert "overridable     2" in result.stdout

    newer = subprocess.run(
        [sys.executable, str(script), new_ref],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert new_ref[:7] in newer.stdout
    assert "unique --bw-*   3" in newer.stdout
    assert newer.stdout != result.stdout, (
        "both refs printed identical output, so the printed figures do not track the ref they were asked for"
    )
