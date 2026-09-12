# Preview (interim)

Northline is a documentation skeleton. Until the package ships a live token
specimen ([icvoss/django-brickwork#268](https://github.com/icvoss/django-brickwork/issues/268)),
prove overrides in the consuming project by:

1. Loading [tokens.css](../tokens.css) after brickwork's stylesheet.
2. Setting `data-bw-brand="northline"` on the shell root when exercising this
   pack.
3. Rendering any package shell or component page and checking light and dark
   themes, including fg-on-accent contrast on primary buttons.

**Package visual-bar leg:** from the package root,
`npm run visual-bar:fixtures:northline` then
`npm run visual-bar:capture:northline` exercises the same load order on the
VISUAL-BAR S1 to S8 map (private stills under `docs/audits/_stills/`). See
[VISUAL-BAR.md](../../../../VISUAL-BAR.md) section 5 and
[_stills/README.md](../../../../audits/_stills/README.md).

Replace this file with a link to the live specimen route once #268 lands.
Do not treat a static HTML kit as a second component catalogue.
