- **Thirteen more example sections, completing the catalogue's nine types.**
  `pricing` (three-tier, single-plan, comparison-table), `testimonial`
  (single-quote, quote-grid, logo-and-quote), `faq` (single-column, two-column),
  `stats` (inline-band, card-row) and `listing` (card-grid, media-list,
  compact-table) join the four types that shipped in 3.1.0, for 26 sections in
  total. Every one clears the same gates as wave 1: axe WCAG 2.2 AA in both
  themes, the no-JS floor, and no horizontal scroll at 360, 375 or 414px.
- **A card grid is still not a component, now on evidence rather than
  assumption.** The plan deferred the decision until the first two `listing`
  variants existed. They now do, and what they share turned out to be the ENTRY
  CONTRACT (`title`, `summary`, `url`, `meta`), not a grid: the card grid is a
  multi-column layout of vertical stacks and the media list is a single column
  of horizontal rows, and the two share no layout declaration. Promoting a grid
  component would have abstracted the half they do not have in common, so the
  four declarations stay in each example where a consumer can change them.
- **Two sections deliberately take no context where a looping wrapper would
  have.** `pricing/single-plan` includes `_pricing_tier.html` once and `faq/*`
  include `_disclosure.html` once per question, both with flat strings, because
  a consumer copying a static pricing or FAQ band wants to edit words in the
  template rather than wire up a view. Each file documents the list-shaped route
  as the alternative for data-driven content.
