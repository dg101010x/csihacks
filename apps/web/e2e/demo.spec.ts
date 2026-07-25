import { test, expect } from "@playwright/test";

// Section 16.3 demonstration journey / Phase B DoD: the complete baseline
// scenario renders from static fixtures, and the shock control recalculates
// the timeline, Resilience Score, and risk summary.
test.describe("/demo shock simulator", () => {
  test("renders the baseline scenario from fixtures", async ({ page }) => {
    await page.goto("/demo");
    await expect(page.getByText("Baseline — no shock applied")).toBeVisible();
    await expect(page.getByText("82", { exact: true })).toBeVisible();
    await expect(page.getByText("Rent — Meridian Apartments")).toBeVisible();
    await expect(page.getByText("Auto Loan")).toBeVisible();
  });

  test("the shock control recalculates the Resilience Score and risk", async ({ page }) => {
    await page.goto("/demo");
    await expect(page.getByText("82", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Reduce paycheck by $380.00" }).click();

    await expect(page.getByText("Paycheck reduced by $380.00")).toBeVisible();
    await expect(page.getByText("54", { exact: true })).toBeVisible();
    await expect(page.getByText("Rent ($1,450.00) and the auto loan payment", { exact: false })).toBeVisible();

    await page.getByRole("button", { name: "Reset" }).click();
    await expect(page.getByText("Baseline — no shock applied")).toBeVisible();
    await expect(page.getByText("82", { exact: true })).toBeVisible();
  });

  test("the timeline has an accessible table alternative (Section 27)", async ({ page }) => {
    await page.goto("/demo");
    await page.getByRole("button", { name: "View as table" }).click();
    await expect(page.getByRole("table")).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Reserve risk" })).toBeVisible();
  });
});
