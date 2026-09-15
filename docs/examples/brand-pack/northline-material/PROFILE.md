# Northline-material profile

Level claimed: L3
Light + dark: yes
Axes authored:
  - L1 colours + `--bw-color-surface-raised`
  - L2 font families
  - L3 radius (`--bw-radius-sm` / `-md` / `-lg`) plus `--bw-radius-xl`
    for modal/toast overlay chrome (beyond L3 minimum)
  - L3 elevation (`--bw-elevation-1` / `-2` / `-3`) plus `--bw-elevation-4`
    for open-modal altitude (beyond L3 minimum)
Kit exceptions: none
Preview routes: shell, card, form, one marketing band under
  `data-bw-brand="northline-material"` after tokens.css; prefer
  `{% bw_token_specimen %}` plus live kit surfaces
Contrast: fg-on-accent light and dark (same northline values; verify ≥ 4.5:1)
Deferred: L4 spacing/density; further surface ladder (sunken/overlay);
  toast `--bw-elevation-5`

Fictional L3 torture pack: soft radius and heavier elevation so material
language is obvious on a white canvas (card, button, modal). Not a
recommended product look. See [THEME.md](../../../THEME.md).
