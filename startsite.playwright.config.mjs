// A dedicated reporter output lets CI prove the startsite gate ran. The main
// a11y config excludes this spec so its aggregate count cannot mask a skipped
// emitted-project scan.
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./a11y",
  testMatch: "startsite.spec.mjs",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [
    [process.env.CI ? "github" : "list"],
    ["json", { outputFile: "a11y-startsite-results.json" }],
  ],
  use: { headless: true },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
