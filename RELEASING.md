# Releasing

How to cut a release for django-brickwork.

## TL;DR

```
branch  ->  PR  ->  review  ->  merge to main  ->  tag the merged commit  ->  CI publishes
```

The **tag is the trigger**. Pushing a tag of the form `v<semver>` runs the
publish workflow (`publish.yml`), which tests, builds, and uploads to **public
PyPI** via OIDC trusted publishing. No API token and no Actions secret are
involved: the workflow exchanges a short-lived OIDC token, and the trusted
publisher is configured in the PyPI project settings.

brickwork graduated from the private index (`pypi.icvoss.com`, ADR-020) to
public PyPI. This document previously described the private flow, which no
longer applies to this package.

CI refuses to publish without a CHANGELOG entry matching the version, so a
missing entry fails the run before any upload. **Tagging is publishing. There is
no separate "publish" step, no undo, and a version number on PyPI can never be
reused.**

## Canonical flow

1. **Branch** off `main`:
   `release/<version>` (e.g. `release/0.5.0`).
2. **Bump** on the branch:
   - `pyproject.toml` - update `version`
   - `src/brickwork/__init__.py` - update `__version__` (keep in sync)
   - `CHANGELOG.md` - rename `[Unreleased]` to `[<version>] - <YYYY-MM-DD>`
3. **Open a PR** to `main`. CI runs lint and tests. Get it reviewed. This is
   the gate, do not skip it.
4. **Merge to `main`** (squash or merge, per repo norm).
5. **Tag the merged commit on `main`** and push the tag:
   ```bash
   git checkout main && git pull
   git tag v<version>
   git push origin v<version>
   ```
6. **Watch the publish run** and confirm PyPI:
   ```bash
   gh run watch <run-id> --exit-status
   # confirm the version landed on public PyPI (add --pre for an rc):
   pip index versions django-brickwork
   ```

> **Tag the commit that is on `main`, not a feature branch.** Tags point at
> commits, not branches, so tagging a feature branch *will* publish, but it
> publishes code that may never have been merged. Always tag after the merge so
> what is on PyPI is exactly what is on `main`.

## Tag format (strict)

`v<semver>`: the letter `v` followed by the version number. The publish
workflow matches `v*` and parses the version from after `v`.

| Version | Tag example |
| --- | --- |
| 0.5.0 | `v0.5.0` |
| 1.0.0 | `v1.0.0` |
| 1.2.3 | `v1.2.3` |

## Versioning (SemVer)

[Semantic Versioning](https://semver.org/). Pre-1.0, the rules still apply
with the usual pre-1.0 caveat that minor bumps may carry breaking changes:

- **Patch** (`0.4.0 -> 0.4.1`): bug fixes, doc-only changes, no API or
  behaviour change.
- **Minor** (`0.4.1 -> 0.5.0`): new public API, **any behaviour change** (even
  a safer one), or a raised minimum dependency floor (e.g. Django).
- **Major** (`0.x -> 1.0`): the stability commitment; breaking changes after
  1.0.

If in doubt between patch and minor, choose minor. Burning a version number is
free; shipping a behaviour change as a patch surprises consumers.

## CHANGELOG (required, every release)

**A release MUST include a CHANGELOG entry for its version. No entry, no tag.**
Every published version needs a dated section in `CHANGELOG.md`. CI enforces
this: the publish workflow will fail if no matching `## [<version>]` heading
exists.

[Keep a Changelog](https://keepachangelog.com/) format. Subsections: Added /
Changed / Fixed / Removed. Call out behaviour changes explicitly, including
ones that are "safer", because a consumer relying on the old behaviour still
needs to know.

### Feature branches write fragments, not CHANGELOG.md

**A feature branch never edits `CHANGELOG.md`.** It adds one file under
`changelog.d/` instead:

```
changelog.d/<issue-or-slug>.<added|changed|fixed|removed>.md
```

The file body is the entry as it should appear, as markdown list items, with no
section heading. Full rules and examples: `changelog.d/README.md`.

This exists because the 1.4.0 wave ran six parallel branches that all appended
to the same `## [Unreleased]` block, so every merge hit a conflict in a file
where nothing had actually disagreed, and union-resolving those conflicts
silently filed new capabilities under `Fixed`
(icvoss/django-brickwork#113). Two fragments are two different files, so they
merge without ever being compared.

### The release PR assembles them

In the release PR only:

```bash
python scripts/assemble_changelog.py <version>
```

That groups every fragment by type, writes the dated `## [<version>]` section
into `CHANGELOG.md`, and deletes the fragments it consumed. **Edit the
generated section by hand afterwards**: it is a starting point, and a release
usually wants a summary paragraph that no individual fragment could write.

The GitHub release body is auto-generated from the tag, but that is **not** a
substitute for the curated CHANGELOG entry. Write the CHANGELOG by hand so
consumers reading the package on PyPI or GitHub get a human-authored summary,
not just a commit list.

## Version locations

The version lives in exactly two places. Both must match at the time of
tagging:

- `pyproject.toml` under `[project]` -> `version`
- `src/brickwork/__init__.py` -> `__version__`

## Keep the CI Django pin in step with the floor

The publish workflow's test job pins `Django~=5.2.0`. When you raise the
minimum Django in `pyproject.toml`, **update the pin in the same PR**, or the
tagged build's test job can fail to resolve dependencies and block the publish.

## Consumer smoke-test gate (Django packages, ADR-027)

CI carries a `smoke-test` job that installs this package **as a built wheel**
into a fresh venv and runs the checks a real consumer runs against a throwaway
consumer project: `makemigrations --check --dry-run`, a fresh-DB `migrate`, and
`mypy` with the `django-stubs` plugin. This exists because two published
versions (icv-identity 0.3.0's unmigrated manager change; the boundary /
icv-identity django-stubs wall) shipped defects only a real consumer surfaced,
after release. The gate moves those to "caught before the tag".

- **The gate is blocking.** A red `smoke-test` blocks the PR, so it blocks the
  release (tagging is gated on a green `main`).
- **Declared mypy / django-stubs pair.** This package typechecks clean against a
  specific `mypy` + `django-stubs` pair, declared in the `[dev]` extra of
  `pyproject.toml` and pinned by the smoke-test job. Consumers pin the same pair.
  Current pair: `mypy 1.10+ + django-stubs (Django 6.0.x)` (e.g. `mypy 1.19.x` + `django-stubs 5.2.x`).
- **Advisory `mypy` leg (temporary).** If this package does not yet typecheck
  clean in a consumer, the `mypy` leg runs `continue-on-error: true` and this
  line records that it is advisory. The `makemigrations --check` and `migrate`
  legs are blocking regardless. Flip the `mypy` leg to blocking in the same
  release that ships the typing fix, and delete this bullet.

## Pre-tag checklist

Before pushing the tag (the irreversible step):

- [ ] **CHANGELOG has a `[<version>] - <date>` entry** (assembled from
      `changelog.d/` via `scripts/assemble_changelog.py`, then edited by hand).
      This is mandatory.
- [ ] `changelog.d/` holds no leftover fragments for this release (the
      assembler deletes what it consumes; anything still there was missed).
- [ ] Behaviour changes and breaking changes called out in that CHANGELOG entry.
- [ ] Version bumped in `pyproject.toml` **and** `src/brickwork/__init__.py`,
      and they match.
- [ ] CI Django pin matches the package's minimum, if the floor changed.
- [ ] **Consumer smoke-test green** (`makemigrations --check`, `migrate`, and
      `mypy` where blocking) — see the smoke-test gate section above (ADR-027).
- [ ] Tests pass locally and the package builds (`python -m build`).
- [ ] The PR is **merged to `main`** and you are tagging that commit.
- [ ] Tag format is `v<version>`.
- [ ] This exact version has never been published (PyPI rejects re-uploads).

## If something goes wrong

- **PyPI rejects the upload (version exists).** That version is permanently
  taken. You cannot re-upload, even after deleting. Bump to the next patch
  and re-tag.
- **The test or build job fails after tagging.** Nothing was published (publish
  is the last job and depends on test and build). Fix on a new PR, merge,
  delete the bad tag (`git push --delete origin v<version>`), and re-tag the
  new commit with the **same** version (since nothing reached PyPI).
- **Published, but the code is not on `main`.** Open a PR from the release
  branch to `main` immediately and merge, so `main` reflects what is on PyPI.
  Avoid this by always tagging after the merge.

## Optional hardening

Consider adding a **manual approval gate** to the `publish` job via a
protected GitHub Environment (`pypi`), so "push tag" and "irreversibly upload
to PyPI" are decoupled. A human approves the upload after seeing test and
build go green. The workflow already declares `environment: pypi`; add a
required-reviewer protection rule to that environment to enable the gate.
