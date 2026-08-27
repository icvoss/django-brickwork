// ESLint flat config for the accessibility gate's Playwright specs
// (icvoss/django-brickwork#276).
//
// Scope is deliberately narrow: a11y/**/*.spec.mjs only. This is not
// general JS linting for the repo (build-tokens.mjs, vite.config.js,
// frontend/src/js/* are out of scope; that is a separate decision with
// a separate cost).
//
// Rules are hand-picked rather than extending the plugin's recommended
// set, so every rule earns its place against one named defect class: a
// synchronous matcher wrapping an async callback makes an assertion
// that cannot fail. See CONTRIBUTING.md ("Accessibility spec linting")
// for what each rule catches and, just as importantly, what it does
// not: this rule set is a partial defence, not a complete one.
import playwright from "eslint-plugin-playwright";

export default [
  {
    files: ["a11y/**/*.spec.mjs"],
    plugins: { playwright },
    rules: {
      // Flags Playwright async matchers/APIs (toBeVisible, expect.poll,
      // test.step, waitFor*) that are not awaited or returned.
      "playwright/missing-playwright-await": "error",
      // Flags a `.then()` chain carrying an expect() that is not itself
      // returned or awaited from the test body.
      "playwright/valid-expect-in-promise": "error",
      // Bans `toThrow`/`not.toThrow` outright. This is the matcher the
      // canonical defect always routes through: it is the only sync
      // matcher whose subject is a function, so it is the one that can
      // swallow an unawaited async callback's work
      // (`expect(async () => {...}).not.toThrow()` "passes" no matter
      // what the callback does). Neither of the two rules above fires
      // on this shape, so this ban is the only mechanism in this config
      // that catches the issue's own canonical example.
      "playwright/no-restricted-matchers": [
        "error",
        {
          toThrow: "Do not assert on whether a callback throws. A synchronous matcher wrapping an async callback cannot fail: it checks whether the CALL threw, not whether the returned promise rejects, so unawaited work inside the callback leaks past teardown and reads as flake. Await the callback directly and assert on its result instead.",
          "not.toThrow": "Do not assert on whether a callback throws. A synchronous matcher wrapping an async callback cannot fail: it checks whether the CALL threw, not whether the returned promise rejects, so unawaited work inside the callback leaks past teardown and reads as flake. Await the callback directly and assert on its result instead.",
        },
      ],
    },
  },
];
