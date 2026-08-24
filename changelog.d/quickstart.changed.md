- **`PILOT-ADOPTION-BRIEF.md` is now `docs/QUICKSTART.md`.** The file was a
  task brief for a finished pilot round, pinned to 0.3.0 and the private index.
  It is now a short public quickstart that orients a newcomer and routes them
  to `docs/INTEGRATION.md` for greenfield wiring or `docs/ADOPTION.md` for
  migrating an existing UI, rather than restating either.
- **PyPI description states a verification claim, not a design claim.** It read
  "Accessible by construction", which contradicted the README's explicit
  framing of accessibility as tested rather than asserted. It now reads "WCAG
  2.2 AA tested in CI". This reaches PyPI on the next release.
