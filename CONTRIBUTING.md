# Contributing to django-brickwork

Practical guide for contributors working on this package.

---

## Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Django 6.0 or later (installed as part of the dev setup)
- No database server is required: the test suite uses SQLite
- Node (npm) only if you rebuild the shipped static assets; see
  `frontend/README.md`

---

## Local Development Setup

```bash
git clone https://github.com/icvoss/django-brickwork.git
cd django-brickwork

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

Or with uv:

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

---

## Running Tests

```bash
pytest tests/ -v --tb=short
```

Test configuration lives in `[tool.pytest.ini_options]` in `pyproject.toml`,
so no environment variables are needed.

---

## Code Standards

All Python code is linted and formatted with [ruff](https://docs.astral.sh/ruff/),
configured in `pyproject.toml`.

| Setting | Value |
|---------|-------|
| Line length | 120 |
| Quote style | Double |
| Target Python | 3.12 |

```bash
# Check for lint errors
ruff check .

# Check formatting (no writes)
ruff format --check .

# Apply formatting
ruff format .
```

CI will fail if either check reports errors. Run both before pushing.

### Accessibility spec linting

The `a11y/**/*.spec.mjs` Playwright specs are linted separately with ESLint
and `eslint-plugin-playwright` (`eslint.config.mjs`, scoped to that
directory only; this is not general JS linting for the repo).

```bash
npm run a11y:lint
```

The rule set targets one specific defect class: a synchronous matcher
wrapping an async callback, most often `expect(async () => {...}).not.toThrow()`,
makes an assertion that cannot fail. `.not.toThrow()` checks whether the
*call* threw, not whether the returned promise rejects, so the unawaited
work inside the callback leaks past test teardown and surfaces later as
`Error: page.evaluate: Test ended`, which reads as infrastructure flake
rather than the assertion bug it is. `playwright/no-restricted-matchers`
bans `toThrow`/`not.toThrow` outright for this reason.
`playwright/missing-playwright-await` and `playwright/valid-expect-in-promise`
catch the related shapes of a missing `await` on a Playwright matcher or an
unreturned `.then()` chain carrying an `expect()`. See icvoss/django-brickwork#276.

CI runs this as its own step in the `a11y-gate` job. Run it locally before
pushing if you touch a spec file.

### Figures and claims about the codebase

**A change that moves a figure or a claim about the codebase updates every
occurrence of it, gated and ungated. The gated one is not the check.**

Several documents state facts about what the package contains: token counts,
fixture counts, "every X does Y", "component A already uses B". A few of those
are gated by a test that derives them from a shipped artefact. Most are not,
and the ungated ones sit in the same sentence, the same table, or the file
next door.

The failure is not forgetting the figure. It is fixing the gated one, watching
the suite go green, and reading that as the figure being handled. It is not:
the gate covers the occurrence it was written for, and says nothing about the
prose beside it.

This is not only about numbers. A claim about a set ("every other interactive
control already meets this floor") and a claim about a mechanism ("`_x.html`
already uses that passthrough") rot the same way and are harder to spot,
because nothing about them looks like a fact that could go stale.

**Five instances were found in a single day, in one package. None was caught
by a gate. Every one was caught by grepping for the old value and reading each
hit.** One had been wrong since 3.11.0, across two shipped releases, because
the maintained figure beside it moved and it did not. Another appeared in a
3.12.0 release note, describing a passthrough that the component it named did
not have at the tag.

This governs a fresh changelog fragment exactly as much as it governs
editing an existing figure: a fragment that compares the new thing to another
component's current behaviour is making a claim about a document, and nothing
about writing it for the first time exempts it from the rule below
(icvoss/django-brickwork#315).

When you change something a document counts or describes, or write a fragment
that compares against something you did not change:

- Grep for the old value or phrasing across `docs/`, `README.md`,
  `CONTRIBUTING.md` and `CHANGELOG.md`, and read every hit rather than
  replacing blind. Some are dated historical snapshots that must stay as they
  are.
- Derive figures from the shipped artefact rather than editing them by hand,
  and read that artefact at an explicit git ref rather than from your working
  tree. A worktree that is behind, mid-edit, or on another branch produces a
  correct measurement of the wrong tree, which is how most of these got
  published. Quote the ref with the number: a figure without it cannot be
  checked by anyone else, even when it is right.
- If a claim asserts the behaviour of code your change does not touch, verify
  it, drop it, or cite the issue or ADR that established the convention
  instead of describing the other component's implementation from memory (the
  3.12.0 entry's "matching the existing no-JS floor (#117)" is this shape,
  and held up where the two claims corrected under #315 did not). At the
  time of writing, the claim about your own change is checked by the work in
  front of you and the claim about the other thing is recalled, and nothing
  re-checks the recalled half before it ships; a citation stays correct as
  the other component changes, a description of its current state does not.

---

## Repository Structure

```
django-brickwork/
    src/brickwork/      # importable package
    frontend/           # in-repo build for the shipped static assets
    a11y/               # Playwright + axe-core accessibility gate
    tests/
        settings.py     # Django settings for the test suite
        conftest.py
        test_*.py
    pyproject.toml      # package metadata, dependencies, tool config
    changelog.d/        # one changelog fragment per change (see its README)
    CHANGELOG.md
    README.md
    RELEASING.md
```

---

## Git Workflow

### Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>
```

| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `chore` | Maintenance, version bumps, dependency updates |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `style` | Formatting, whitespace, no logic change |
| `refactor` | Code change that is neither a fix nor a feature |

### Branches and PRs

Push feature branches and open a pull request against `main`. CI must pass
before merging. Prefer small, focused commits over large ones.

### Changelog fragments (not CHANGELOG.md)

A feature branch **never edits `CHANGELOG.md`**. Add one file per change under
`changelog.d/` named `<issue-or-slug>.<added|changed|fixed|removed>.md`, whose
body is the entry as markdown list items. See `changelog.d/README.md`.

Parallel branches all editing one `[Unreleased]` block conflict on every merge
and get union-resolved into the wrong sections
(icvoss/django-brickwork#113); separate fragment files cannot conflict. The
release PR assembles them.

---

## Releasing

See [RELEASING.md](RELEASING.md) for the full release process. The short
version:

1. Bump the version in `pyproject.toml` and `src/brickwork/__init__.py`.
2. Assemble the changelog: `python scripts/assemble_changelog.py <version>`,
   then edit the generated section by hand.
3. Open a PR, get it reviewed, and merge to `main`.
4. Tag the merged commit and push the tag:

   ```bash
   git tag v<version>
   git push origin v<version>
   ```

The tag push triggers the CI publish workflow automatically.
