import { test, expect } from "@playwright/test";

test.describe("Relief demonstration journey", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(async ({ request }) => {
    const response = await request.post("/v1/demo/reset");
    expect(response.ok()).toBe(true);
  });

  test("renders the baseline command center", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
    await expect(page.getByText("Available balance")).toBeVisible();
    await expect(page.getByText("$2,480.00")).toBeVisible();
    await expect(page.getByText("Rent — Meridian Apartments", { exact: false })).toBeVisible();
  });

  test("applies the paycheck scenario and produces recommendations", async ({ page }) => {
    await page.goto("/scenario-lab");
    await page.getByRole("button", { name: "Apply scenario" }).click();

    await expect(page.getByRole("heading", { name: "Baseline vs. simulated" })).toBeVisible();
    await expect(page.getByText("A scenario is currently applied to the live forecast.")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recommended interventions" })).toBeVisible();

    await page.getByRole("button", { name: "Reset to baseline" }).click();
    await expect(page.getByRole("button", { name: "Apply scenario" })).toBeEnabled();
  });

  test("the forecast has an accessible table alternative", async ({ page }) => {
    await page.goto("/timeline");
    await page.getByRole("button", { name: "View as table" }).click();
    await expect(page.getByRole("table")).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Reserve risk" })).toBeVisible();
  });
});
