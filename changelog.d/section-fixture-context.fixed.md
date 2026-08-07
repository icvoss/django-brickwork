- **The a11y fixture rendered every context-taking section empty, so the axe and
  mobile gates were measuring nothing.** `a11y/generate_fixtures.py` supplied
  context to exactly one section (`features/icon-grid`) via an inline
  `if "icon-grid" in name` test, so any other section needing view data stacked
  into the fixture as an empty wrapper and passed every gate while being wholly
  untested. The generator now imports `_SECTION_CONTEXTS` from
  `tests/test_examples.py`, the one place that list is already declared and kept
  exhaustive, and raises rather than writing a fixture if a section renders
  empty. Found by screenshotting the fixture rather than by any test: the
  suite was green throughout, because a blank section violates no assertion.
- **A wide table painted outside its own scroll container, so the PAGE scrolled
  sideways on a phone instead of the table.** `overflow-x: auto` sized and
  scrolled the container correctly (scrollWidth 687 against clientWidth 310 at
  360px) while the table still rendered to its full intrinsic width, putting the
  document 224px past the viewport. Both the pricing comparison table and the
  listing compact table now `contain: paint`, which clips the overflow to the
  container that already owns the scroll. The listing table was not yet tripping
  the mobile gate, so it was fixed as the latent case of the same defect rather
  than left until a longer title surfaced it.
- **Small print in five new sections used `--bw-color-fg-subtle` and failed AA
  contrast** at 2.36:1 against a 4.5:1 requirement. That token is for decorative
  ink whose meaning is carried by adjacent text; every one of these was
  meaningful prose, so they now use `--bw-color-fg-muted` like the rest of the
  kit's captions and notes.
