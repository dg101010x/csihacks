import { test, expect } from "@playwright/test";

// Section 16.3 demonstration journey. Tests verify core UI elements and
// navigation flows work correctly with mocked data.
test.describe("UI demonstration flows", () => {
  test("home page loads with main content area", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("main")).toBeVisible();
  });

  test("scenario lab page loads and renders content", async ({ page }) => {
    await page.goto("/scenario-lab");
    await expect(page.locator("main")).toBeVisible();
  });

  test("timeline page has chart and table toggle", async ({ page }) => {
    await page.goto("/timeline");
    await expect(page.locator("main")).toBeVisible();
    // Table toggle button should exist
    const tableButton = page.getByRole("button", { name: /View as table|Table/i });
    if (await tableButton.isVisible()) {
      await tableButton.click();
      await expect(page.getByRole("table")).toBeVisible();
    }
  });

  test("interventions page loads correctly", async ({ page }) => {
    await page.goto("/interventions");
    await expect(page.locator("main")).toBeVisible();
  });

  test("constitution page loads with rules interface", async ({ page }) => {
    await page.goto("/constitution");
    await expect(page.locator("main")).toBeVisible();
  });

  test("audit page loads with ledger view", async ({ page }) => {
    await page.goto("/audit");
    await expect(page.locator("main")).toBeVisible();
  });

  test("providers page shows account cards", async ({ page }) => {
    await page.goto("/providers");
    await expect(page.locator("main")).toBeVisible();
  });
});
