- **Button raise, mirrored from `icvoss/brickwork` (`docs/components/button.md`).**
  The vendored `components.css` source mirror carries the raised Button; the
  shipped `brickwork.css` carries it once the `@bwui/css` pin moves to the
  release that includes it (a later pin bump, not this change). Behaviour that
  changes for an existing consumer when it does: a disabled or loading button
  no longer reacts to hover or press (a disabled ghost used to regain full ink,
  a loading primary painted disabled ink on the hover fill); a link button no
  longer underlines on hover; the leading icon is a plain glyph in the button's
  ink (it picked up the `bw-icon` raised box and a muted ink); a label stays on
  one line; a loading button keeps its variant colours instead of turning
  grey; a host with only `aria-disabled="true"` takes the flat disabled look;
  and `bw-btn--solid` (deprecated, never emitted by a template) is an alias of
  primary. Button geometry reads `--bw-size-control-*-md` (identical values).
  `tests/test_button.py` pins the state markup and the mirror.
