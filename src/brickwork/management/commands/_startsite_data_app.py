"""The ``data-app`` starter's payload (ADR-095, icvoss/django-brickwork#470).

A product application whose screens read from a database: an ``invoices`` app
with one model, its migration, a seeding command, and two views over the ORM
(a dashboard whose figures are aggregates, and a filterable, sortable,
paginated list). The pages are copied from the shipped ``app/dashboard.html``
and ``app/list.html`` examples, with the example's hard-coded "New invoice" and
"Export" buttons dropped, because this starter scaffolds no create or export
view for them to point at.

Where the ``public-site`` starter types its content into views, this one
computes it, which is the whole difference between a brochure and an app: the
views here are the worked answer to "what does a view that feeds a brickwork
page actually look like when the data is real".

Nothing here is supported surface (ADR-095 section 3): see
``_startsite_payload.py``.
"""

from __future__ import annotations

import re

from brickwork import examples
from brickwork.management.commands._startsite_payload import (
    BRAND_CSS_PATH,
    GITIGNORE,
    MANAGE_PY,
    WSGI_PY,
    brand_css,
    emitted_page_from_source,
    requirements_txt,
    settings_py,
)

URLS_PY = '''"""URLconf for the project `manage.py startsite` emitted (ADR-095).

Yours from the moment it was written. Wires the two starting screens this
command generated; add your own routes here as the project grows.
"""

from django.urls import path

from invoices import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("invoices/", views.invoice_list, name="invoice-list"),
]
'''

NAV_PY = '''"""Navigation config for the project `manage.py startsite` emitted (ADR-095).

Yours from the moment it was written. Validated at import via
validate_nav_config (brickwork's own documented pattern, docs/INTEGRATION.md
section 2), so a bad nav tree fails at startup, never at first render.

nav_items / nav_active is a convention the shipped example pages use, not a
brickwork contract: no shell reads a nav variable from context, they expose
blocks a page fills with {% bw_nav %}. This file follows that convention
because the emitted pages do; it is not an API you must keep.
"""

from brickwork.models import NavItem
from brickwork.services.navigation import validate_nav_config

NAV = (
    NavItem(key="dashboard", label="Dashboard", url_name="dashboard", icon="home"),
    NavItem(key="invoices", label="Invoices", url_name="invoice-list", icon="document"),
)

validate_nav_config(NAV)
'''

MODELS_PY = '''"""The data this starter is about: invoices.

Yours from the moment it was written. Replace Invoice with your own domain
model (or add to it), then run `python manage.py makemigrations` and
`python manage.py migrate`. brickwork never reads your models: the views
turn rows into the plain lists and dicts its components render.
"""

from django.db import models


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"

    reference = models.CharField(max_length=20, unique=True)
    client = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SENT)
    issued_on = models.DateField()

    class Meta:
        ordering = ["-issued_on", "-id"]

    def __str__(self) -> str:
        return f"{self.reference} ({self.client})"
'''

MIGRATION_PY = """from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(max_length=20, unique=True)),
                ("client", models.CharField(max_length=120)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("sent", "Sent"), ("paid", "Paid"), ("overdue", "Overdue")],
                        default="sent",
                        max_length=10,
                    ),
                ),
                ("issued_on", models.DateField()),
            ],
            options={"ordering": ["-issued_on", "-id"]},
        ),
    ]
"""

FORMS_PY = '''"""The list screen's filter form.

Yours from the moment it was written. brickwork's filter bar renders any
form's fields through its own accessible field renderer; the form decides
what the fields are and the view decides what they filter.
"""

from django import forms

from .models import Invoice


class InvoiceFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"placeholder": "Reference or client"}),
    )
    status = forms.ChoiceField(
        required=False,
        label="Status",
        choices=[("", "All statuses"), *Invoice.Status.choices],
    )
'''

SEED_PY = '''"""`python manage.py seed_demo`: fill the database with example invoices.

Yours from the moment it was written. Delete this command once you have real
data. Dates are relative to today, so the dashboard's 30-day comparison and
12-week trend always have something to show whenever you run it.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from invoices.models import Invoice

CLIENTS = [
    "Dunmore Retail",
    "Carrick & Sons",
    "Acme Corp",
    "Halden Foods",
    "Brightwater Ltd",
    "Orwell Studios",
]
COUNT = 36


class Command(BaseCommand):
    help = "Create example invoices so the dashboard and list have data to show."

    def handle(self, *args, **options) -> None:
        if Invoice.objects.exists():
            self.stdout.write("Invoices already exist; nothing seeded.")
            return
        today = timezone.localdate()
        invoices = []
        for i in range(COUNT):
            days_ago = (i * 7) // 3
            if days_ago < 3:
                status = Invoice.Status.DRAFT if i % 4 == 0 else Invoice.Status.SENT
            elif i % 6 == 0:
                status = Invoice.Status.OVERDUE
            else:
                status = Invoice.Status.PAID
            invoices.append(
                Invoice(
                    reference=f"INV-{1000 + COUNT - i}",
                    client=CLIENTS[i % len(CLIENTS)],
                    amount=Decimal(450 + (i * 379) % 2600),
                    status=status,
                    issued_on=today - timedelta(days=days_ago),
                )
            )
        Invoice.objects.bulk_create(invoices)
        self.stdout.write(self.style.SUCCESS(f"Created {len(invoices)} example invoices."))
'''

VIEWS_PY = '''"""Views for the project `manage.py startsite` emitted (ADR-095).

Yours from the moment it was written. Each view reads the database and hands
its page template exactly the context that template asks for; see the
template's own leading comment (copied from the brickwork example it started
from) for the full contract. brickwork never reads your models: it renders the
plain lists, dicts and strings built here.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import render
from django.template import Context, Template
from django.template.loader import render_to_string
from django.urls import resolve
from django.utils import timezone
from django.utils.safestring import mark_safe

from brickwork.services.navigation import resolve_active_item

from .forms import InvoiceFilterForm
from .models import Invoice
from .nav import NAV

PAGE_SIZE = 10
PERIOD_DAYS = 30
TREND_WEEKS = 12

# Sort keys the list's column headers send in ?sort=, mapped to model fields.
# Anything else falls back to DEFAULT_SORT, so a hand-edited URL cannot name
# an arbitrary field.
SORT_FIELDS = {
    "reference": "reference",
    "client": "client",
    "status": "status",
    "amount": "amount",
    "issued": "issued_on",
}
DEFAULT_SORT = "-issued"


def _money(value) -> str:
    return f"\\u00a3{value:,.0f}"


def _change(current: Decimal, previous: Decimal) -> tuple[str, str]:
    """The (trend, label) pair a stat tile wants: direction and its plain-words caption."""
    if previous == 0:
        if current:
            return "up", "New this period"
        return "flat", "No activity in either period"
    delta = (current - previous) / previous * 100
    if round(delta) == 0:
        return "flat", "Level with the prior period"
    direction = "up" if delta > 0 else "down"
    return direction, f"{abs(delta):.0f}% {direction} on the prior period"


def _total(queryset) -> Decimal:
    return queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0")


def _trend_svg(points: list[Decimal]) -> str:
    """A server-rendered trend line (no JS chart engine)."""
    peak = float(max(points)) or 1.0
    steps = len(points) - 1
    coords = [(i * (640 / steps), 200 - (float(p) / peak) * 180 - 10) for i, p in enumerate(points)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = (
        f"M {coords[0][0]:.1f},200 L "
        + " L ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
        + " L 640,200 Z"
    )
    return (
        '<svg class="bw-dashboard-trend" viewBox="0 0 640 200" width="100%" '
        'height="200" role="img" aria-label="Paid revenue by week for the last 12 weeks.">'
        '<defs><linearGradient id="bw-dash-trend-fill" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="var(--bw-color-chart-1)" stop-opacity="0.35"/>'
        '<stop offset="100%" stop-color="var(--bw-color-chart-1)" stop-opacity="0"/>'
        "</linearGradient></defs>"
        f'<path d="{area}" fill="url(#bw-dash-trend-fill)"/>'
        '<polyline fill="none" stroke="var(--bw-color-chart-1)" stroke-width="2.5" '
        f'points="{line}"/>'
        "</svg>"
    )


def _weekly_paid_revenue(today) -> list[Decimal]:
    """Paid revenue per week for the last TREND_WEEKS weeks, oldest first."""
    weekly = [Decimal("0")] * TREND_WEEKS
    window_start = today - timedelta(weeks=TREND_WEEKS)
    paid = Invoice.objects.filter(status=Invoice.Status.PAID, issued_on__gt=window_start)
    for issued_on, amount in paid.values_list("issued_on", "amount"):
        weeks_ago = (today - issued_on).days // 7
        if 0 <= weeks_ago < TREND_WEEKS:
            weekly[TREND_WEEKS - 1 - weeks_ago] += amount
    return weekly


def dashboard(request):
    """The overview (from brickwork's examples/app/dashboard.html), computed from Invoice rows."""
    today = timezone.localdate()
    this_start = today - timedelta(days=PERIOD_DAYS)
    prior_start = this_start - timedelta(days=PERIOD_DAYS)

    paid = Invoice.objects.filter(status=Invoice.Status.PAID)
    revenue = _total(paid.filter(issued_on__gt=this_start))
    prior_revenue = _total(paid.filter(issued_on__gt=prior_start, issued_on__lte=this_start))
    revenue_trend, revenue_label = _change(revenue, prior_revenue)

    raised = Invoice.objects.filter(issued_on__gt=this_start).count()
    prior_raised = Invoice.objects.filter(issued_on__gt=prior_start, issued_on__lte=this_start).count()
    raised_trend, raised_label = _change(Decimal(raised), Decimal(prior_raised))

    overdue = _total(Invoice.objects.filter(status=Invoice.Status.OVERDUE))

    # Weighted scorecard: revenue is the argument; supporting tiles take one
    # column each. span= carries the ranking (see the template's own comment).
    headline_tiles = [
        {
            "content": mark_safe(
                render_to_string(
                    "brickwork/components/_stat_comparison.html",
                    {
                        "label": "Paid revenue",
                        "current": _money(revenue),
                        "previous": _money(prior_revenue),
                        "period_label": f"prior {PERIOD_DAYS} days",
                        "trend": revenue_trend,
                        "trend_label": revenue_label,
                        "size": "lg",
                    },
                )
            ),
            "span": 2,
        },
        {
            "content": mark_safe(
                render_to_string(
                    "brickwork/components/_stat.html",
                    {
                        "label": "Invoices raised",
                        "value": str(raised),
                        "trend": raised_trend,
                        "trend_label": raised_label,
                    },
                )
            ),
        },
        {
            "content": mark_safe(
                render_to_string(
                    "brickwork/components/_stat.html",
                    {"label": "Overdue", "value": _money(overdue)},
                )
            ),
        },
    ]

    weekly = _weekly_paid_revenue(today)
    trend_data_table = Template(
        "{% load brickwork_components %}"
        "{% bw_chart_data_table caption=caption columns=columns rows=rows "
        'data_table_mode="toggle" toggle_label="Show revenue by week" %}'
    ).render(
        Context(
            {
                "caption": "Paid revenue by week (last 12 weeks)",
                "columns": ("Week", "Paid revenue"),
                "rows": [(f"W{i + 1}", _money(value)) for i, value in enumerate(weekly)],
            }
        )
    )

    top_accounts = (
        Invoice.objects.values("client").annotate(total=Sum("amount")).order_by("-total", "client")[:5]
    )
    top_accounts_rows = [
        {"label": row["client"], "amount": int(row["total"]), "value": _money(row["total"])}
        for row in top_accounts
    ]

    activity_columns = [
        {"label": "Invoice", "sortable": False},
        {"label": "Client", "sortable": False},
        {"label": "Status", "sortable": False},
        {"label": "Issued", "sortable": False},
    ]
    activity_rows = [
        {
            "id": f"invoice-{invoice.pk}",
            "cells": [
                invoice.reference,
                invoice.client,
                invoice.get_status_display(),
                f"{invoice.issued_on:%d %b %Y}",
            ],
        }
        for invoice in Invoice.objects.all()[:5]
    ]

    active = resolve_active_item(NAV, resolve(request.path))
    return render(
        request,
        "invoices/dashboard.html",
        {
            "headline_tiles": headline_tiles,
            "trend_mount": mark_safe(_trend_svg(weekly)),
            "trend_data_table": trend_data_table,
            "top_accounts_rows": top_accounts_rows,
            "activity_columns": activity_columns,
            "activity_rows": activity_rows,
            "nav_items": NAV,
            "nav_active": active,
        },
    )


def invoice_list(request):
    """The filterable, sortable, paginated list (from brickwork's examples/app/list.html)."""
    form = InvoiceFilterForm(request.GET or None)
    invoices = Invoice.objects.all()
    if form.is_valid():
        search = form.cleaned_data["q"]
        status = form.cleaned_data["status"]
        if search:
            invoices = invoices.filter(Q(reference__icontains=search) | Q(client__icontains=search))
        if status:
            invoices = invoices.filter(status=status)

    sort = request.GET.get("sort", DEFAULT_SORT)
    if sort.lstrip("-") not in SORT_FIELDS:
        sort = DEFAULT_SORT
    prefix = "-" if sort.startswith("-") else ""
    invoices = invoices.order_by(prefix + SORT_FIELDS[sort.lstrip("-")], "-id")

    page = Paginator(invoices, PAGE_SIZE).get_page(request.GET.get("page"))

    columns = [
        {"label": "Reference", "sortable": True, "sort_key": "reference"},
        {"label": "Client", "sortable": True, "sort_key": "client"},
        {"label": "Status", "sortable": True, "sort_key": "status"},
        {"label": "Amount", "sortable": True, "sort_key": "amount", "align": "end"},
        {"label": "Issued", "sortable": True, "sort_key": "issued"},
    ]
    rows = [
        {
            "id": f"invoice-{invoice.pk}",
            "cells": [
                invoice.reference,
                invoice.client,
                invoice.get_status_display(),
                _money(invoice.amount),
                f"{invoice.issued_on:%d %b %Y}",
            ],
        }
        for invoice in page.object_list
    ]

    active = resolve_active_item(NAV, resolve(request.path))
    return render(
        request,
        "invoices/list.html",
        {
            "invoices": page,
            "filter_form": form,
            "invoice_columns": columns,
            "invoice_rows": rows,
            "current_sort": sort,
            "nav_items": NAV,
            "nav_active": active,
        },
    )
'''

# --- Page templates --------------------------------------------------------

# The example's page_actions block (with the comment that introduces it, where
# there is one). The example points its button at a URL this starter does not
# scaffold, and an emitted starter should not ship a button to a 404.
_PAGE_ACTIONS = re.compile(
    r"(?:\{% comment %\}\nActions sit.*?\{% endcomment %\}\n)?"
    r"\{% block page_actions %\}.*?\{% endblock %\}\n\n?",
    re.DOTALL,
)

# The list example opts its filter bar into htmx. This project loads no htmx and
# the view returns whole pages, so the bar stays a plain GET form (the no-JS
# floor); a consumer adding htmx also adds a partial-returning view.
_HTMX_FILTER = ' hx_get="/invoices/" hx_target="#invoices-table"'


def _without_page_actions(source: str, name: str) -> str:
    adjusted, count = _PAGE_ACTIONS.subn("", source)
    if count != 1 or "{% block page_actions %}" in adjusted:
        raise RuntimeError(f"startsite expected exactly one page_actions block in the {name} example")
    return adjusted


def dashboard_html() -> str:
    source = _without_page_actions(examples.read_example("app/dashboard.html"), "app/dashboard.html")
    return emitted_page_from_source(source, "app/dashboard.html", "invoices/templates/invoices/dashboard.html")


def list_html() -> str:
    source = _without_page_actions(examples.read_example("app/list.html"), "app/list.html")
    if source.count(_HTMX_FILTER) != 1:
        raise RuntimeError("startsite expected the app/list.html example to opt its filter bar into htmx")
    source = source.replace(_HTMX_FILTER, "")
    return emitted_page_from_source(source, "app/list.html", "invoices/templates/invoices/list.html")


# --- Project README ---------------------------------------------------------

README_MD = """# This project was started with `manage.py startsite` (data-app)

Everything in this directory is yours from the moment it was written
(ADR-095 in django-brickwork). There is no update command and no upgrade
path: this is a one-time emission, not a framework that reaches back into
your files later. Edit anything here however your project needs.

## Run it

```
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Then open http://127.0.0.1:8000/ for the dashboard and /invoices/ for the
list. `seed_demo` fills the database with example invoices; the screens
render honest empty states without it.

## What you have

- `mysite/settings.py`: brickwork installed, the theme context processor
  wired, static files configured, SQLite for the database.
- `invoices/models.py` and `invoices/migrations/`: one model, `Invoice`.
- `invoices/views.py`: a dashboard whose figures are aggregates over the
  database, and a list with search, status filter, sortable columns and
  pagination. Each view turns rows into the plain lists and dicts the page
  templates ask for.
- `invoices/templates/invoices/`: two real pages, copied from brickwork's
  own example pages (an app dashboard and an app list).
- `invoices/nav.py`: a real navigation config, validated at import.
- `invoices/management/commands/seed_demo.py`: example data. Delete it once
  you have real data.
- `static/brand.css`: placeholder brand tokens, contrast-verified, ready for
  you to replace with your own brand.
- `requirements.txt`: the one dependency, pinned to the django-brickwork that
  wrote this project. You own the pin.

## Next steps

1. Replace `Invoice` with your own model, then `python manage.py
   makemigrations` and `python manage.py migrate`. Update the two views to
   read it.
2. Edit `static/brand.css` with your real brand colours. Re-verify
   `--bw-color-fg-on-accent` at 4.5:1 against your new accent in each theme;
   see BRANDING.md in the installed django-brickwork package.
3. Read INTEGRATION.md in the installed django-brickwork package for the
   rest of the seams (forms, htmx 422 loop, the chrome/body boundary) as you
   add create and edit screens. Want a public site instead? Run
   `python -m brickwork startsite --starter public-site <empty-directory>`.
"""


def files() -> dict[str, str]:
    """Every file this starter emits, as project-relative path to text."""
    return {
        "manage.py": MANAGE_PY,
        ".gitignore": GITIGNORE,
        "requirements.txt": requirements_txt(),
        "README.md": README_MD,
        "mysite/__init__.py": "",
        "mysite/settings.py": settings_py(app="invoices", marketing=False),
        "mysite/urls.py": URLS_PY,
        "mysite/wsgi.py": WSGI_PY,
        "invoices/__init__.py": "",
        "invoices/models.py": MODELS_PY,
        "invoices/forms.py": FORMS_PY,
        "invoices/nav.py": NAV_PY,
        "invoices/views.py": VIEWS_PY,
        "invoices/migrations/__init__.py": "",
        "invoices/migrations/0001_initial.py": MIGRATION_PY,
        "invoices/management/__init__.py": "",
        "invoices/management/commands/__init__.py": "",
        "invoices/management/commands/seed_demo.py": SEED_PY,
        "invoices/templates/invoices/dashboard.html": dashboard_html(),
        "invoices/templates/invoices/list.html": list_html(),
        BRAND_CSS_PATH: brand_css(),
    }
