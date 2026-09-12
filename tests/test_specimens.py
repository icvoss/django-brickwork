"""Package-owned listing specimen contexts (icvoss/django-brickwork#497)."""

from __future__ import annotations

import pytest
from django.template import Context, Engine, TemplateDoesNotExist
from django.template.loader import get_template

from brickwork import specimens


def test_list_families_includes_listing() -> None:
    assert specimens.list_families() == [specimens.FAMILY_LISTING]


def test_list_scenarios_is_sorted_and_complete() -> None:
    names = specimens.list_scenarios(specimens.FAMILY_LISTING)
    assert names == sorted(names)
    assert "data_table.populated" in names
    assert "filter_bar.unbound" in names
    assert "empty_state.no_results" in names
    assert len(names) == 9


def test_unknown_family_and_scenario_raise_loudly() -> None:
    with pytest.raises(specimens.SpecimenNotFoundError, match="not a shipped"):
        specimens.list_scenarios("not-a-family")
    with pytest.raises(specimens.SpecimenNotFoundError, match="not a shipped"):
        specimens.get_context(specimens.FAMILY_LISTING, "missing.scenario")


def test_get_context_returns_fresh_copies() -> None:
    first = specimens.get_context(specimens.FAMILY_LISTING, "data_table.populated")
    second = specimens.get_context(specimens.FAMILY_LISTING, "data_table.populated")
    assert first is not second
    assert first["rows"] is not second["rows"]
    first["rows"].clear()
    assert len(second["rows"]) == 6


def test_filter_contexts_use_fresh_forms() -> None:
    first = specimens.get_context(specimens.FAMILY_LISTING, "filter_bar.bound")
    second = specimens.get_context(specimens.FAMILY_LISTING, "filter_bar.bound")
    assert first["fields"][0].form is not second["fields"][0].form
    assert first["fields"][0].value() == "Halden"
    assert first["fields"][1].value() == "overdue"


@pytest.mark.parametrize(
    ("name", "needle"),
    [
        ("data_table.populated", "INV-2417"),
        ("data_table.empty", "No invoices yet"),
        ("data_table.loading", "bw-skeleton"),
        ("data_table.long_label", "Customer-facing invoice reference number"),
        ("filter_bar.unbound", "All statuses"),
        ("filter_bar.bound", "Halden"),
        ("empty_state.no_data", "New invoice"),
        ("empty_state.no_results", "Clear filters"),
        ("empty_state.no_action", "Nothing here yet"),
    ],
)
def test_every_listing_scenario_renders_its_component(name: str, needle: str) -> None:
    meta = specimens.get_scenario(specimens.FAMILY_LISTING, name)
    context = specimens.get_context(specimens.FAMILY_LISTING, name)
    html = get_template(meta.component).render(context)
    assert needle in html, f"{name} rendered without {needle!r}"


def test_specimen_module_is_importable_before_django_setup_helpers() -> None:
    """Discovery helpers stay available; matching examples.list_examples style."""
    assert callable(specimens.list_families)
    assert specimens.FAMILY_LISTING == "listing"


def test_specimens_are_not_on_the_template_loader_path() -> None:
    """Specimens are Python context factories, not extendable templates."""
    engine = Engine(dirs=[], app_dirs=True)
    with pytest.raises(TemplateDoesNotExist):
        engine.get_template("brickwork/specimens/listing.html")
    # Context dicts remain renderable via ordinary component includes.
    ctx = Context(specimens.get_context(specimens.FAMILY_LISTING, "empty_state.no_data"))
    assert "No invoices yet" in get_template("brickwork/components/_empty_state.html").render(ctx.flatten())
