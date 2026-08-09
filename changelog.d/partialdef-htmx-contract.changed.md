- The HTMX 422 form-validation recipe in `docs/INTEGRATION.md` now uses a Django 6.0
  template partial rather than a separate hand-authored fragment file. The form region
  and the page it lives in are one file addressed by fragment name, so the two cannot
  drift, and there is no `partials/` template to keep in sync. The package has mandated
  Django 6.0 since BR-BW-TPL-004, so the previous recipe was teaching a workaround its
  own floor had already made unnecessary.
