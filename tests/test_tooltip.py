"""Direct render tests for _tooltip.html's block naming (0.12.0, #56, ADR-077 SS4).

Covers the deprecated `tooltip_trigger` block dual-shipped alongside its
concise successor `trigger` (BR-BW-VER-001 parallel support): both must
render.
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


def test_deprecated_tooltip_trigger_block_still_renders_alone() -> None:
    out = _extend("{% block tooltip_trigger %}<button>LEGACY-SENTINEL</button>{% endblock %}")
    assert "LEGACY-SENTINEL" in out


def test_trigger_and_tooltip_trigger_both_render_when_both_are_filled() -> None:
    out = _extend(
        "{% block trigger %}<span>TRIGGER-SENTINEL</span>{% endblock %}"
        "{% block tooltip_trigger %}<span>LEGACY-SENTINEL</span>{% endblock %}"
    )
    assert "TRIGGER-SENTINEL" in out
    assert "LEGACY-SENTINEL" in out
    assert out.index("TRIGGER-SENTINEL") < out.index("LEGACY-SENTINEL")


def test_bubble_still_renders_the_text_context() -> None:
    out = _extend("{% block trigger %}<button>Info</button>{% endblock %}", text="Helpful hint")
    assert "Helpful hint" in out
