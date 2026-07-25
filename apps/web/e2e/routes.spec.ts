import { test, expect } from "@playwright/test";

// Section 17 route inventory smoke test — real journey coverage (Section 87
// end-to-end tests) lands with the corresponding phase (B-E).
const routes = [
  "/",
  "/timeline",
  "/scenario-lab",
  "/interventions",
  "/constitution",
  "/audit",
  "/providers",
  "/data",
];

for (const route of routes) {
  test(`${route} renders without error`, async ({ page }) => {
    const response = await page.goto(route);
    expect(response?.status()).toBeLessThan(400);
    await expect(page.locator("main")).toBeVisible();
  });
}
