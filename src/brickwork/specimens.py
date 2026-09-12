"""Package-owned demonstration specimen contexts (icvoss/django-brickwork#497).

Brickwork ships reusable UI; consumers own real application data. Showcase
sites and integration tests still need deterministic, generic inputs that do
not depend on Consentics, AgentPM, or other product fixtures. This module is
that first package-owned surface.

**First family:** ``listing`` (data table, filter bar, empty state). Later
families land as additive scenario names under new family ids; this module
does not become a gallery CMS.

    >>> from brickwork import specimens
    >>> "listing" in specimens.list_families()
    True
    >>> ctx = specimens.get_context("listing", "data_table.populated")
    >>> ctx["table_id"]
    'specimen-invoices'

Contexts are always freshly built (including new Django ``Form`` instances)
so a caller can bind or mutate without affecting later callers. Safe to import
before ``django.setup()`` for discovery helpers; building a filter-bar context
requires Django forms and therefore a configured Django (as any form render
does).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from django import forms

__all__ = [
    "FAMILY_LISTING",
    "SpecimenFilterForm",
    "SpecimenNotFoundError",
    "SpecimenScenario",
    "get_context",
    "get_scenario",
    "list_families",
    "list_scenarios",
]

FAMILY_LISTING = "listing"


class SpecimenNotFoundError(LookupError):
    """Raised when a family or scenario name is not in the shipped set.

    Subclasses ``LookupError`` rather than ``KeyError`` for the same reason
    ``ExampleNotFoundError`` and ``IconNotFoundError`` do: a ``KeyError``
    raised inside template variable resolution is swallowed into a silently
    empty string.
    """


class SpecimenFilterForm(forms.Form):
    """Generic list-filter stand-in for ``_filter_bar.html`` specimens.

    Mirrors the invoice scorecard filter shape used by the package examples
    and a11y fixtures: search plus a closed status choice. Not a domain model;
    a consumer swaps it for their own form when leaving demonstration mode.
    """

    q = forms.CharField(required=False, label="Search")
    status = forms.ChoiceField(
        required=False,
        label="Status",
        choices=[
            ("", "All statuses"),
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("paid", "Paid"),
            ("overdue", "Overdue"),
        ],
    )


@dataclass(frozen=True)
class SpecimenScenario:
    """One named demonstration scenario inside a component family."""

    family: str
    name: str
    component: str
    state: str
    description: str


_TABLE_COLUMNS: list[dict[str, object]] = [
    {"label": "Number", "sortable": True, "sort_key": "number"},
    {"label": "Account", "sortable": False},
    {"label": "Amount", "sortable": True, "sort_key": "amount", "align": "end"},
]

_TABLE_ROWS: list[dict[str, object]] = [
    {"id": 1, "cells": ["INV-2417", "Acme Corp", "£1,240.00"], "url": "/invoices/2417/"},
    {"id": 2, "cells": ["INV-2418", "Halden Group", "£880.00"], "url": "/invoices/2418/"},
    {"id": 3, "cells": ["INV-2419", "Dunmore Retail", "£3,150.00"], "url": "/invoices/2419/"},
    {"id": 4, "cells": ["INV-2420", "Prestwick Logistics", "£640.00"], "url": "/invoices/2420/"},
    {"id": 5, "cells": ["INV-2421", "Carrick & Sons", "£2,090.00"], "url": "/invoices/2421/"},
    {"id": 6, "cells": ["INV-2422", "North Quay Ltd", "£1,475.00"], "url": "/invoices/2422/"},
]

_LONG_LABEL_COLUMNS: list[dict[str, object]] = [
    {
        "label": "Customer-facing invoice reference number",
        "sortable": True,
        "sort_key": "number",
    },
    {"label": "Billing account legal name", "sortable": False},
    {
        "label": "Amount due including recoverable VAT",
        "sortable": True,
        "sort_key": "amount",
        "align": "end",
    },
]

_LONG_LABEL_ROWS: list[dict[str, object]] = [
    {
        "id": 1,
        "cells": [
            "INV-2417-GLASGOW-DEPOT-RUSH",
            "Acme Corporation Holdings (UK) Limited",
            "£1,240.00",
        ],
        "url": "/invoices/2417/",
    },
    {
        "id": 2,
        "cells": [
            "INV-2418-HALDEN-GROUP-RETAINER",
            "Halden Group International Services PLC",
            "£880.00",
        ],
        "url": "/invoices/2418/",
    },
]


def _data_table_populated() -> dict[str, Any]:
    return {
        "table_id": "specimen-invoices",
        "columns": deepcopy(_TABLE_COLUMNS),
        "rows": deepcopy(_TABLE_ROWS),
        "current_sort": "number",
    }


def _data_table_empty() -> dict[str, Any]:
    return {
        "table_id": "specimen-invoices",
        "columns": deepcopy(_TABLE_COLUMNS),
        "rows": [],
        "empty_heading": "No invoices yet",
        "empty_body": "Raise the first invoice to see it listed here.",
        "empty_action_href": "/invoices/new/",
        "empty_action_label": "New invoice",
    }


def _data_table_loading() -> dict[str, Any]:
    return {
        "table_id": "specimen-invoices",
        "columns": deepcopy(_TABLE_COLUMNS),
        "rows": [],
        "loading": True,
    }


def _data_table_long_label() -> dict[str, Any]:
    return {
        "table_id": "specimen-invoices-long",
        "columns": deepcopy(_LONG_LABEL_COLUMNS),
        "rows": deepcopy(_LONG_LABEL_ROWS),
        "current_sort": "number",
    }


def _filter_bar_unbound() -> dict[str, Any]:
    return {
        "fields": list(SpecimenFilterForm()),
        "submit_label": "Filter",
        "clear_href": "/invoices/",
        "filter_bar_id": "specimen-invoice-filters",
    }


def _filter_bar_bound() -> dict[str, Any]:
    form = SpecimenFilterForm(data={"q": "Halden", "status": "overdue"})
    form.is_valid()
    return {
        "fields": list(form),
        "submit_label": "Filter",
        "clear_href": "/invoices/",
        "filter_bar_id": "specimen-invoice-filters",
    }


def _empty_state_no_data() -> dict[str, Any]:
    return {
        "heading": "No invoices yet",
        "body": "Raise the first invoice to get paid faster.",
        "variant": "no_data",
        "action_href": "/invoices/new/",
        "action_label": "New invoice",
    }


def _empty_state_no_results() -> dict[str, Any]:
    return {
        "heading": "No invoices match these filters",
        "body": "Clear the filters or try a broader search.",
        "variant": "no_results",
        "action_href": "/invoices/",
        "action_label": "Clear filters",
    }


def _empty_state_no_action() -> dict[str, Any]:
    """Populated empty state with no optional action CTA."""
    return {
        "heading": "Nothing here yet",
        "body": "This panel has no create action on purpose.",
        "variant": "no_data",
    }


@dataclass(frozen=True)
class _ScenarioEntry:
    meta: SpecimenScenario
    build: Callable[[], dict[str, Any]]


_LISTING_SCENARIOS: dict[str, _ScenarioEntry] = {
    "data_table.populated": _ScenarioEntry(
        SpecimenScenario(
            family=FAMILY_LISTING,
            name="data_table.populated",
            component="brickwork/components/_data_table.html",
            state="populated",
            description="Six invoice rows with sortable headers and row URLs.",
        ),
        _data_table_populated,
    ),
    "data_table.empty": _ScenarioEntry(
        SpecimenScenario(
            family=FAMILY_LISTING,
            name="data_table.empty",
            component="brickwork/components/_data_table.html",
            state="empty",
            description="Zero rows with empty-state heading, body and CTA.",
        ),
        _data_table_empty,
    ),
    "data_table.loading": _ScenarioEntry(
        SpecimenScenario(
            family=FAMILY_LISTING,
            name="data_table.loading",
            component="brickwork/components/_data_table.html",
            state="loading",
            description="Loading skeleton branch (loading=True).",
        ),
        _data_table_loading,
    ),
    "data_table.long_label": _ScenarioEntry(
        SpecimenScenario(
            family=FAMILY_LISTING,
            name="data_table.long_label",
            component="brickwork/components/_data_table.html",
            state="long_label",
            description="Long column labels and cell values for wrap stress.",
        ),
        _data_table_long_label,
    ),
    "filter_bar.unbound": _ScenarioEntry(
        SpecimenScenario(
            family=FAMILY_LISTING,
            name="filter_bar.unbound",
            component="brickwork/components/_filter_bar.html",
            state="unbound",
            description="Unbound search and status fields ready to submit.",
        ),
        _filter_bar_unbound,
    ),
    "filter_bar.bound": _ScenarioEntry(
        SpecimenScenario(
            family=FAMILY_LISTING,
            name="filter_bar.bound",
            component="brickwork/components/_filter_bar.html",
            state="bound",
            description="Bound filter values (search=Halden, status=overdue).",
        ),
        _filter_bar_bound,
    ),
    "empty_state.no_data": _ScenarioEntry(
        SpecimenScenario(
            family=FAMILY_LISTING,
            name="empty_state.no_data",
            component="brickwork/components/_empty_state.html",
            state="no_data",
            description="Standalone no_data empty state with create CTA.",
        ),
        _empty_state_no_data,
    ),
    "empty_state.no_results": _ScenarioEntry(
        SpecimenScenario(
            family=FAMILY_LISTING,
            name="empty_state.no_results",
            component="brickwork/components/_empty_state.html",
            state="no_results",
            description="Standalone no_results empty state with clear CTA.",
        ),
        _empty_state_no_results,
    ),
    "empty_state.no_action": _ScenarioEntry(
        SpecimenScenario(
            family=FAMILY_LISTING,
            name="empty_state.no_action",
            component="brickwork/components/_empty_state.html",
            state="missing_optional",
            description="Empty state without optional action_href/action_label.",
        ),
        _empty_state_no_action,
    ),
}

_FAMILIES: Mapping[str, Mapping[str, _ScenarioEntry]] = {
    FAMILY_LISTING: _LISTING_SCENARIOS,
}


def list_families() -> list[str]:
    """Return every shipped specimen family id, sorted."""
    return sorted(_FAMILIES)


def list_scenarios(family: str) -> list[str]:
    """Return every scenario name in ``family``, sorted.

    Raises :class:`SpecimenNotFoundError` if ``family`` is unknown.
    """
    try:
        scenarios = _FAMILIES[family]
    except KeyError:
        raise SpecimenNotFoundError(
            f"{family!r} is not a shipped brickwork specimen family. Try brickwork.specimens.list_families()."
        ) from None
    return sorted(scenarios)


def get_scenario(family: str, name: str) -> SpecimenScenario:
    """Return metadata for one scenario without building its context."""
    return _entry(family, name).meta


def get_context(family: str, name: str) -> dict[str, Any]:
    """Return a fresh template context for one scenario.

    Always newly constructed: list values are deep-copied and filter forms are
    new instances, so callers may mutate the returned dict safely.
    """
    return _entry(family, name).build()


def _entry(family: str, name: str) -> _ScenarioEntry:
    try:
        family_map = _FAMILIES[family]
    except KeyError:
        raise SpecimenNotFoundError(
            f"{family!r} is not a shipped brickwork specimen family. Try brickwork.specimens.list_families()."
        ) from None
    try:
        return family_map[name]
    except KeyError:
        raise SpecimenNotFoundError(
            f"{name!r} is not a shipped scenario in family {family!r}. "
            f"Try brickwork.specimens.list_scenarios({family!r})."
        ) from None
