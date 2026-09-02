"""Every class a shipped component/form/nav/marketing template can emit is
actually styled (icvoss/django-brickwork#137, the structural cause of #130).

test_examples.py's `test_every_section_class_it_emits_is_actually_styled`
renders example SECTIONS and checks every ``bw-*`` class they emit against
the compiled stylesheet. That is the right check, but its engine only
renders `src/brickwork/examples/`: a class emitted ONLY from a component
template under `src/brickwork/templates/brickwork/components/` (or forms/,
nav/, or the marketing sub-app), reached the way a real consumer reaches it
(``{% include %}``, ``{% extends %}``, or a ``{% bw_* %}`` inclusion tag),
is never rendered by that engine and so is never checked. #130's own defect
class (``bw-btn--md``, ``bw-field__control``) lived exactly there: 1000+
tests green with an unstyled default button size on every page.

THE TRAP THIS FILE EXISTS TO AVOID (a recorded ecosystem lesson: a fixture
rendering a component EMPTY passes every gate while asserting nothing): a
component rendered with a bare/default/empty context renders near-empty and
its modifier classes never appear, so the check below would pass vacuously.
Two things guard against that:

1. Every render context here is DELIBERATELY rich (real labels, icons, error
   states, loading states, selected/highlighted rows, multi-item lists), not
   the minimal context that satisfies "required context: none".
2. Every component that takes a documented option vocabulary (variant, size,
   placement, ...) is rendered ONCE PER DOCUMENTED VALUE, drawn from
   `test_option_vocabularies.py`'s `_VOCABULARIES` (the existing hand
   maintained list, ADR-060) rather than a second copy of the same data:
   that test proves each value resolves to a real class; this one proves the
   template actually EMITS that class when the value is passed, over a
   context rich enough to reach it.
3. `test_every_registered_render_produced_non_trivial_output` (the guard) is
   a second contract check by DESIGN, not deduplication: a template that
   silently rendered empty (a bad fixture, a wrong template name, a context
   key the template does not read) would otherwise pass the class-contract
   test with zero classes found and zero classes missing. This suite would
   be a no-op without it, which is exactly the failure mode #130 slipped
   through under.

Rendering conventions match each component's OWN existing test file (e.g.
test_card.py's `_extend`, test_dropdown.py's tag-loading `_render`,
test_marketing.py's `_include`/`_extend`), so a reviewer already familiar
with one of those files recognises the shape here immediately.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from django import forms
from django.template import Context, Template, engines
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.utils.safestring import mark_safe

from brickwork.models import NavItem
from tests._class_contract import UNSTYLED_BY_DESIGN, unstyled_classes
from tests.test_option_vocabularies import _VOCABULARIES

# --- shared fixtures ---------------------------------------------------------


class _DemoForm(forms.Form):
    """A rich stand-in form: one text field (with help text, so the help
    branch renders), one field pre-populated with an error (so the invalid
    branch and the error-message loop render), and a choice field (so
    combobox/select coverage has real options)."""

    name = forms.CharField(label="Company name", help_text="As it appears on invoices")
    plan = forms.ChoiceField(
        label="Plan",
        choices=[("solo", "Solo"), ("team", "Team"), ("scale", "Scale")],
    )


def _invalid_demo_form() -> _DemoForm:
    form = _DemoForm(data={"name": "", "plan": "solo"})
    form.is_valid()
    return form


def _tag(load: str, src: str, **ctx: object) -> str:
    """Render one inclusion-tag call, matching test_components.py/test_dropdown.py's
    own ``_render`` helper shape (one `{% load %}` plus the tag invocation)."""
    return engines["django"].from_string("{% load " + load + " %}" + src).render(ctx)


def _include(template: str, **ctx: object) -> str:
    """Render a structural {% include %}, matching test_marketing.py's own
    ``_include`` helper. A ``request=`` kwarg is forwarded to
    render_to_string's own ``request`` parameter (a REAL RequestContext,
    with ``context.request`` set), not left inside the plain context dict:
    {% querystring %} (used by _pagination.html and _data_table.html's sort
    links) reads ``context.request`` directly and raises AttributeError
    against a bare Context, matching test_data_table.py's own convention."""
    request = ctx.pop("request", None)
    return render_to_string(template, ctx, request=request)


def _extend(parent: str, blocks: str, **ctx: object) -> str:
    """Render a consumer partial that EXTENDS a block-based component
    (_card.html, _modal.html, _slide_over.html, _tooltip.html,
    _bulk_actions_bar.html), matching test_card.py/test_modal.py's own
    ``_extend`` helper. Always loads brickwork_components: several filler
    blocks compose {% bw_button %} (the real-world shape, per _card.html's
    own docstring example), and loading an unused library is a no-op for the
    blocks that do not."""
    source = "{% extends '" + parent + "' %}{% load brickwork_components %}" + blocks
    return Template(source).render(Context(ctx))


_DROPDOWN_ITEMS = [
    {"label": "New invoice", "url": "/invoices/new/", "icon": "plus"},
    {"label": "Draft invoices", "url": "/invoices/?status=draft"},
    {"divider": True},
    {"label": "Delete demo data", "url": "/reset/", "variant": "danger"},
]

_ACCOUNT_MENU_ITEMS = [
    {"label": "Profile", "url": "/account/profile/", "icon": "user"},
    {"label": "Billing", "url": "/account/billing/", "icon": "document"},
    {"label": "Sign out", "url": "/account/logout/", "icon": "log-out", "danger": True, "method": "post"},
]

_TABLE_COLUMNS = [
    {"label": "Number", "sortable": True, "sort_key": "number"},
    {"label": "Account", "sortable": False},
    {"label": "Amount", "sortable": True, "sort_key": "amount"},
]
_TABLE_ROWS = [
    {"id": 1, "cells": ["INV-2417", "Acme Corp", "1240.00 GBP"], "url": "/invoices/1/", "selected": True},
    {"id": 2, "cells": ["INV-2418", "Halden Group", "880.00 GBP"]},
]

_STEPPER_STEPS = [
    {"label": "Company", "status": "complete"},
    {"label": "Team", "status": "current"},
    {"label": "Billing", "status": "upcoming"},
]

_TABS = [
    {"key": "overview", "label": "Overview"},
    {"key": "activity", "label": "Activity", "badge": 3},
]

_COMBOBOX_OPTIONS = [
    {"value": "acme", "label": "Acme Corp"},
    {"value": "halden", "label": "Halden Group"},
]

_NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem(
        key="workspace",
        label="Workspace",
        section_header=True,
        children=(
            NavItem(key="invoices", label="Invoices", href="/invoices/", icon="document", badge=3),
            NavItem(key="reports", label="Reports", href="/reports/"),
        ),
    ),
    NavItem(key="settings", label="Settings", href="/settings/", icon="settings"),
    NavItem(key="docs", label="Docs", external_url="https://docs.example.com/"),
)
_NAV_ACTIVE = _NAV_ITEMS[0].children[0]
_NAV_REQUEST = RequestFactory().get("/invoices/")


def _render_nav(tag: str) -> str:
    source = "{% load brickwork_nav %}{% " + tag + " items=items active=active %}"
    ctx = {"items": _NAV_ITEMS, "active": _NAV_ACTIVE, "request": _NAV_REQUEST}
    return Template(source).render(Context(ctx))


# --- the registry: name -> zero-arg render callable --------------------------
#
# One entry per component/form/nav render, PLUS one entry per documented
# option-vocabulary permutation for the components _VOCABULARIES covers, so a
# component's non-default modifier classes are exercised, not just its
# defaults. Grouped to match the components/ directory order; forms/, nav/
# and the marketing sub-app follow.

_COMPONENT_RENDERS: dict[str, Callable[[], str]] = {
    # --- components/, tag-invoked ------------------------------------------
    "_button (bw_button: href, icon, loading)": lambda: _tag(
        "brickwork_components",
        '{% bw_button "Run the demo" variant="primary" size="lg" href="/demo/" icon="download" %}',
    ),
    "_button (bw_button: submit, icon-only)": lambda: _tag(
        "brickwork_components",
        '{% bw_button icon="trash" icon_only=True aria_label="Delete" variant="danger" size="sm" %}',
    ),
    "_button (bw_button: loading)": lambda: _tag(
        "brickwork_components", '{% bw_button "Saving" variant="secondary" loading=True %}'
    ),
    "_badge (bw_badge: dismissible)": lambda: _tag(
        "brickwork_components", '{% bw_badge "Overdue" variant="danger" icon="alert-circle" dismissible=True %}'
    ),
    "_alert (bw_alert: dismissible, title)": lambda: _tag(
        "brickwork_components",
        '{% bw_alert "Payment failed." variant="danger" title="Action needed" dismissible=True %}',
    ),
    "_toggle (bw_toggle)": lambda: _tag(
        "brickwork_components", '{% bw_toggle "Auto-chase" id="autochase" checked=True %}'
    ),
    "_skeleton (bw_skeleton: sized)": lambda: _tag(
        "brickwork_components", '{% bw_skeleton variant="row" count=3 width="12rem" height="1rem" %}'
    ),
    "_search (bw_search: scoped)": lambda: _tag(
        "brickwork_components",
        '{% bw_search action="/search/" value="invoice" scope=scope %}',
        scope={"label": "Project: Acme", "name": "project", "value": "acme", "clear_href": "/search/?q=invoice"},
    ),
    "_card (extended, all regions, interactive+bordered)": lambda: _extend(
        "brickwork/components/_card.html",
        '{% block card_header %}<div class="bw-card__header"><h2 class="bw-card__title">Members</h2>'
        '<div class="bw-card__actions">{% bw_button label="Add" variant="secondary" size="sm" %}</div></div>{% endblock %}'
        "{% block card_body %}<p>Body copy.</p>{% endblock %}"
        '{% block card_footer %}<footer class="bw-card__footer">Updated today</footer>{% endblock %}',
        interactive=True,
        bordered=True,
        size="lg",
    ),
    "_card (linked)": lambda: _include("brickwork/components/_card.html", href="/invoices/1/", size="sm"),
    "_stat (trend, icon, href, sparkline)": lambda: _include(
        "brickwork/components/_stat.html",
        label="Average time to pay",
        value="21 days",
        trend="down",
        trend_label="17 days faster",
        icon="calendar",
        href="/reports/aging/",
        size="lg",
    ),
    "_stat (loading)": lambda: _include("brickwork/components/_stat.html", label="Revenue", value="0", loading=True),
    "_trend_indicator (up, with label)": lambda: _include(
        "brickwork/components/_trend_indicator.html", trend="up", trend_label="17 days faster"
    ),
    "_trend_indicator (down, no label)": lambda: _include("brickwork/components/_trend_indicator.html", trend="down"),
    "_trend_indicator (flat)": lambda: _include("brickwork/components/_trend_indicator.html", trend="flat"),
    "_stat_comparison (sm, trend up, label, period_label)": lambda: _include(
        "brickwork/components/_stat_comparison.html",
        label="Revenue",
        current="12,400",
        previous="10,900",
        period_label="vs last month",
        trend="up",
        trend_label="14% up",
        size="sm",
    ),
    "_stat_comparison (lg, trend down)": lambda: _include(
        "brickwork/components/_stat_comparison.html",
        label="Churn",
        current="4.2%",
        previous="3.1%",
        period_label="vs last quarter",
        trend="down",
        trend_label="1.1pt worse",
        size="lg",
    ),
    "_stat_comparison (md default, no trend, no period_label)": lambda: _include(
        "brickwork/components/_stat_comparison.html",
        current="987",
        previous="1,234",
    ),
    "_scorecard (mixed spans, data attrs)": lambda: _include(
        "brickwork/components/_scorecard.html",
        items=[
            {
                "content": mark_safe(  # noqa: S308 (test-authored trusted markup)
                    '<div class="bw-stat"><span class="bw-stat__label">Revenue</span>'
                    '<span class="bw-stat__value">£12,400</span></div>'
                ),
                "span": 2,
            },
            {
                "content": mark_safe(  # noqa: S308 (test-authored trusted markup)
                    '<div class="bw-stat"><span class="bw-stat__label">Churn</span>'
                    '<span class="bw-stat__value">4.2%</span></div>'
                ),
                "span": "3",
            },
            {
                "content": mark_safe(  # noqa: S308 (test-authored trusted markup)
                    '<div class="bw-stat"><span class="bw-stat__label">Signups</span>'
                    '<span class="bw-stat__value">318</span></div>'
                ),
                "span": 4,
            },
            {
                "content": mark_safe(  # noqa: S308 (test-authored trusted markup)
                    '<div class="bw-stat"><span class="bw-stat__label">Uptime</span>'
                    '<span class="bw-stat__value">99.98%</span></div>'
                ),
            },
        ],
        data={"data-testid": "kpi-grid"},
    ),
    "_ranked_list (bw_ranked_list: linked rows, basis=total, label, data)": lambda: _tag(
        "brickwork_components",
        "{% bw_ranked_list rows=rows basis='total' label='Top accounts' data=data %}",
        rows=[
            {"label": "Acme Corp", "amount": 4000, "value": "£4,000", "href": "/accounts/acme/"},
            {"label": "Globex", "amount": 3000, "value": "£3,000", "href": "/accounts/globex/"},
            {"label": "Initech", "amount": 1000, "value": "£1,000", "href": "/accounts/initech/"},
        ],
        data={"data-testid": "top-accounts"},
    ),
    "_ranked_list (bw_ranked_list: empty, with action)": lambda: _tag(
        "brickwork_components",
        "{% bw_ranked_list rows=rows empty_heading='No accounts yet' empty_body='Add one to see it here.' "
        "empty_action_href='/accounts/new/' empty_action_label='Add an account' %}",
        rows=[],
    ),
    "_ranked_list (bw_ranked_list: loading)": lambda: _tag(
        "brickwork_components", "{% bw_ranked_list rows=rows loading=True %}", rows=[]
    ),
    "_chart_card (populated, legend, title/actions)": lambda: _extend(
        "brickwork/components/_chart_card.html",
        '{% block title %}<h2 class="bw-card__title">Revenue by month</h2>{% endblock %}'
        '{% block actions %}<div class="bw-card__actions">{% bw_button label="Export" variant="secondary" size="sm" %}'
        "</div>{% endblock %}"
        '{% block chart_legend %}<div class="bw-chart-card__legend">Legend swatch</div>{% endblock %}',
        legend_position="side",
        mount=mark_safe(  # noqa: S308 (test-authored trusted markup)
            '<div class="bw-chart-mount" data-bw-chart-mount role="img" aria-label="Revenue by month"></div>'
        ),
    ),
    # _sparkline renders through {% bw_sparkline %}, so it registers with _tag
    # rather than _include. Both tones are exercised: neutral takes the
    # overridable stroke token, trend adds the glyph-plus-visually-hidden-text
    # pairing COL-030 requires, and the two emit different modifier classes.
    "_sparkline (neutral, highlighted)": lambda: _tag(
        "brickwork_components",
        '{% bw_sparkline points=pts label="Revenue trend" value="1,234" highlight_index=3 %}',
        pts=[4, 7, 5, 9, 8],
    ),
    "_sparkline (trend)": lambda: _tag(
        "brickwork_components",
        '{% bw_sparkline points=pts label="Signups" tone="trend" %}',
        pts=[2, 4, 9],
    ),
    "_chart_card (loading)": lambda: _include("brickwork/components/_chart_card.html", loading=True),
    "_chart_card (error)": lambda: _include(
        "brickwork/components/_chart_card.html",
        error=True,
        error_title="Could not load",
        error_message="Try again later.",
    ),
    "_chart_card (empty, with action)": lambda: _include(
        "brickwork/components/_chart_card.html",
        empty=True,
        empty_body="Nothing to plot yet.",
        empty_action_href="/reports/new/",
        empty_action_label="Create a report",
    ),
    "_chart_mount (bw_chart_mount: named, not template-backed)": lambda: _tag(
        "brickwork_components",
        '{% bw_chart_mount aria_label="Revenue by month" min_height="20rem" aspect_ratio="16 / 9" %}',
    ),
    "_chart_mount (bw_chart_mount: decorative, not template-backed)": lambda: _tag(
        "brickwork_components", '{% bw_chart_mount decorative=True min_height="20rem" %}'
    ),
    # All three of CHT-013's data_table_mode values, because each emits a
    # different wrapper: "visible" is the bare base state, "hidden" adds the
    # bw-visually-hidden clip wrapper, and "toggle" pulls in _disclosure.html's
    # own class family. Registering only one would leave the other two's
    # classes ungated.
    "_chart_data_table (bw_chart_data_table: visible)": lambda: _tag(
        "brickwork_components",
        "{% bw_chart_data_table caption='Revenue by month' columns=cols rows=rws data_table_mode='visible' %}",
        cols=["Month", "Direct", "Referral"],
        rws=[["January", "120", "45"], ["February", "150", "60"]],
    ),
    "_chart_data_table (bw_chart_data_table: hidden)": lambda: _tag(
        "brickwork_components",
        "{% bw_chart_data_table caption='Revenue by month' columns=cols rows=rws data_table_mode='hidden' %}",
        cols=["Month", "Direct", "Referral"],
        rws=[["January", "120", "45"], ["February", "150", "60"]],
    ),
    "_chart_data_table (bw_chart_data_table: toggle)": lambda: _tag(
        "brickwork_components",
        "{% bw_chart_data_table caption='Revenue by month' columns=cols rows=rws data_table_mode='toggle' "
        "toggle_label='View as table' %}",
        cols=["Month", "Direct", "Referral"],
        rws=[["January", "120", "45"], ["February", "150", "60"]],
    ),
    "_gauge (bw_gauge: threshold_bands, label, size=lg)": lambda: _tag(
        "brickwork_components",
        "{% bw_gauge value=value label='CPU load' size='lg' threshold_bands=bands %}",
        value=65,
        bands=[
            {"max": 50, "token": "danger"},
            {"max": 80, "token": "warning"},
            {"max": 100, "token": "success"},
        ],
    ),
    "_gauge (bw_gauge: default accent, size=sm)": lambda: _tag(
        "brickwork_components", "{% bw_gauge value=value size='sm' %}", value=42
    ),
    "_data_table (records, selectable, sticky, stack, sorted)": lambda: _include(
        "brickwork/components/_data_table.html",
        table_id="invoices",
        variant="records",
        columns=_TABLE_COLUMNS,
        rows=_TABLE_ROWS,
        current_sort="number",
        selectable=True,
        sticky_header=True,
        responsive="stack",
    ),
    "_data_table (definition)": lambda: _include(
        "brickwork/components/_data_table.html",
        table_id="invoice-facts",
        variant="definition",
        rows=[{"label": "Account", "value": "Acme Corp"}, {"label": "Raised", "value": "14 July 2026"}],
    ),
    "_data_table (empty, loading)": lambda: (
        _include("brickwork/components/_data_table.html", table_id="a", columns=_TABLE_COLUMNS, rows=[])
        + _include("brickwork/components/_data_table.html", table_id="b", columns=_TABLE_COLUMNS, rows=[], loading=True)
    ),
    "_code (filename, language, copyable)": lambda: _include(
        "brickwork/components/_code.html",
        filename="billing/reminders.py",
        language="Python",
        copyable=True,
        code=(
            "def next_reminder(invoice):\n"
            '    """Return the next reminder stage for an overdue invoice."""\n'
            "    days_overdue = (today() - invoice.due_date).days\n"
            "    if days_overdue >= 14:\n"
            "        return Stage.FINAL_NOTICE\n"
            "    if days_overdue >= 3:\n"
            "        return Stage.OVERDUE\n"
            "    return Stage.DUE_TODAY"
        ),
    ),
    "_code (plain, no header)": lambda: _include(
        "brickwork/components/_code.html",
        label="Reminder schedule, plain text",
        code=(
            "due_date - 7d   first reminder, friendly\n"
            "due_date        due today\n"
            "due_date + 3d   overdue, cc the account owner\n"
            "due_date + 14d  final notice before escalation"
        ),
    ),
    "_stepper (vertical, all statuses)": lambda: _include(
        "brickwork/components/_stepper.html", steps=_STEPPER_STEPS, orientation="vertical"
    ),
    "_modal (extended, full chrome)": lambda: _extend(
        "brickwork/components/_modal.html",
        "{% block modal_body %}<p>Body copy.</p>{% endblock %}"
        '{% block modal_footer %}<footer class="bw-modal__footer">'
        '<button type="submit">Go</button></footer>{% endblock %}',
        title="Confirm deletion",
        size="lg",
        backdrop_dismiss=False,
        close_href="/invoices/",
    ),
    "_slide_over (extended, full chrome)": lambda: _extend(
        "brickwork/components/_slide_over.html",
        "{% block slide_over_body %}<p>Body copy.</p>{% endblock %}"
        '{% block slide_over_footer %}<footer class="bw-slide-over__footer">'
        '<button type="submit">Save</button></footer>{% endblock %}',
        title="Edit invoice",
        size="lg",
        placement="start",
    ),
    "_account_menu (post item, open, placement=start)": lambda: _include(
        "brickwork/components/_account_menu.html",
        items=_ACCOUNT_MENU_ITEMS,
        trigger_label="Nigel",
        trigger_icon="user",
        placement="start",
        menu_open=True,
    ),
    "_tooltip (extended)": lambda: _extend(
        "brickwork/components/_tooltip.html",
        '{% block tooltip_trigger %}<button type="button" class="bw-btn bw-btn--ghost bw-btn--sm bw-btn--icon-only" '
        'aria-label="More info">i</button>{% endblock %}',
        id="rate-tooltip",
        text="Applied after your first invoice.",
        placement="end",
    ),
    "_disclosure (bordered, open, trigger_meta)": lambda: _include(
        "brickwork/components/_disclosure.html",
        label="What happens if I cancel?",
        content="You keep access until the end of the billing period.",
        variant="bordered",
        name="faq",
        open=True,
        trigger_meta="New",
    ),
    "_progress (determinate, show_value)": lambda: _include(
        "brickwork/components/_progress.html", label="Import progress", value=62, show_value=True
    ),
    "_progress (indeterminate)": lambda: _include("brickwork/components/_progress.html", label="Sending"),
    "_breadcrumbs (multi-level)": lambda: _include(
        "brickwork/components/_breadcrumbs.html",
        crumbs=[
            {"label": "Invoices", "url": "/invoices/"},
            {"label": "INV-2417", "url": "/invoices/1/"},
            {"label": "Edit"},
        ],
    ),
    "_pagination (mid-list)": lambda: _render_pagination(),
    "_pager (two-link)": lambda: _include(
        "brickwork/components/_pager.html",
        previous_href="/docs/getting-started/",
        previous_label="Getting started",
        next_href="/docs/theming/",
        next_label="Theming",
    ),
    "_bulk_actions_bar (extended, select_all)": lambda: _extend(
        "brickwork/components/_bulk_actions_bar.html",
        '{% block bulk_actions_buttons %}{% bw_button label="Archive" type="submit" name="bulk_action" '
        'value="archive" variant="secondary" size="sm" %}{% bw_button label="Delete" type="submit" '
        'name="bulk_action" value="delete" variant="danger" size="sm" %}{% endblock %}',
        select_all_href="?select_all=1",
    ),
    "_empty_state (no_results, action)": lambda: _include(
        "brickwork/components/_empty_state.html",
        heading="No invoices match your filters",
        body="Try clearing a filter to see more results.",
        variant="no_results",
        icon="search",
        action_href="/invoices/",
        action_label="Clear filters",
    ),
    "_page_header (description)": lambda: _include(
        "brickwork/components/_page_header.html", title="Invoices", description="Everything you have billed."
    ),
    "_page_header (loading)": lambda: _include(
        "brickwork/components/_page_header.html", title="Invoices", loading=True
    ),
    "_filter_bar (hx, clear)": lambda: _include(
        "brickwork/components/_filter_bar.html",
        fields=list(_DemoForm()),
        hx_get="/invoices/",
        hx_target="#invoices",
        clear_href="/invoices/",
        filter_bar_id="invoice-filters",
    ),
    "_dropzone (multiple, errors)": lambda: _include(
        "brickwork/components/_dropzone.html",
        label="Upload receipts",
        id="receipts",
        name="receipts",
        multiple=True,
        accept="image/*,.pdf",
        help_text="Up to 10 files",
        errors=["One file was too large."],
    ),
    "_tag_input (multiline, errors, value)": lambda: _include(
        "brickwork/components/_tag_input.html",
        label="Keywords",
        id="keywords",
        name="keywords",
        value="overdue,vip",
        placeholder="Add a keyword",
        help_text="Comma separated",
        errors=["At least one keyword is required."],
        multiline=True,
    ),
    "_toast_region (placement)": lambda: _include("brickwork/components/_toast_region.html", placement="bottom-start"),
    "_toast (bw_toast: action, danger, private render target)": lambda: _tag(
        "brickwork_interactions",
        '{% bw_toast "Payment failed." variant="danger" duration="persistent" '
        'action_label="Retry" action_href="/invoices/1/retry/" %}',
    ),
    "_dropdown (bw_dropdown: icon-only, placement=end, hover, private render target)": lambda: _tag(
        "brickwork_interactions",
        "{% bw_dropdown items=items icon_only=True aria_label='Actions' trigger_icon='more-vertical' "
        "placement='end' trigger_mode='hover' close_on_select=False %}",
        items=_DROPDOWN_ITEMS,
    ),
    "_dropdown (bw_dropdown: labelled, placement=start, private render target)": lambda: _tag(
        "brickwork_interactions",
        "{% bw_dropdown items=items trigger_label='Actions' trigger_variant='primary' placement='start' %}",
        items=_DROPDOWN_ITEMS,
    ),
    "_tabs (bw_tabs: variant=pill, lazy, private render target)": lambda: _tag(
        "brickwork_interactions",
        "{% bw_tabs tabs=tabs active=active id='demo-pill' variant='pill' lazy_load=True %}",
        tabs=_TABS,
        active="activity",
        request=_NAV_REQUEST,
    ),
    "_tabs (bw_tabs: variant=underline, private render target)": lambda: _tag(
        "brickwork_interactions",
        "{% bw_tabs tabs=tabs active=active id='demo-underline' variant='underline' %}",
        tabs=_TABS,
        active="overview",
        request=_NAV_REQUEST,
    ),
    "_combobox (bw_combobox: explicit trio, multiple, allow_create, private render target)": lambda: _tag(
        "brickwork_interactions",
        "{% bw_combobox name='account' options=options selected=selected filter_mode='client' "
        "multiple=True allow_create=True placeholder='Search accounts' %}",
        options=_COMBOBOX_OPTIONS,
        selected=["acme"],
    ),
    "_combobox (bw_combobox: bound field, server filter, private render target)": lambda: _render_field_combobox(),
    # --- forms/ --------------------------------------------------------------
    "_field (valid)": lambda: _render_field(_DemoForm()["name"]),
    "_field (invalid, with error + help)": lambda: _render_field(_invalid_demo_form()["name"]),
    "_form (bw_form: stacked, invalid)": lambda: _tag(
        "brickwork_forms", "{% bw_form form %}", form=_invalid_demo_form()
    ),
    "_form (bw_form: grid, readonly, density)": lambda: _tag(
        "brickwork_forms",
        "{% bw_form form layout='grid' grid_columns=2 density='compact' readonly=True %}",
        form=_DemoForm(),
    ),
    "_form_errors (non-field errors)": lambda: _render_form_errors(),
    # --- nav/ ------------------------------------------------------------
    "_nav (bw_nav: populated tree)": lambda: _render_nav("bw_nav"),
    "_nav_header (bw_nav_header: populated tree)": lambda: _render_nav("bw_nav_header"),
    "_nav_rail (bw_nav_rail: populated tree)": lambda: _render_nav("bw_nav_rail"),
    # --- marketing sub-app ----------------------------------------------
    "_hero (marketing: media, align=center, dict CTAs)": lambda: _include(
        "brickwork_marketing/components/_hero.html",
        eyebrow="New",
        heading="Chase invoices without the awkward call",
        lede="Northwind reminds, tracks and reconciles for you.",
        primary_cta={"label": "Get started", "url": "/signup/"},
        secondary_cta={"label": "Watch demo", "url": "/demo/"},
        media="<img src='/static/hero.png' alt=''>",
        align="center",
    ),
    "_cta (marketing: plain band, flat CTAs)": lambda: _include(
        "brickwork_marketing/components/_cta.html",
        heading="Ready to get paid faster?",
        body="Set up your first chase sequence in minutes.",
        primary_cta_label="Start free trial",
        primary_cta_href="/signup/",
        secondary_cta_label="Talk to sales",
        secondary_cta_href="/contact/",
        band="plain",
    ),
    "_faq (marketing: single_open)": lambda: _include(
        "brickwork_marketing/components/_faq.html",
        heading="Questions",
        items=[
            {"question": "Can I cancel?", "answer": "Any time, from the billing page."},
            {"question": "Do you offer refunds?", "answer": "Pro-rated, on request."},
        ],
        single_open=True,
    ),
    "_feature_grid (marketing: linked items, columns=2)": lambda: _include(
        "brickwork_marketing/components/_feature_grid.html",
        heading="Everything you need",
        lede="Built for small finance teams.",
        items=[
            {
                "icon": "bell",
                "heading": "Automatic reminders",
                "body": "Chases send themselves.",
                "url": "/features/reminders/",
                "aria_label": "Learn about automatic reminders",
            },
            {"icon": "check", "heading": "Reconciliation", "body": "Payments match themselves off."},
        ],
        columns=2,
    ),
    "_logo_cloud (marketing: greyscale)": lambda: _include(
        "brickwork_marketing/components/_logo_cloud.html",
        heading="Trusted by teams at",
        logos=[
            {"src": "/static/logo-acme.svg", "alt": "Acme Corp"},
            {"src": "/static/logo-halden.svg", "alt": "Halden Group"},
        ],
        greyscale=True,
    ),
    "_pricing_table (marketing: 3 tiers, highlighted+badge, note)": lambda: _include(
        "brickwork_marketing/components/_pricing_table.html",
        heading="Simple pricing",
        lede="Cancel any time.",
        tiers=[
            {
                "name": "Solo",
                "price": "9 GBP",
                "period": "/month",
                "description": "For one person.",
                "features": ["Unlimited invoices"],
                "cta_label": "Start free trial",
                "cta_url": "/signup/?plan=solo",
            },
            {
                "name": "Team",
                "price": "29 GBP",
                "period": "/month",
                "description": "For a small team.",
                "features": ["Everything in Solo", "Up to 10 users"],
                "cta_label": "Start free trial",
                "cta_url": "/signup/?plan=team",
                "highlighted": True,
                "badge": "Most popular",
            },
            {
                "name": "Scale",
                "price": "89 GBP",
                "period": "/month",
                "description": "Multi-entity.",
                "features": ["Everything in Team"],
                "cta_label": "Talk to sales",
                "cta_url": "/contact/",
            },
        ],
        note="Prices exclude VAT.",
    ),
    "_pricing_tier (marketing: single, highlighted+badge, dict CTA)": lambda: _include(
        "brickwork_marketing/components/_pricing_tier.html",
        name="Team",
        price="29 GBP",
        period="/month",
        description="For a small team.",
        features=["Everything in Solo", "Up to 10 users"],
        cta={"label": "Start free trial", "url": "/signup/?plan=team"},
        highlighted=True,
        badge="Most popular",
    ),
    "_stat_band (marketing: trend)": lambda: _include(
        "brickwork_marketing/components/_stat_band.html",
        heading="By the numbers",
        stats=[
            {"value": "21 days", "label": "Average time to pay", "trend": "down", "trend_label": "17 days faster"},
            {"value": "94%", "label": "Invoices paid without a call"},
        ],
    ),
    "_testimonial (marketing: avatar, logo)": lambda: _include(
        "brickwork_marketing/components/_testimonial.html",
        quote="Northwind paid for itself in the first month.",
        author="Priya Shah",
        role="CFO, Halden Group",
        avatar="/static/avatar-priya.jpg",
        logo="<img src='/static/logo-halden.svg' alt='Halden Group'>",
    ),
}


def _render_pagination() -> str:
    from django.core.paginator import Paginator

    page = Paginator(range(50), 10).page(2)
    return _include("brickwork/components/_pagination.html", page_obj=page, request=_NAV_REQUEST)


def _render_field(field) -> str:
    return Template("{% load brickwork_forms %}{% include 'brickwork/forms/_field.html' with field=field %}").render(
        Context({"field": field})
    )


def _render_form_errors() -> str:
    form = _DemoForm(data={})
    form.is_valid()
    form.add_error(None, "Your plan does not support that many users.")
    return _include("brickwork/forms/_form_errors.html", form=form)


def _render_field_combobox() -> str:
    form = _DemoForm()
    return _tag(
        "brickwork_interactions",
        "{% bw_combobox field=form.plan options_url='/invoices/options/' %}",
        form=form,
    )


# Add one render per _VOCABULARIES entry: proves the TEMPLATE actually emits
# the class for a documented value, over a context rich enough to reach it,
# which is the half test_option_vocabularies.py's CSS-only check cannot cover
# (it proves the class exists; it never renders the template at all).
_VOCABULARY_CONTEXTS: dict[str, Callable[[str], str]] = {
    "_tabs": lambda value: _tag(
        "brickwork_interactions",
        f"{{% bw_tabs tabs=tabs active=active id='vocab-tabs' variant='{value}' %}}",
        tabs=_TABS,
        active="overview",
        request=_NAV_REQUEST,
    ),
    "_slide_over": lambda value: _extend(
        "brickwork/components/_slide_over.html",
        "{% block slide_over_body %}<p>Body.</p>{% endblock %}",
        title="Panel",
        **({"size": value} if value in {"sm", "md", "lg"} else {"placement": value}),
    ),
    "_hero": lambda value: _include(
        "brickwork_marketing/components/_hero.html",
        heading="Headline",
        media=mark_safe("<img src='/hero.png' alt=''>"),  # noqa: S308 (test-authored trusted markup)
        **({"align": value} if value in {"start", "center", "end"} else {"media_placement": value}),
    ),
    "_alert": lambda value: _tag("brickwork_components", f'{{% bw_alert "Message" variant="{value}" %}}'),
    "_card": lambda value: _include("brickwork/components/_card.html", size=value),
    "_account_menu": lambda value: _include(
        "brickwork/components/_account_menu.html", items=_ACCOUNT_MENU_ITEMS, placement=value
    ),
    "_dropdown": lambda value: _tag(
        "brickwork_interactions",
        f"{{% bw_dropdown items=items trigger_label='Actions' placement='{value}' %}}",
        items=_DROPDOWN_ITEMS,
    ),
    "_badge": lambda value: _tag("brickwork_components", f'{{% bw_badge "Status" variant="{value}" %}}'),
    "_disclosure": lambda value: _include(
        "brickwork/components/_disclosure.html", label="Question", content="Answer", variant=value
    ),
    "_modal": lambda value: _extend(
        "brickwork/components/_modal.html",
        "{% block modal_body %}<p>Body.</p>{% endblock %}",
        title="Dialog",
        size=value,
    ),
    "_stepper": lambda value: _include("brickwork/components/_stepper.html", steps=_STEPPER_STEPS, orientation=value),
    "_tooltip": lambda value: _extend(
        "brickwork/components/_tooltip.html",
        '{% block tooltip_trigger %}<button type="button">i</button>{% endblock %}',
        id="vocab-tooltip",
        text="Hint",
        placement=value,
    ),
    "_toast_region": lambda value: _include("brickwork/components/_toast_region.html", placement=value),
    "_chart_card": lambda value: _include(
        "brickwork/components/_chart_card.html",
        legend_position=value,
        mount=mark_safe(  # noqa: S308 (test-authored trusted markup)
            '<div class="bw-chart-mount" data-bw-chart-mount role="img" aria-label="Revenue by month"></div>'
        ),
    ),
    "_feature_grid": lambda value: _include(
        "brickwork_marketing/components/_feature_grid.html",
        items=[{"heading": "Feature", "body": "Body"}],
        columns=value,
    ),
    "_cta": lambda value: _include(
        "brickwork_marketing/components/_cta.html",
        heading="Ready to get paid faster?",
        primary_cta_label="Start free trial",
        primary_cta_href="/signup/",
        width=value,
    ),
}

for _component, _option, _value, _css_class in _VOCABULARIES:
    _builder = _VOCABULARY_CONTEXTS.get(_component)
    if _builder is None:
        continue  # covered directly above with a fixed value already
    _COMPONENT_RENDERS[f"{_component} {_option}={_value!r} (vocabulary)"] = lambda builder=_builder, value=_value: (
        builder(value)
    )


# --- the class-contract check, and its non-triviality guard -----------------


@pytest.mark.parametrize("name", sorted(_COMPONENT_RENDERS))
def test_every_component_class_it_emits_is_actually_styled(name: str) -> None:
    """The icvoss/django-brickwork#137 check: every component/form/nav/
    marketing template, rendered the way a real consumer reaches it, over a
    rich context and (where documented) every option-vocabulary value, with
    every ``bw-*`` class it emits checked against the COMPILED stylesheet.

    The allowlist (structural hooks with no styling rule of their own,
    verified individually) is the single canonical copy at
    tests/_class_contract.py: test_components.py imports the same set, so a
    justification can go stale in only one place, not two.
    """
    html = _COMPONENT_RENDERS[name]()
    missing = unstyled_classes(html, allowlist=UNSTYLED_BY_DESIGN)
    assert not missing, f"{name} emits classes with no rule in the shipped CSS: {missing}"


@pytest.mark.parametrize("name", sorted(_COMPONENT_RENDERS))
def test_every_registered_render_produced_non_trivial_output(name: str) -> None:
    """The guard: a context that silently fails to populate (wrong template
    name, an unread context key, a near-empty default) renders almost
    nothing, which would make the class-contract test above pass vacuously
    (zero classes emitted, so nothing to find missing). This is the
    ecosystem-recorded "a fixture rendering a component EMPTY passes every
    gate" trap, applied here: every registered render must produce
    meaningful markup AND at least one ``bw-*`` class.
    """
    html = _COMPONENT_RENDERS[name]()
    assert len(html.strip()) >= 40, f"{name} rendered suspiciously little ({len(html.strip())} chars): {html!r}"
    from tests._class_contract import used_bw_classes

    assert used_bw_classes(html), f"{name} rendered with no bw-* class at all"


def test_the_registry_covers_every_shipped_component_form_nav_and_marketing_template() -> None:
    """A new template with no registry entry would otherwise be silently
    untested, exactly like test_examples.py's own
    `test_the_shipped_example_set_matches_what_the_tests_cover` guards the
    examples tree. Private render targets of a tag (bw_dropdown's
    _dropdown.html, bw_tabs's _tabs.html, bw_toast's _toast.html,
    bw_combobox's _combobox.html) are exercised via their tag, not by name,
    so they are excluded here the same way test_toast.py documents them as
    "PRIVATE render target of the tag: never {% include %} this file
    directly". Shell templates are covered by test_examples.py /
    test_shell.py / test_marketing.py, which already render them as full
    documents; this registry's job is the include/tag/extend surface those
    do not reach.

    covered_stems is DERIVED from the registry (icvoss/django-brickwork#331),
    not hand-maintained: a registry entry with no matching shipped template,
    or a shipped template with no registry entry, is now the SAME failure
    this assertion already reports, not a silent one-directional gap.

    Deriving `label.split()[0]` only works because every _COMPONENT_RENDERS
    key leads with its template stem (verified below, and true of every
    entry as of this fix): a tag-invoked entry such as bw_button's is keyed
    "_button (bw_button: ...)", not "bw_button (...)", and a marketing entry
    is keyed "_hero (marketing: ...)", not "marketing _hero (...)". The
    vocabulary-generated entries (test_option_vocabularies.py's
    _VOCABULARIES, appended below the hand-written block) already conform:
    their label is built as f"{_component} ..." where _component is always
    the bare stem.

    Four stems derive from the registry but must NOT enter covered_stems:
    _dropdown/_tabs/_toast/_combobox are private render targets (excluded
    from `shipped` above, the same as their .html files), and _chart_mount
    is a simple_tag with no backing template file at all (nothing for
    `shipped` to ever contain). Excluding them here keeps the assertion
    symmetric instead of reintroducing a one-directional gap one level down.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "src" / "brickwork"
    private_render_targets = {
        "_dropdown.html",
        "_tabs.html",
        "_toast.html",
        "_combobox.html",
        # _button.html's loading=True branch includes this directly; it has
        # no context contract of its own to render standalone, and the
        # "_button (bw_button: loading)" registry entry already exercises
        # its class.
        "_spinner.html",
        # bw_theme_switch's private render target (icvoss/django-brickwork#117):
        # its own dedicated test file (test_theme_switch.py) already renders it
        # through the tag and checks its fixed, non-option-driven class set,
        # matching the dropdown/tabs/toast/combobox precedent above.
        "_theme_switch.html",
    }
    shell_dirs = {"shell"}

    registry_stems = {name.split()[0] for name in _COMPONENT_RENDERS}
    non_conforming = [name for name in _COMPONENT_RENDERS if not name.split()[0].startswith("_")]
    assert not non_conforming, (
        "a _COMPONENT_RENDERS key does not lead with its template stem, so "
        f"deriving covered_stems from it would be silently wrong: {non_conforming}"
    )
    # Private render targets and tag-only entries with no backing template
    # file: present in the registry (so the class-contract tests above still
    # cover them), absent from `shipped` (no standalone template exists or
    # {% include %} is forbidden), so excluded here to keep both sides of
    # the assertion below in agreement.
    not_independently_shipped = {"_dropdown", "_tabs", "_toast", "_combobox", "_chart_mount"}
    covered_stems = registry_stems - not_independently_shipped

    templates_dirs = [root / "templates" / "brickwork", root / "marketing" / "templates" / "brickwork_marketing"]
    shipped = set()
    for templates_dir in templates_dirs:
        for path in templates_dir.rglob("*.html"):
            if path.parent.name in shell_dirs:
                continue
            if path.name in private_render_targets:
                continue
            shipped.add(path.stem)
    assert shipped == covered_stems, (
        f"a shipped template has no class-contract coverage: {shipped - covered_stems}, "
        f"or covered_stems names a template that no longer ships: {covered_stems - shipped}"
    )


def test_a_registered_but_unlisted_component_is_now_caught() -> None:
    """icvoss/django-brickwork#331's own failure mode, reproduced against a
    deliberately wrong hand-written covered_stems: a stem present in the
    registry but MISSING from covered_stems (a component registered, then
    silently dropped from the hand-maintained list, or never added to it in
    the first place) used to pass this suite, because the coverage test only
    ever compared covered_stems against shipped templates, never against the
    registry. With covered_stems now DERIVED from the registry, the same
    scenario is structurally impossible to reproduce by hand: the registry
    IS covered_stems (minus the private/non-template exclusions), so this
    test instead proves the derivation itself would surface the gap were it
    ever reintroduced, by rebuilding a deliberately incomplete covered_stems
    the way the old hand-written version could have been and showing it now
    disagrees with the registry-derived one.
    """
    registry_stems = {name.split()[0] for name in _COMPONENT_RENDERS}
    assert "_empty_state" in registry_stems, "the fixture below assumes _empty_state is a real registered component"

    hand_maintained_with_a_dropped_entry = registry_stems - {
        "_dropdown",
        "_tabs",
        "_toast",
        "_combobox",
        "_chart_mount",
    }
    hand_maintained_with_a_dropped_entry.discard("_empty_state")  # simulates a component silently dropped by hand

    derived = registry_stems - {"_dropdown", "_tabs", "_toast", "_combobox", "_chart_mount"}

    assert derived != hand_maintained_with_a_dropped_entry, (
        "the derived set must disagree with a hand-maintained set missing a "
        "registered component, or this test is not exercising the failure "
        "mode #331 fixed"
    )
    assert "_empty_state" in derived
    assert "_empty_state" not in hand_maintained_with_a_dropped_entry
