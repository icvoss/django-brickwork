# Preview

Northline is a documentation skeleton. Prove overrides by:

1. Loading [tokens.css](../tokens.css) after brickwork's stylesheet.
2. Setting `data-bw-brand="northline"` on the shell root when exercising this
   pack.
3. Rendering `{% bw_token_specimen %}` (THM-016) on a theming or brand page so
   light and dark panes show the live cascade, including fg-on-accent contrast
   on the paired sample chip.

**Package visual-bar leg:** from the package root,
`npm run visual-bar:fixtures:northline` then
`npm run visual-bar:capture:northline` exercises the same load order on the
VISUAL-BAR S1 to S8 map (private stills under `docs/audits/_stills/`). See
[VISUAL-BAR.md](../../../../VISUAL-BAR.md) section 5 and
[_stills/README.md](../../../../audits/_stills/README.md).

Do not treat a static HTML kit as a second component catalogue.
