// Playwright config for the brickwork accessibility + no-JS gate.
// Tests load pre-rendered fixtures (file://), so no web server is needed.
import { defineConfig } from "@playwright/test";

// The json reporter always runs alongside the human-readable one, writing to
// a fixed path (gitignored, see .gitignore): icvoss/django-brickwork#382's
// non-zero-tests-ran guard reads this file's stats after the run rather than
// grepping console text, since only the reporter's own counts distinguish
// "found files, ran zero tests" from a run that genuinely passed.
export default defineConfig({
  testDir: "./a11y",
  testMatch: "**/*.spec.mjs",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [
    [process.env.CI ? "github" : "list"],
    ["json", { outputFile: "a11y-results.json" }],
  ],
  use: { headless: true },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
