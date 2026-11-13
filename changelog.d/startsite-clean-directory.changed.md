- **`startsite` emits the `public-site` starter by default, which is two pages,
  not three.** The previous default project carried a landing page, an app
  dashboard and a docs home. The dashboard moved into the new `data-app`
  starter, where it reads a database; the default now emits the landing page and
  docs home only. Run `startsite --starter data-app` for the dashboard. Emitted
  output carries no semver guarantee (ADR-095), but a consumer who scripts
  `startsite` and expects `/app/` will find it gone.
- **The emitted brand stylesheet moved from `static/pages/brand.css` to
  `static/brand.css`**, linked as `{% static 'brand.css' %}`, because the two
  starters no longer share an app directory to nest it in. Only projects emitted
  after this release are affected; existing ones are untouched.
- **`startsite` accepts a directory that holds only a `.git`, `.venv` or `venv`
  entry.** It used to refuse any non-empty directory, so the natural first step
  of creating a virtual environment in a fresh project directory made the
  command refuse. Any other entry still refuses before a file is written.
- **`startsite` no longer runs Django's system checks on its own invocation.**
  It writes files and reads no models or URLs, and the clean-directory path has
  no settings module to check. The emitted project's own `manage.py check` is
  unchanged.
- **The `docs/QUICKSTART.md` install path no longer runs `django-admin
  startproject mysite .` before `startsite myproject`.** That sequence made two
  projects, the second nested inside the first.
