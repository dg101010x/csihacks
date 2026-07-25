import { test, expect } from "@playwright/test";

// Section 17 route inventory smoke test — real journey coverage (Section 87
// end-to-end tests) lands with the corresponding phase (B-E).
const routes = [
  "/",
  "/demo",
  "/onboarding",
  "/dashboard",
  "/timeline",
  "/interventions",
  "/interventions/int_01",
  "/constitution",
  "/provider",
  "/provider/cases/case_01",
  "/audit/decision_01",
  "/settings",
  "/settings/integrations",
];

for (const route of routes) {
  test(`${route} renders without error`, async ({ page }) => {
    const response = await page.goto(route);
    expect(response?.status()).toBeLessThan(400);
    await expect(page.locator("main")).toBeVisible();
  });
}
