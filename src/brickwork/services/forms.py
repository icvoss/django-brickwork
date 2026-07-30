"""Form helpers: the HTMX 422 validation-swap contract (BR-BW-HTMX-003).

brickwork has NO hard django-htmx dependency: its core reads the ``HX-Request``
header directly and duck-types ``request.htmx`` when a consumer already runs
django-htmx (04-interfaces.md). These helpers are ``[v1-single-consumer]``:
consentics exercises the HTMX swap; agentpm's no-JS forms exercise the equivalent
full-page POST -> redisplay path instead (BR-BW-HTMX-001).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.forms import BoundField
    from django.http import HttpRequest


def is_htmx_request(request: HttpRequest) -> bool:
    """Whether this request came from htmx.

    Prefers a duck-typed ``request.htmx`` (set by django-htmx when the optional
    [htmx] extra is installed), falling back to the raw ``HX-Request`` header so
    brickwork's core needs no django-htmx dependency of its own.
    """
    htmx = getattr(request, "htmx", None)
    if htmx is not None:
        return bool(htmx)
    return request.headers.get("HX-Request") == "true"


def is_htmx_validation_request(request: HttpRequest) -> bool:
    """Whether a failed form submission should respond with the 422 swap.

    True for an htmx-driven form POST (BR-BW-HTMX-003). A consuming view calls
    this in ``form_invalid`` to decide whether to set status 422 for the targeted
    ``hx-swap="outerHTML"`` re-render, versus a normal full-page redisplay for a
    non-htmx (e.g. JS-disabled) submission, which is itself a fully working page.
    """
    return is_htmx_request(request)


def field_error_id(field: BoundField) -> str:
    """The stable id for a field's error container, wired via aria-describedby.

    Kept in one place so the field template and any test reference the same id
    convention (BR-BW-HTMX-003 / BR-BW-A11Y-002).
    """
    return f"{field.auto_id}_errors"


def render_field_errors(field: BoundField) -> list[str]:
    """Return a field's validation error messages as a list of plain strings.

    The public helper named in 04-interfaces.md section 3. It gives a consuming
    view or template the field's errors decoupled from the shipped ``_field.html``
    markup, so a project that renders its own field chrome can still reuse
    brickwork's error extraction (and the matching aria-describedby id via
    ``field_error_id``). Returns an empty list for a field with no errors.
    """
    return [str(error) for error in field.errors]
