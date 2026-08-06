- **Every closed option vocabulary is now enforced** (ADR-060 rule 2).
  `{% bw_badge %}` had a documented variant set and no validation at all, so a
  typo emitted a `.bw-badge--<typo>` class that does not exist and failed
  silently; `{% bw_form %}`'s `density` reached `data-density` unvalidated while
  its two sibling arguments on the same tag validated. Both now raise on an
  unknown value.

- **`{% bw_dropdown %}` gains `placement`** (`start` default, `end`), closing
  icvoss/django-brickwork#120. `.bw-dropdown--end` had shipped in every
  consumer's stylesheet since 0.8.0 with no code path able to emit it.

- **A test asserts every documented option value resolves to a real CSS rule**
  (`tests/test_option_vocabularies.py`, ADR-060 rule 3). This is the systematic
  version of the #120 check, and it immediately found three more defects in the
  opposite direction, where a documented DEFAULT emitted a class the stylesheet
  never matched: `.bw-tabs--underline`, `.bw-slide-over--md` and
  `.bw-hero--start` now ship real rules. `.bw-hero--end` is added alongside, so
  the hero's alignment axis is complete (ADR-057 section 1a).
