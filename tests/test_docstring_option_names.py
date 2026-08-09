"""Component docstrings document the ADR-060 option names, never a retired one.

icvoss/django-brickwork#129: two shipped components documented a pre-3.0.0
option name (align, padding) while their executable line already read the
renamed one (placement, size). Both are inclusion-path components, where an
unrecognised kwarg is silently ignored rather than raising, so a migration
done by reading the docstring writes an option that does nothing and reports
no error. This asserts the retired spellings never reappear in a docstring
header, and that the current spelling is present, so the drift cannot recur
silently.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "src/brickwork/templates"

# icvoss/django-brickwork#129: the exact retired-spelling regressions. Each
# entry is (template, retired option header pattern, its current replacement).
_RENAMED_OPTIONS = [
    (
        "brickwork/components/_account_menu.html",
        re.compile(r"^\s*align \("),
        "placement",
    ),
    (
        "brickwork/components/_card.html",
        re.compile(r"^\s*padding \("),
        "size",
    ),
]


@pytest.mark.parametrize(("template", "retired_pattern", "current_name"), _RENAMED_OPTIONS)
def test_docstring_documents_the_shipped_option_name_not_the_retired_one(
    template: str, retired_pattern: re.Pattern, current_name: str
) -> None:
    source = (_TEMPLATES_ROOT / template).read_text(encoding="utf-8")
    lines = source.splitlines()
    retired_hits = [line for line in lines if retired_pattern.match(line)]
    assert not retired_hits, f"{template} still documents the retired option header: {retired_hits}"
    assert re.search(rf"^\s*{current_name} \(", source, re.MULTILINE), (
        f"{template} should document its current option name {current_name!r}"
    )


def test_no_shipped_component_docstring_documents_a_pre_3_0_0_option_header() -> None:
    """The general sweep #129 asked for: no OTHER component regresses the same way."""
    retired_patterns = [re.compile(r"^\s*align \("), re.compile(r"^\s*padding \(")]
    offenders = []
    for path in sorted(_TEMPLATES_ROOT.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if any(pattern.match(line) for pattern in retired_patterns):
                offenders.append(f"{path.relative_to(_TEMPLATES_ROOT)}: {line.strip()}")
    assert not offenders, f"retired pre-3.0.0 option names still documented: {offenders}"
