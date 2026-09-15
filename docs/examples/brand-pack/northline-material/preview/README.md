# Preview

Northline-material is an L3 documentation skeleton. Prove overrides by:

1. Loading [tokens.css](../tokens.css) after brickwork's stylesheet.
2. Setting `data-bw-brand="northline-material"` on the shell root.
3. Rendering shell, card, form, and one marketing band, plus
   `{% bw_token_specimen %}` so radius/elevation and raised surface are visible
   without DevTools archaeology.

Do not treat a static HTML kit as a second component catalogue.

Prefer `{% bw_token_specimen level="L3" %}` (or `L4` for dense) so radius, elevation, and type samples are visible without DevTools.
