#!/usr/bin/env python3
"""Fail a PR that changes a component template or adds a template tag with no fragment.

Run in a PR, against the merge base with the PR's target branch (icvoss/django-brickwork#375):

    python scripts/check_changelog_fragment_required.py <base-ref> [<head-ref>]

``<base-ref>`` and ``<head-ref>`` default to ``origin/main`` and ``HEAD``, which
is what the CI job passes. A PR needs a ``changelog.d/`` fragment when the diff
between the merge base and the head EITHER:

  a) adds, modifies, or deletes a file matching
     ``src/brickwork/templates/brickwork/components/*.html``, or
  b) adds a line matching a ``@register.`` decorator anywhere under
     ``src/brickwork/templatetags/`` (added lines only: a reformat or a house
     move of an existing tag does not trip this, only a genuinely new
     registration does).

The gate is satisfied by the diff ADDING at least one file under
``changelog.d/`` that is not ``changelog.d/README.md``.

Why this exists: v3.13.0 shipped four capabilities (three new component
templates plus a new template tag) and named none of them in the CHANGELOG,
because none of those PRs added a fragment (icvoss/django-brickwork#361). A
release-time check on ``changelog.d/`` cannot catch this class of miss,
because it can only see fragments that exist; a capability that never wrote
one is invisible to it. This is the load-bearing half: it runs at the point
the capability is introduced, before the missing fragment has any chance to
go unnoticed.

Escape hatch: a PR that genuinely changes no user-visible behaviour (a pure
refactor of a component's internal markup, a template tag renamed and
re-registered with no behaviour change already covered by an existing
fragment) may opt out by adding the exact line
``changelog-fragment-not-required`` to the PR body. The marker must stand
ALONE on its own line: prose merely mentioning it does not waive the gate
(icvoss/django-brickwork#380). This is deliberately the
only mechanism, and deliberately narrow: it requires a human decision recorded
in the PR body itself, visible in review, greppable in PR history, and not
satisfiable by accident (unlike an empty fragment file, which would pollute
``changelog.d/`` and later break ``assemble_changelog.py``'s
"fragment is empty" check).

Deliberately dependency-free (stdlib only), shelling out to ``git`` the same
way ``generate_template_manifest.py`` shells out to nothing and
``assemble_changelog.py`` reads the filesystem directly: this script's real
dependency is git plumbing, not a library wrapping it.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

COMPONENT_TEMPLATE_RE = re.compile(r"^src/brickwork/templates/brickwork/components/[^/]+\.html$")
TEMPLATETAGS_PATH_PREFIX = "src/brickwork/templatetags/"
REGISTER_DECORATOR_RE = re.compile(r"^@register\.")
OPT_OUT_MARKER = "changelog-fragment-not-required"


def opt_out_requested(pr_body: str) -> bool:
    """True only when the marker stands alone on a line of the PR body.

    A substring test (``OPT_OUT_MARKER in pr_body``) waives the gate for any
    PR whose body merely MENTIONS the marker, including a PR discussing this
    gate or quoting the failure message the gate itself prints
    (icvoss/django-brickwork#380). The docstring above has always said "the
    exact line"; this is the check that makes that true.

    Surrounding whitespace is tolerated because a body is human-typed and a
    trailing space is not a decision. Anything else on the line is not,
    because that is the prose case the substring test could not tell apart.
    """
    return any(line.strip() == OPT_OUT_MARKER for line in pr_body.splitlines())


def run_git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout


def merge_base(base_ref: str, head_ref: str) -> str:
    return run_git("merge-base", base_ref, head_ref).strip()


def changed_paths(merge_base_sha: str, head_ref: str) -> list[str]:
    """Every path added, modified, or deleted between the merge base and head."""
    output = run_git("diff", "--name-only", f"{merge_base_sha}..{head_ref}")
    return [line for line in output.splitlines() if line]


def added_lines_by_path(merge_base_sha: str, head_ref: str, path_prefix: str) -> dict[str, list[str]]:
    """Map path -> list of ADDED lines (unified diff '+' lines, header excluded).

    Restricted to ``path_prefix`` so the diff invocation stays small; a
    templatetags-only change is a small tree.
    """
    output = run_git(
        "diff",
        "--unified=0",
        f"{merge_base_sha}..{head_ref}",
        "--",
        path_prefix,
    )
    added: dict[str, list[str]] = {}
    current_path = None
    for line in output.splitlines():
        if line.startswith("+++ "):
            raw = line[4:]
            current_path = None if raw == "/dev/null" else raw.removeprefix("b/")
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+") and current_path is not None:
            added.setdefault(current_path, []).append(line[1:])
    return added


def new_changelog_fragments(merge_base_sha: str, head_ref: str) -> list[str]:
    """Paths under changelog.d/ that the diff ADDS (status A), excluding README.md."""
    output = run_git(
        "diff",
        "--name-only",
        "--diff-filter=A",
        f"{merge_base_sha}..{head_ref}",
        "--",
        "changelog.d/",
    )
    return [line for line in output.splitlines() if line and line != "changelog.d/README.md"]


def read_pr_body() -> str:
    """The PR body, if the workflow provided one via PR_BODY; empty otherwise.

    Read from an environment variable rather than the GitHub API so this
    script has no network dependency and stays runnable offline.
    """
    return os.environ.get("PR_BODY", "")


def main(argv: list[str]) -> int:
    base_ref = argv[1] if len(argv) > 1 else "origin/main"
    head_ref = argv[2] if len(argv) > 2 else "HEAD"

    base_sha = merge_base(base_ref, head_ref)

    changed = changed_paths(base_sha, head_ref)
    component_template_hits = sorted(p for p in changed if COMPONENT_TEMPLATE_RE.match(p))

    added_by_path = added_lines_by_path(base_sha, head_ref, TEMPLATETAGS_PATH_PREFIX)
    new_tag_hits = sorted(
        path
        for path, lines in added_by_path.items()
        if any(REGISTER_DECORATOR_RE.match(line.strip()) for line in lines)
    )

    if not component_template_hits and not new_tag_hits:
        print("No component template or new template-tag registration in this diff. No fragment required.")
        return 0

    fragments = new_changelog_fragments(base_sha, head_ref)
    if fragments:
        print(f"Fragment(s) found: {', '.join(fragments)}. Gate satisfied.")
        return 0

    if opt_out_requested(read_pr_body()):
        print(f"'{OPT_OUT_MARKER}' present in the PR body. Fragment requirement waived.")
        return 0

    reasons = []
    if component_template_hits:
        reasons.append("  - component template(s) changed: " + ", ".join(component_template_hits))
    if new_tag_hits:
        reasons.append("  - new @register. template tag added in: " + ", ".join(new_tag_hits))

    print(
        "ERROR: this PR touches user-visible surface but adds no changelog.d/ "
        "fragment.\n\n"
        "Triggered by:\n" + "\n".join(reasons) + "\n\n"
        "Add a fragment: create changelog.d/<issue-or-slug>.<type>.md, where "
        "<type> is one of added, changed, fixed, removed. See "
        "changelog.d/README.md for the content rules.\n\n"
        f"If this change genuinely has no user-visible effect (a pure "
        f"refactor), opt out by adding the exact line '{OPT_OUT_MARKER}' to "
        "the PR body instead.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
