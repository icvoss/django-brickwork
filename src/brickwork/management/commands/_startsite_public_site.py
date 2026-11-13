"""The ``public-site`` starter's payload (ADR-095, icvoss/django-brickwork#470).

A public-facing site with no database: a marketing landing page (from the
shipped ``marketing/landing.html`` example) and a documentation home (from
``docs/home.html``), each with the view that supplies its context. Its pages
are static content typed into views and templates, which is the honest shape
for a brochure or docs site; the sibling ``data-app`` starter is the one that
reads from a database.

Nothing here is supported surface (ADR-095 section 3): see
``_startsite_payload.py``.
"""

from __future__ import annotations

from brickwork.management.commands._startsite_payload import (
    BRAND_CSS_PATH,
    GITIGNORE,
    MANAGE_PY,
    WSGI_PY,
    brand_css,
    emitted_page,
    requirements_txt,
    settings_py,
)

# --- urls.py ---------------------------------------------------------------

URLS_PY = '''"""URLconf for the project `manage.py startsite` emitted (ADR-095).

Yours from the moment it was written. Wires the two starting pages this
command generated; add your own routes here as the project grows.
"""

from django.urls import path

from pages import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("docs/", views.docs_home, name="docs-home"),
]
'''

# --- nav.py ------------------------------------------------------------

NAV_PY = '''"""Navigation config for the project `manage.py startsite` emitted (ADR-095).

Yours from the moment it was written. Validated at import via
validate_nav_config (brickwork's own documented pattern, docs/INTEGRATION.md
section 2), so a bad nav tree fails at startup, never at first render.

nav_items / nav_active is a convention the shipped example pages use, not a
brickwork contract: no shell reads a nav variable from context, they expose
blocks a page fills with {% bw_nav %}. This file follows that convention
because the emitted docs page does; it is not an API you must keep.
"""

from brickwork.models import NavItem
from brickwork.services.navigation import validate_nav_config

NAV = (
    NavItem(key="home", label="Home", url_name="landing", icon="home"),
    NavItem(key="docs", label="Docs", url_name="docs-home", icon="file"),
)

validate_nav_config(NAV)
'''

# --- views.py ------------------------------------------------------------

VIEWS_PY = '''"""Views for the project `manage.py startsite` emitted (ADR-095).

Yours from the moment it was written. Each view supplies exactly the context
its page template needs; see that template's own leading comment (copied
from the brickwork example it started from) for the full contract. Extend or
replace these however this project needs.
"""

from django.shortcuts import render
from django.urls import resolve
from django.utils.safestring import mark_safe

from brickwork.services.navigation import resolve_active_item

from .nav import NAV


def landing(request):
    """The marketing landing page (from brickwork's examples/marketing/landing.html)."""
    logos = [
        {"src": "https://placehold.co/120x32?text=Acme", "alt": "Acme"},
        {"src": "https://placehold.co/120x32?text=Globex", "alt": "Globex"},
        {"src": "https://placehold.co/120x32?text=Initech", "alt": "Initech"},
    ]
    features = [
        {
            "icon": "folder",
            "heading": "Organise everything",
            "body": "Keep every project, file and conversation in one searchable place.",
        },
        {
            "icon": "users",
            "heading": "Built for teams",
            "body": "Invite your team and share context without a single lost thread.",
        },
        {
            "icon": "settings",
            "heading": "Configured your way",
            "body": "Every workspace is different. Set it up the way your team works.",
        },
    ]
    feature_rows = [
        {
            "heading": "Reminders that go out without you",
            "body": "Set the schedule once. Northwind sends the nudges and stops when paid.",
        },
        {
            "heading": "Know who is about to run late",
            "body": "Every account carries a prediction based on how it has actually paid you.",
        },
    ]
    stats = [
        {"value": "2,400+", "label": "Teams onboarded"},
        {"value": "99.98%", "label": "Uptime last quarter"},
        {"value": "4.8/5", "label": "Average review score"},
    ]
    footer_groups = [
        {
            "heading": "Product",
            "links": [
                {"label": "Features", "href": "/features/"},
                {"label": "Pricing", "href": "/pricing/"},
            ],
        },
        {
            "heading": "Company",
            "links": [
                {"label": "About", "href": "/about/"},
                {"label": "Contact", "href": "/contact/"},
            ],
        },
    ]
    # Beside-hero media: layered product chrome (tokens only; example-owned SVG).
    hero_media = mark_safe(
        '<div class="bw-product-chrome bw-product-chrome--stack" aria-hidden="true">'
        '<div class="bw-product-chrome__frame bw-product-chrome__frame--rear"></div>'
        '<div class="bw-product-chrome__frame">'
        '<div class="bw-product-chrome__bar"><span class="bw-product-chrome__title">'
        "Open invoices</span></div>"
        '<div class="bw-product-chrome__stage"></div>'
        "</div></div>"
    )
    return render(
        request,
        "pages/landing.html",
        {
            "logos": logos,
            "features": features,
            "feature_rows": feature_rows,
            "stats": stats,
            "footer_groups": footer_groups,
            "hero_media": hero_media,
        },
    )


def docs_home(request):
    """The docs home page (from brickwork's examples/docs/home.html)."""
    active = resolve_active_item(NAV, resolve(request.path))
    return render(
        request,
        "pages/docs_home.html",
        {
            "nav_items": NAV,
            "nav_active": active,
            # No search view is scaffolded by startsite; point this at your
            # own search endpoint once you build one.
            "docs_search_action": "/docs/search/",
            "has_published_docs": True,
        },
    )
'''


def landing_html() -> str:
    return emitted_page("marketing/landing.html", "pages/templates/pages/landing.html")


def docs_home_html() -> str:
    return emitted_page("docs/home.html", "pages/templates/pages/docs_home.html")


# --- Project README ---------------------------------------------------------

README_MD = """# This project was started with `manage.py startsite` (public-site)

Everything in this directory is yours from the moment it was written
(ADR-095 in django-brickwork). There is no update command and no upgrade
path: this is a one-time emission, not a framework that reaches back into
your files later. Edit anything here however your project needs.

## Run it

```
python manage.py runserver
```

Then open http://127.0.0.1:8000/ for the landing page and /docs/ for the
docs home. There is no database to migrate: this starter is a public site
whose content lives in its views and templates.

## What you have

- `mysite/settings.py`: brickwork and brickwork.marketing installed, the
  theme context processor wired, static files configured.
- `pages/nav.py`: a real navigation config, validated at import.
- `pages/views.py`: two views, each supplying the context its page needs.
- `pages/templates/pages/`: two real pages, copied from brickwork's own
  example pages (a marketing landing page and a docs home).
- `static/brand.css`: placeholder brand tokens, contrast-verified, ready for
  you to replace with your own brand.
- `requirements.txt`: the one dependency, pinned to the django-brickwork that
  wrote this project. You own the pin.

## Next steps

1. Edit `static/brand.css` with your real brand colours. Re-verify
   `--bw-color-fg-on-accent` at 4.5:1 against your new accent in each theme;
   see BRANDING.md in the installed django-brickwork package.
2. Edit `pages/nav.py`, `pages/views.py` and the page templates: none of
   it is generated again, so there is nothing to lose by changing it.
3. Read INTEGRATION.md in the installed django-brickwork package for the
   rest of the seams (forms, htmx, the chrome/body boundary) as you build
   past these two pages. Want a database-backed app instead? Run
   `python -m brickwork startsite --starter data-app <empty-directory>`.
"""


def files() -> dict[str, str]:
    """Every file this starter emits, as project-relative path to text."""
    return {
        "manage.py": MANAGE_PY,
        ".gitignore": GITIGNORE,
        "requirements.txt": requirements_txt(),
        "README.md": README_MD,
        "mysite/__init__.py": "",
        "mysite/settings.py": settings_py(app="pages", marketing=True),
        "mysite/urls.py": URLS_PY,
        "mysite/wsgi.py": WSGI_PY,
        "pages/__init__.py": "",
        "pages/nav.py": NAV_PY,
        "pages/views.py": VIEWS_PY,
        "pages/templates/pages/landing.html": landing_html(),
        "pages/templates/pages/docs_home.html": docs_home_html(),
        BRAND_CSS_PATH: brand_css(),
    }
