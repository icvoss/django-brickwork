- **The Documentation family opens with two copy-paste archetypes**
  (icvoss/django-brickwork#408, icvoss/django-brickwork#409).
  `examples/docs/home.html` is a documentation home: a search box leading the
  page, three hand-ranked start-here cards, a short list of frequently opened
  pages, and a real empty state for a docs site whose shell has shipped ahead
  of its content. `examples/docs/article.html` is a documentation article: a
  lede, linkable headings, two code panels taking their multi-line source from
  the view, an editorial warning callout, a scrollable data table and prev/next
  links. Both extend `brickwork/shell/docs.html`, so they are the first shipped
  templates to use the docs shell, and the first bound by
  `tests/test_family_boundary.py`'s docs entry: neither emits a
  marketing-family class, and the arrangement uses `.bw-band-grid--3` rather
  than `.bw-feature-grid--3`, per ADR-090 decision 1.

  Both are pure composition, with no bespoke CSS, and both are enrolled in the
  archetype harness, so each is now rendered and axe-scanned in light and dark
  at every supported width. The Documentation family previously shipped nothing
  at all, so a team wanting a docs site had to compose the surface from the
  marketing shell and invent the rest; the required-archetype table in
  `docs/INTERFACE-SYSTEM.md` names seven for this family, and these are the
  first two of them.
