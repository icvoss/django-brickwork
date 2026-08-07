- **The hero no longer scrolls the page sideways on a phone.** Three separate
  causes, all found by the new mobile-first gate and all invisible to the
  existing suites. `.bw-hero__copy` sized to its content rather than its
  container, because `.bw-hero` sets `align-items` to something other than
  `stretch`; the display heading was a fixed 3.75rem, at which a single
  unbreakable word ("Documentation") measures 406px and cannot wrap, overflowing
  any viewport narrower than that; and neither had a wrap fallback. The heading
  is now fluid, capped at the display token so a brand retuning the type scale
  still governs the ceiling. A multi-word heading hid this by wrapping between
  words, which is why the shipped marketing pages never tripped it.
- **A code block no longer widens the page it sits in.** The `<pre>` scrolled
  its own overflow correctly while its `<code>` child painted straight through
  the scroll container, so the document itself scrolled horizontally.
- **`.bw-callout--note` had no CSS rule.** It is the default kind and the
  documented spelling, so it rendered unstyled: the
  icvoss/django-brickwork#120 defect class, caught this time by a test that
  asserts every class an example emits exists in the compiled stylesheet.
