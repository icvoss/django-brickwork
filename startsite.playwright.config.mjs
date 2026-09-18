// A dedicated reporter output lets CI prove the startsite gate ran. The main
// a11y config excludes this spec so its aggregate count cannot mask a skipped
// emitted-project scan.
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";
import { defineConfig } from "@playwright/test";

import { assertLocalNodeModules } from "./a11y/assert_node_modules.mjs";

const repoRoot = dirname(fileURLToPath(import.meta.url));
assertLocalNodeModules(repoRoot);

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
