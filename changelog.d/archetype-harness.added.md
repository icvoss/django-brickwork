- **The archetype-test harness** (interface-system delivery plan, W0.3).
  `tests/test_archetype_harness.py` auto-discovers every full-page example
  (`kind == "archetype"` in the W0.2 catalogue manifest) and proves each one
  renders, in both themes, from `tests/test_examples.py`'s own
  `_EXAMPLE_CONTEXTS` (the same render-context source the existing example
  tests use, never a second, parallel context table), failing loudly by name
  if a new archetype ships with no matching context entry rather than
  skipping it. `a11y/generate_archetype_fixtures.py` renders the same
  auto-discovered set into `a11y/fixtures/archetypes/`, and the new
  `a11y/archetypes.spec.mjs` sweeps every one of them across the full W0.1
  breakpoint matrix (read live off the shipped `tokens.css`'s
  `--bw-breakpoint-sm/md/lg/xl`, per ADR-079 section 6, never hardcoded) in
  both themes, gating on render success, axe WCAG 2.2 AA, no horizontal
  overflow at the smallest supported width, visibly distinct light/dark
  computed styles, the skip-link no-JS keyboard floor, and (dormant until an
  archetype composes one) WCAG 1.4.3 composited contrast for any
  `media_placement="behind"` hero. A new archetype is enrolled in every one
  of these checks by shipping the example and its catalogue-manifest entry
  alone: no harness file is edited.
