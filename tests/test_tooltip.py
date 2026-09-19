"""Direct render tests for _tooltip.html's block naming (0.12.0, #56, ADR-077 SS4).

Covers the concise `trigger` block (prefixed tooltip_trigger removed in 4.0.0).
"""

from __future__ import annotations

from django.template import Context, Template


def _extend(blocks: str, **ctx: object) -> str:
    ctx.setdefault("id", "info-tip")
    ctx.setdefault("text", "More info")
    source = "{% extends 'brickwork/components/_tooltip.html' %}" + blocks
    return Template(source).render(Context(ctx))


def test_trigger_block_renders() -> None:
    out = _extend("{% block trigger %}<button>TRIGGER-SENTINEL</button>{% endblock %}")
    assert "TRIGGER-SENTINEL" in out


def test_deprecated_tooltip_trigger_block_no_longer_renders() -> None:
    out = _extend("{% block tooltip_trigger %}<button>LEGACY-SENTINEL</button>{% endblock %}")
    assert "LEGACY-SENTINEL" not in out


def test_legacy_tooltip_trigger_fill_is_discarded_when_trigger_is_filled() -> None:
    out = _extend(
        "{% block trigger %}<span>TRIGGER-SENTINEL</span>{% endblock %}"
        "{% block tooltip_trigger %}<span>LEGACY-SENTINEL</span>{% endblock %}"
    )
    assert "TRIGGER-SENTINEL" in out
    assert "LEGACY-SENTINEL" not in out


def test_bubble_still_renders_the_text_context() -> None:
    out = _extend("{% block trigger %}<button>Info</button>{% endblock %}", text="Helpful hint")
    assert "Helpful hint" in out
