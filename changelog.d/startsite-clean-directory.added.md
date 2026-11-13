- **`python -m brickwork startsite DIRECTORY` runs with no Django project.**
  `manage.py startsite` needed a project to run in, so a consumer starting from
  an empty directory had to build one by hand before they could run the command
  that builds one. The new module entry point configures just enough Django to
  run `startsite` and nothing else, so `pip install django-brickwork` followed by
  `python -m brickwork startsite .` is the whole clean-directory path. It never
  reads the caller's settings. `manage.py startsite` is unchanged and still works
  inside a project.
- **`startsite --starter` selects one of two starters.** `public-site` is the
  existing landing page and docs home with no database. `data-app` is new: an
  `invoices` app with a model, a migration and a `seed_demo` command, a dashboard
  whose figures are aggregates over the rows, and a filterable, sortable,
  paginated list, both pages copied from the shipped `app/dashboard.html` and
  `app/list.html` examples. Both starters pass the same WCAG 2.2 AA gate the
  package does, with `data-app` scanned populated.
- **Emitted projects carry a `requirements.txt`** pinning the django-brickwork
  that wrote them, and a `.gitignore`.
- **QUICKSTART documents the existing-project path as one complete page.** Path B
  shows the settings lines, URL, view, context, template and static brand
  stylesheet in one place, and `tests/test_quickstart_docs.py` writes those
  blocks into a fresh `startproject` project to prove they work as written.
