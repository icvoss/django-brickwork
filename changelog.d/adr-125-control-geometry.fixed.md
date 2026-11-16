- **Brand token validation accepts the shipped computed control-size tokens.**
  `render_brand_css` rejected `calc(var(--bw-density-control-height) *
  var(--bw-size-step-md))` (a product, which the generic value fallback did not
  allow), the same class of defect as icvoss/django-brickwork#473: the package
  rejecting its own defaults. `*` is now permitted in the fallback; the
  injection guard (no braces, semicolons, remote `url(`) is unchanged.
