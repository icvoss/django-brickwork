- **The docs shell gains a seam for site-wide header and footer chrome**
  (icvoss/django-brickwork#448). `brickwork/shell/docs.html` had no override
  point outside `<main>`, so a consumer wanting the same header and footer
  the rest of their site carries had to override `{% block shell %}` wholesale
  and reproduce the marketing shell's own internal markup. `docs_site_header`
  and `docs_site_footer` (with `docs_site_header_region` /
  `docs_site_footer_region` wrappers) fill that gap: site-wide chrome, sited
  outside `<main>` entirely, distinct from the pre-existing page-local
  `docs_header` / `docs_footer` (ADR-091 decision 2 is unchanged; a docs
  page header or footer is still for a version switcher or feedback control,
  never site chrome). The whole shell is now wrapped in `.bw-docs-shell`, a
  flex column supplying the sticky-footer layout `.bw-docs` alone could not,
  so a short docs page no longer floats a filled site footer mid-viewport.
  Both new regions are empty by default: an existing consumer's output is
  unaffected until they fill one.
