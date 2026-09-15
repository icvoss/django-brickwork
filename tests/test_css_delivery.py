"""Tests for css_delivery / sync_brickwork_projection (Brickwork Theme Phase F)."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from brickwork import __version__
from brickwork.services.css_delivery import (
    copy_dist_file,
    dist_root,
    projection_path,
    sync_tailwind_theme,
)


def test_dist_root_contains_projection() -> None:
    root = dist_root()
    assert (root / "tailwind-theme.css").is_file()
    assert (root / "tokens.css").is_file()
    assert (root / "brickwork.css").is_file()


def test_projection_path_matches_dist() -> None:
    assert projection_path() == dist_root() / "tailwind-theme.css"


def test_sync_tailwind_theme_writes_stamp(tmp_path: Path) -> None:
    dest = tmp_path / "frontend" / "src" / "brickwork-theme.css"
    result = sync_tailwind_theme(dest)

    assert result.wrote is True
    assert result.bytes_written > 0
    assert dest.is_file()
    text = dest.read_text(encoding="utf-8")
    assert f"django-brickwork {__version__}" in text
    assert "@theme inline" in text
    assert text.index("VENDORED") < text.index("@theme")


def test_sync_tailwind_theme_idempotent(tmp_path: Path) -> None:
    dest = tmp_path / "brickwork-theme.css"
    first = sync_tailwind_theme(dest)
    second = sync_tailwind_theme(dest)

    assert first.wrote is True
    assert second.wrote is False
    assert second.bytes_written == 0


def test_sync_tailwind_theme_force_rewrites(tmp_path: Path) -> None:
    dest = tmp_path / "brickwork-theme.css"
    sync_tailwind_theme(dest)
    dest.write_text("stale\n", encoding="utf-8")
    result = sync_tailwind_theme(dest, force=True)

    assert result.wrote is True
    assert "VENDORED" in dest.read_text(encoding="utf-8")


def test_sync_rejects_directory_destination(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="directory"):
        sync_tailwind_theme(tmp_path)


def test_copy_dist_file_rejects_path_separators(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="bare dist filename"):
        copy_dist_file("../secrets", tmp_path / "out.css")


def test_copy_dist_file_tokens_js(tmp_path: Path) -> None:
    dest = tmp_path / "tokens.js"
    result = copy_dist_file("tokens.js", dest)
    assert result.wrote is True
    assert "export" in dest.read_text(encoding="utf-8") or "bw-" in dest.read_text(
        encoding="utf-8"
    )


def test_management_command_writes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dest = tmp_path / "theme.css"
    call_command("sync_brickwork_projection", str(dest))
    out = capsys.readouterr().out
    assert dest.is_file()
    assert "Wrote" in out
    call_command("sync_brickwork_projection", str(dest))
    out2 = capsys.readouterr().out
    assert "Already up to date" in out2


def test_management_command_directory_is_error(tmp_path: Path) -> None:
    with pytest.raises(CommandError, match="directory"):
        call_command("sync_brickwork_projection", str(tmp_path))
