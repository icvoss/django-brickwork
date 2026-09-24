- **Hero `width="bleed"` keeps the page gutter** (follow-up to
  icvoss/django-brickwork#710). In 4.3.0 the bleed hero's inline padding was
  `max(gutter, cap)`, so on viewports wider than the marketing measure the
  copy and media sat one page gutter outside every other band's content
  edge. It is now cap plus gutter, matching the rail rule and
  `.bw-section__inner`. No change on viewports narrower than the measure.
