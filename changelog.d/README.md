# changelog.d: one fragment per change

Every user-visible change adds a **new file here** instead of editing
`CHANGELOG.md`. At release time the fragments are assembled into the release's
`CHANGELOG.md` section and deleted. See RELEASING.md, "CHANGELOG".

## Why (icvoss/django-brickwork#113)

The 1.4.0 wave ran six parallel feature branches. Every one of them appended to
the same `## [Unreleased]` block in `CHANGELOG.md`, so every one of them
conflicted with every other on merge: six separate conflict resolutions for a
file where nothing had genuinely disagreed. Worse, resolving those conflicts by
taking the union silently mis-sectioned new capabilities under `Fixed`, because
the resolver was reconciling text, not meaning.

A fragment per change cannot conflict: two branches adding two changes add two
different files. Git merges them without ever comparing their contents.

## Naming

```
changelog.d/<issue-or-slug>.<type>.md
```

- `<issue-or-slug>`: the issue number driving the change (`113`), or a short
  kebab-case slug when there is no issue (`examples-tree`).
- `<type>`: one of `added`, `changed`, `fixed`, `removed`. This is what decides
  the section the entry lands in, so it is chosen by the person who wrote the
  change, not by whoever assembles the release. That is the whole point.

Examples:

```
changelog.d/110.fixed.md
changelog.d/98.added.md
changelog.d/examples-tree.added.md
```

## Content

The body of the file is the entry exactly as it should appear in the CHANGELOG,
as one or more markdown list items, without the section heading:

```markdown
- **Dev extra pins ruff to the CI version** (icvoss/django-brickwork#110). The
  `[dev]` extra allowed any `ruff>=0.5.0` while CI installed exactly
  `0.15.22`, so a local `ruff format` could reformat files the pinned version
  formats differently and produce drift with no source change.
```

House style applies: British English, no em or en dashes, issues referenced as
`icvoss/django-brickwork#N`, no session links. A fragment comparing your
change to another component's current behaviour is bound by CONTRIBUTING.md,
"Figures and claims about the codebase" (icvoss/django-brickwork#315): verify
it, drop it, or cite what landed instead (the merge commit, the PR, or
the tag it shipped in). An issue number names a request, not a change:
a reader following it cannot tell whether the thing landed or in what
form. Cite an issue or ADR only when the claim is about a convention it
establishes rather than about code.

## Assembling a release

`python scripts/assemble_changelog.py <version>` reads every fragment, groups
by type into Added / Changed / Fixed / Removed, writes the dated section into
`CHANGELOG.md` above the previous release, and deletes the consumed fragments.
Run it in the release PR, review the generated section by hand (it is a
starting point, not a finished entry: a release usually wants a summary
paragraph the fragments cannot write), then commit.
