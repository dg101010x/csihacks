import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // The demo API intentionally exposes one shared Sarah scenario. Keep
  // browser journeys serial so a shock/reset in one test cannot corrupt
  // another test's baseline assertions.
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3400",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npx next dev --port 3400",
    url: "http://localhost:3400",
    reuseExistingServer: !process.env.CI,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
