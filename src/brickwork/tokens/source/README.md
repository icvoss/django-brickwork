# brickwork design-token source (DTCG)

The authored source for brickwork's design tokens. `node build-tokens.mjs`
(`npm run build:tokens`) compiles these into the shipped artefacts in
`../../static/brickwork/dist/` (`tokens.css`, `tailwind-theme.css`, `tokens.js`),
with **stable, non-hashed filenames** versioned by the Python package's semver.
Consumers reference the artefacts via plain `{% static %}`; they never run Style
Dictionary themselves (04-interfaces.md section 8).

## Files and tiers

| File | Tier / axis | Notes |
|---|---|---|
| `primitive.tokens.json` | Primitive | Raw oklch colour ramps (Radix-seeded) + spacing/radii/icon-size scales (Open-Props-seeded). NOT the public contract (BR-BW-TOK-001); names may change between minors. |
| `semantic.light.tokens.json` | Semantic, light | Role-named `--bw-color-*` (surface, fg, border, accent, status) plus the theme-variant `--bw-state-*` overlays and `--bw-elevation-*` ramp. Names ARE the public contract; values are brand-overridable. Derived tokens carry a live color-mix expression in `$extensions.bw.derived` (docs/DESIGN.md section 3); `$value` stays the resolved-default regression baseline. |
| `semantic.dark.tokens.json` | Semantic, dark | The **authored** dark values (BR-BW-TOK-002): same names, deliberately chosen dark oklch values, never derived from light. Derivations use dark-tuned constants. |
| `component.tokens.json` | Component | Per-component tokens (icon size/stroke, button radius, drawer width, disabled opacity), typography scales (`--bw-font-*`), focus-ring geometry, the z-index scale, and opacity roles. |
| `typography.tokens.json` | Component | The `--bw-text-<role>-*` type-role bundles (DESIGN.md section 7.4): every value a var() reference into the `--bw-font-*` scales so overrides cascade. |
| `motion.tokens.json` | Component | Durations, easing curves, and the composite `--bw-transition-*` shorthands (DESIGN.md section 8). |
| `density.{comfortable,compact,spacious}.tokens.json` | Density axis | Spacing/sizing scales per density (BR-BW-TOK-004: density never affects colour). Same names across the three. |

## The four axes -> CSS selectors

The build composes the source into scoped selectors so a live attribute switch
re-resolves with no recompile (BR-BW-TOK-004, four axes compose independently):

- **Brand**: a consumer's own `overrides.json` supplies values against these
  names (mechanism is README Open Question 5, resolved by the v1 pilots).
- **Theme**: `:root` / `[data-theme="light"]` carry the light values;
  `[data-theme="dark"]` overrides only the theme-variant families
  (`--bw-color-*`, `--bw-state-*`, `--bw-elevation-*`; dark authored,
  BR-BW-TOK-002).
- **Density**: `[data-density="compact|comfortable|spacious"]` overrides only the
  `--bw-density-*` scale; `:root` carries `comfortable` as the default.
- **Direction (RTL)**: NOT a token axis. Handled by logical CSS properties in the
  templates/components (BR-BW-TOK-005); the `dir` attribute drives the browser's
  own logical-property resolution.

## Rules enforced here (see 02-business-rules.md)

- **BR-BW-TOK-001**: only semantic/component names are the public contract;
  `--bw-primitive-*` names are free to change.
- **BR-BW-TOK-002**: dark values are authored in `semantic.dark.tokens.json`,
  never computed from light.
- **BR-BW-TOK-003**: every colour value is oklch (no hex, no hsl) in source.
- **BR-BW-TOK-004**: the four axes compose independently.
- **BR-BW-TOK-006**: brand overrides target brickwork's own names, never Radix's
  or Open Props' upstream scale numbers.

`tests/test_tokens.py` asserts these against both the source and the built
artefacts.
