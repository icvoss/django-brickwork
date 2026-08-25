"""Direct render tests for _pagination.html (TBL-004, icvoss/django-brickwork#217).

Covers the pre-existing django.core.paginator.Page path, the new flat
duck-typed stand-in (any object presenting number/num_pages/has_previous/
has_next/previous_page_number/next_page_number flat, with num_pages also
accepted nested via ``paginator``), and that the STA-014 render-nothing
contract (one page, or no page_obj at all) is unchanged for either shape.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.test import RequestFactory

_NAV_REQUEST = RequestFactory().get("/invoices/")


def _render(request=None, **ctx: object) -> str:
    return render_to_string("brickwork/components/_pagination.html", ctx, request=request)


@dataclass
class _FlatPage:
    """A minimal flat duck-typed stand-in for a Page: no ``paginator``
    attribute at all, so a nested read must not be relied on."""

    number: int
    num_pages: int
    has_previous: bool
    has_next: bool
    previous_page_number: int | None
    next_page_number: int | None


# --- real django.core.paginator.Page, unchanged behaviour -------------------


def test_real_page_renders_nav_with_prev_and_next_live_links() -> None:
    page = Paginator(range(50), 10).page(2)
    out = _render(request=_NAV_REQUEST, page_obj=page)
    assert '<nav class="bw-pagination"' in out
    assert "bw-pagination__link--disabled" not in out
    assert "Page 2 of 5" in out


def test_real_page_one_page_renders_nothing() -> None:
    page = Paginator(range(5), 10).page(1)
    out = _render(request=_NAV_REQUEST, page_obj=page)
    assert out.strip() == ""


def test_no_page_obj_in_context_renders_nothing() -> None:
    out = _render(request=_NAV_REQUEST)
    assert out.strip() == ""


# --- flat duck-typed stand-in (TBL-004, #217) --------------------------------


def test_flat_stand_in_renders_nav_identically_shaped() -> None:
    flat = _FlatPage(
        number=2,
        num_pages=5,
        has_previous=True,
        has_next=True,
        previous_page_number=1,
        next_page_number=3,
    )
    out = _render(request=_NAV_REQUEST, page_obj=flat)
    assert '<nav class="bw-pagination"' in out
    assert "bw-pagination__link--disabled" not in out
    assert "Page 2 of 5" in out


def test_flat_stand_in_one_page_renders_nothing() -> None:
    flat = _FlatPage(
        number=1,
        num_pages=1,
        has_previous=False,
        has_next=False,
        previous_page_number=None,
        next_page_number=None,
    )
    out = _render(request=_NAV_REQUEST, page_obj=flat)
    assert out.strip() == ""


def test_flat_stand_in_request_path_emits_page_links_via_querystring() -> None:
    flat = _FlatPage(
        number=2,
        num_pages=5,
        has_previous=True,
        has_next=True,
        previous_page_number=1,
        next_page_number=3,
    )
    out = _render(request=_NAV_REQUEST, page_obj=flat)
    assert 'href="?page=1"' in out
    assert 'href="?page=3"' in out
