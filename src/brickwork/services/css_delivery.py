"""Shipped CSS artefacts for a consumer frontend build (Brickwork Theme Phase F).

``brickwork.css`` is shell-served via ``{% static %}``. A consumer Vite /
Tailwind build still needs ``tailwind-theme.css`` (the ``@theme`` projection)
so page-layout utilities inherit ``--bw-*``. That file lives inside the
installed Python package; Node cannot see it, which is why AgentPM-style
apps hand-copy it into ``frontend/``.

This module is the supported replacement for that hand copy: resolve the
installed path, or sync a byte-identical vendor file into the consumer tree
(with a stamped header naming the package version). It is not dual npm
publish and not a second Tailwind redistribute.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from brickwork import __version__

_DIST = "static/brickwork/dist"
_PROJECTION_NAME = "tailwind-theme.css"
_STAMP_MARKER = "brickwork.services.css_delivery.sync_tailwind_theme"


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Outcome of ``sync_tailwind_theme``.

    ``wrote`` is False when the destination already matched the stamped
    payload (idempotent re-run). ``source`` is the installed package path
    that was read; ``destination`` is the consumer path.
    """

    source: Path
    destination: Path
    wrote: bool
    bytes_written: int


def dist_root() -> Path:
    """Absolute path to the installed ``static/brickwork/dist/`` directory.

    Resolved from the installed ``brickwork`` package tree (editable or
    wheel). Raises ``FileNotFoundError`` when the dist directory is absent.
    """
    # Traversable -> filesystem path. django-brickwork always ships ``static/``
    # as package data on disk (not a zipimport-only resource), matching
    # token_manifest's ``files("brickwork").joinpath(...)`` reads.
    root = Path(str(files("brickwork").joinpath(_DIST))).resolve()
    if not root.is_dir():
        raise FileNotFoundError(
            f"brickwork dist directory missing at {root}; reinstall django-brickwork"
        )
    return root


def projection_path() -> Path:
    """Absolute path to the installed ``tailwind-theme.css`` projection."""
    path = dist_root() / _PROJECTION_NAME
    if not path.is_file():
        raise FileNotFoundError(
            f"missing {_PROJECTION_NAME} under {path.parent}; reinstall django-brickwork"
        )
    return path


def _stamped_payload(source_text: str) -> str:
    stamp = (
        f"/* VENDORED by {_STAMP_MARKER} from django-brickwork {__version__}.\n"
        f" * Source: brickwork/static/brickwork/dist/{_PROJECTION_NAME}.\n"
        f" * Re-run `manage.py sync_brickwork_projection` (or sync_tailwind_theme)\n"
        f" * after bumping django-brickwork. Do not edit by hand. */\n"
    )
    if source_text.lstrip().startswith("/* VENDORED by"):
        return source_text
    return stamp + source_text


def sync_tailwind_theme(destination: Path, *, force: bool = False) -> SyncResult:
    """Copy the installed Tailwind projection into ``destination``.

    Creates parent directories as needed. When ``force`` is False and the
    destination already contains the same stamped bytes, skips the write.

    Raises:
        FileNotFoundError: installed projection missing.
        OSError: destination unwritable.
        ValueError: ``destination`` is an existing directory.
    """
    dest = Path(destination)
    if dest.exists() and dest.is_dir():
        raise ValueError(f"destination must be a file path, not a directory: {dest}")

    source = projection_path()
    # Prefer Traversable read (same path as token_manifest) so a broken Path
    # str() conversion still surfaces as a clean FileNotFoundError from files().
    source_text = (
        files("brickwork")
        .joinpath(f"{_DIST}/{_PROJECTION_NAME}")
        .read_text(encoding="utf-8")
    )
    payload = _stamped_payload(source_text)
    payload_bytes = payload.encode("utf-8")

    if dest.is_file() and not force and dest.read_bytes() == payload_bytes:
        return SyncResult(
            source=source,
            destination=dest.resolve(),
            wrote=False,
            bytes_written=0,
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    # Write via a sibling temp then replace, so a partial write never leaves
    # a half-vendored projection for the next Tailwind build.
    tmp = dest.with_name(f".{dest.name}.tmp")
    try:
        tmp.write_bytes(payload_bytes)
        tmp.replace(dest)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)

    return SyncResult(
        source=source,
        destination=dest.resolve(),
        wrote=True,
        bytes_written=len(payload_bytes),
    )


def copy_dist_file(name: str, destination: Path, *, force: bool = False) -> SyncResult:
    """Copy any named file from ``dist/`` (escape hatch; prefer ``sync_tailwind_theme``).

    ``name`` is a bare filename under ``static/brickwork/dist/`` (no path
    separators). Unlike the projection sync, this copies bytes verbatim with
    no stamp header (manifests and minified CSS must stay byte-faithful).
    """
    if not name or Path(name).name != name or "/" in name or "\\" in name:
        raise ValueError(f"name must be a bare dist filename, got {name!r}")

    source = dist_root() / name
    if not source.is_file():
        raise FileNotFoundError(f"no dist artefact named {name!r} at {source}")

    dest = Path(destination)
    if dest.exists() and dest.is_dir():
        raise ValueError(f"destination must be a file path, not a directory: {dest}")

    if dest.is_file() and not force and dest.read_bytes() == source.read_bytes():
        return SyncResult(
            source=source,
            destination=dest.resolve(),
            wrote=False,
            bytes_written=0,
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    return SyncResult(
        source=source,
        destination=dest.resolve(),
        wrote=True,
        bytes_written=source.stat().st_size,
    )
