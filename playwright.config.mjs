// Playwright config for the brickwork accessibility + no-JS gate.
// Tests load pre-rendered fixtures (file://), so no web server is needed.
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./a11y",
  testMatch: "**/*.spec.mjs",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? "github" : "list",
  use: { headless: true },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
