"""brickwork.tokens: the framework-neutral design-token sub-module.

This sub-module is deliberately Django-free. It holds the DTCG-shaped token
source (``source/``) that Style Dictionary compiles, via the frontend
pipeline, into the shipped artefacts:

  - ``static/brickwork/dist/tokens.css``    (CSS custom properties, all four axes)
  - ``static/brickwork/dist/tailwind-theme.css``  (the @theme inline Tailwind bridge)
  - ``static/brickwork/dist/tokens.js``     (JS re-export for a Vite consumer)

Keeping this module import-free of Django is the discipline that lets it later
extract to a standalone ``brickwork_tokens`` package (via git subtree) without
changing the published token values, if a non-Django consumer ever earns the
split. Do not import anything from ``django`` here.

Token vocabulary: namespaced ``--bw-*``, primitive -> semantic -> component
tiers, four composable axes (brand x theme(light/dark) x density x direction).
shadcn-familiar semantic *concepts*, namespaced *names*. Dark values authored,
never derived; oklch colour space. Neutral primitives seeded from Radix Colors
(MIT); non-colour primitives from Open Props (MIT).
"""
