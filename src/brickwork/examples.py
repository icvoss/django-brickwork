"""Read access to the shipped copy-paste example pages (ADR-056, 2.0.0).

brickwork ships three things as a versioned library: the CSS/token layer, the
components, and the shells. A **whole page** is none of them: it is the single
most project-specific thing a Django developer owns, so brickwork ships pages
as **copy-paste examples the consumer owns outright**, never as an importable,
extendable contract (ADR-056 sections 1 and 2).

That distinction is enforced structurally, not by documentation. The examples
live in ``src/brickwork/examples/``, which is package data, **not** an app
``templates/`` directory. Django's ``APP_DIRS`` loader only walks
``<app>/templates/``, so no configuration of a consumer's project can resolve
``{% extends "brickwork/examples/..." %}``: the loader simply cannot see them.
The only way to use an example is to open it and copy it, which is exactly the
intent (ADR-056 section 3).

This module is the supported way to READ that tree from an installed package,
for tooling that needs the source: principally the brickwork gallery, which
renders each example's source straight from the wheel it has installed, so the
published examples and the documented examples structurally cannot drift.

    >>> from brickwork import examples
    >>> "landing" in examples.list_examples()
    True
    >>> source = examples.read_example("marketing/landing.html")

Nothing here reads Django settings or touches the template engines, so it is
safe to import before ``django.setup()``.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["EXAMPLES_ROOT", "ExampleNotFoundError", "examples_root", "list_examples", "read_example"]


class ExampleNotFoundError(LookupError):
    """Raised when a requested example name is not in the shipped tree.

    Subclasses ``LookupError`` rather than ``KeyError`` for the reason
    ``IconNotFoundError`` does (icvoss/django-brickwork#74): a ``KeyError``
    raised inside a template variable resolution is swallowed by Django's
    lookup machinery and re-surfaces as a silently empty string, turning a
    typo into invisible missing output instead of a loud failure.
    """


EXAMPLES_ROOT = Path(__file__).resolve().parent / "examples"


def examples_root() -> Path:
    """Return the directory holding the shipped examples.

    Provided as a function as well as the ``EXAMPLES_ROOT`` constant because a
    caller that wants to render the examples (the gallery, and this package's
    own drift tests) builds a standalone template ``Engine`` pointed at this
    directory. That is the ONLY supported way to render an example, and it is
    deliberately something the caller must do explicitly: pointing a project's
    own configured loaders here would re-create the extendable-page contract
    ADR-056 retires.
    """
    return EXAMPLES_ROOT


def list_examples() -> list[str]:
    """Return every shipped example's name, sorted.

    Names are POSIX-style paths relative to the examples root, including the
    ``.html`` suffix, e.g. ``"base.html"``, ``"app/list.html"``,
    ``"marketing/landing.html"``.
    """
    return sorted(path.relative_to(EXAMPLES_ROOT).as_posix() for path in EXAMPLES_ROOT.rglob("*.html"))


def read_example(name: str) -> str:
    """Return the source text of one example.

    ``name`` is a path relative to the examples root as returned by
    :func:`list_examples`, e.g. ``"marketing/pricing.html"``.

    Raises :class:`ExampleNotFoundError` if the name does not resolve to a
    shipped example. Path traversal (``..``, or any absolute path) is rejected
    the same way rather than followed, so a caller passing a user-supplied
    name cannot read outside the tree.
    """
    candidate = (EXAMPLES_ROOT / name).resolve()
    try:
        candidate.relative_to(EXAMPLES_ROOT)
    except ValueError:
        raise ExampleNotFoundError(f"{name!r} resolves outside the brickwork examples tree.") from None
    if not candidate.is_file():
        raise ExampleNotFoundError(
            f"{name!r} is not a shipped brickwork example. Try brickwork.examples.list_examples()."
        )
    return candidate.read_text(encoding="utf-8")
