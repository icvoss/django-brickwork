"""Brand-pack PROFILE.md presence and claimed level (Brickwork Theme Phase B)."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PACK_ROOT = _REPO_ROOT / "docs" / "examples" / "brand-pack"

_LEVEL_RE = re.compile(r"(?m)^Level claimed:\s*(L[1-4])\s*$")
_THEME_RE = re.compile(r"THEME\.md")

# Pack slug -> expected claimed level (must match PROFILE.md and authored axes).
_EXPECTED_LEVELS = {
    "northline": "L2",
    "harbour": "L2",
    "folio": "L2",
    "northline-material": "L3",
    "northline-dense": "L4",
}

_REQUIRED_FILES = ("PROFILE.md", "DESIGN.md", "tokens.css")


def test_example_brand_packs_declare_profile_level() -> None:
    missing = [slug for slug in _EXPECTED_LEVELS if not (_PACK_ROOT / slug).is_dir()]
    assert not missing, f"expected brand-pack directories missing: {missing}"

    for slug, expected in _EXPECTED_LEVELS.items():
        pack = _PACK_ROOT / slug
        for name in _REQUIRED_FILES:
            path = pack / name
            assert path.is_file(), f"{slug}: missing {name}"

        profile = (pack / "PROFILE.md").read_text(encoding="utf-8")
        match = _LEVEL_RE.search(profile)
        assert match is not None, f"{slug}: PROFILE.md has no 'Level claimed: Ln' line"
        assert match.group(1) == expected, f"{slug}: claimed {match.group(1)!r}, expected {expected!r}"
        assert _THEME_RE.search(profile), f"{slug}: PROFILE.md must cite THEME.md"

        design = (pack / "DESIGN.md").read_text(encoding="utf-8")
        assert "## 9. Agent brief" in design, f"{slug}: DESIGN.md missing Agent brief H2"
        assert _THEME_RE.search(design), f"{slug}: Agent brief / DESIGN must cite THEME.md"


def test_brand_pack_readme_lists_torture_packs() -> None:
    readme = (_PACK_ROOT / "README.md").read_text(encoding="utf-8")
    for slug in ("northline-material", "northline-dense"):
        assert slug in readme, f"examples README must list {slug}"
    assert "THEME.md" in readme
