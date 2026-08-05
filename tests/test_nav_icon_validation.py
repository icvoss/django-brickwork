"""bw_nav validates NavItem.icon at prepare time (icvoss/django-brickwork#89).

An unregistered icon name on a NavItem previously reached {% bw_icon %} inside
nav/_nav.html's recursive {% partialdef %}; the IconNotFoundError raised there
was masked by Django's template-partials machinery and re-surfaced as a
misleading "Partial 'nav_item' is not defined in the current template.",
sending consumers on a wild goose chase (that is exactly what happened building
brickworkui.com). bw_nav now validates the icon name up front so the accurate
error is raised at prepare time.
"""

import pytest
from django.template import Context, Template

from brickwork.icons.registry import IconNotFoundError, has_icon
from brickwork.models import NavItem


def _render(items):
    return Template("{% load brickwork_nav %}{% bw_nav items=items %}").render(Context({"items": items}))


def test_registered_icon_renders():
    out = _render((NavItem(key="a", label="A", external_url="https://a.test", icon="file"),))
    assert "bw-nav__link" in out
    assert "bw-nav__icon" in out


def test_unregistered_icon_raises_clear_iconnotfound_not_masked_partial_error():
    with pytest.raises(IconNotFoundError) as exc:
        # "file-text" is a Lucide filename stem, NOT a registered brickwork name
        # (the canonical name is "file"); the classic #89 trigger.
        _render((NavItem(key="a", label="A", external_url="https://a.test", icon="file-text"),))
    msg = str(exc.value)
    assert "file-text" in msg
    assert "not a registered" in msg
    # The masked, misleading error must NOT be what the consumer sees.
    assert "Partial" not in msg


def test_unregistered_icon_on_a_child_item_also_raises():
    tree = (
        NavItem(
            key="sec",
            label="Section",
            section_header=True,
            children=(NavItem(key="c", label="C", external_url="https://c.test", icon="file-text"),),
        ),
    )
    with pytest.raises(IconNotFoundError):
        _render(tree)


def test_none_icon_is_fine():
    out = _render((NavItem(key="a", label="A", external_url="https://a.test"),))
    assert "bw-nav__link" in out


def test_has_icon_predicate():
    assert has_icon("file") is True
    assert has_icon("file-text") is False


def test_prepare_time_error_suggests_the_nearest_registered_name():
    # #74's did-you-mean: the classic "file-text" near-miss should point at the
    # canonical "file" so the consumer's next attempt is the right one.
    with pytest.raises(IconNotFoundError) as exc:
        _render((NavItem(key="a", label="A", external_url="https://a.test", icon="file-text"),))
    msg = str(exc.value)
    assert "Did you mean" in msg
    assert "'file'" in msg
