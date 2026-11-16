- **The vendored substrate no longer carries the parallel control text tables.**
  `@bwui/tokens` and `@bwui/css` 0.1.7 and 0.1.8 published
  `--bw-size-text-step-<step>` and `--bw-size-control-font-size-<step>`, which
  ADR-127 forbids; 0.1.9 removes them and points the control font size at
  `--bw-font-size-<step>`. Nothing in django-brickwork read the removed names.
  Closes icvoss/django-brickwork#752.
