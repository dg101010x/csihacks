import { test, expect } from "@playwright/test";

test.describe("Interactive demo functions", () => {
  test.beforeEach(async ({ request }) => {
    const response = await request.post("/v1/demo/reset");
    expect(response.ok()).toBe(true);
  });

  test("shell navigation, model selection, notifications, and table controls work", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: /Search or jump/ }).click();
    const palette = page.getByRole("textbox", { name: "Command palette search" });
    await palette.fill("timeline");
    await palette.press("Enter");
    await expect(page).toHaveURL(/\/timeline$/);

    const model = page.getByRole("combobox", { name: "Forecast model" });
    await model.selectOption("mini");
    await expect(model).toHaveValue("mini");
    await expect(page.getByText("Forecast confidence 100%")).toBeVisible();

    await page.getByRole("button", { name: "7d" }).click();
    await expect(page.getByRole("button", { name: "7d" })).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: "View as table" }).click();
    await expect(page.getByRole("table", { name: /Daily balance forecast/ })).toBeVisible();

    await page.getByRole("button", { name: /^Notifications/ }).click();
    await expect(page.getByText("Nothing needs your attention.")).toBeVisible();
  });

  test("Constitution starter parses and activates with the intended scope", async ({ page }) => {
    await page.goto("/constitution");
    await page.getByRole("button", { name: /You may pause subscriptions/ }).click();

    // CardTitle -> CardHeader (1) -> Card (2): the dl with Scope/Trigger/etc.
    // lives in a sibling CardContent, not inside CardHeader.
    const interpretation = page.getByRole("heading", { name: "Structured interpretation" }).locator("..").locator("..");
    await expect(interpretation.getByText("subscriptions", { exact: true })).toBeVisible();
    await expect(interpretation.getByText("transportation", { exact: true })).toHaveCount(0);
    await expect(interpretation.getByText("none", { exact: true })).toBeVisible();

    await page.getByRole("checkbox", { name: /reviewed this interpretation/ }).check();
    await page.getByRole("button", { name: "Activate rule" }).click();
    await expect(page.getByText(/Scope: subscriptions · Approval: none/)).toBeVisible();
  });

  test("scenario, intervention approval, provider response, and audit evidence complete", async ({ page }) => {
    await page.goto("/scenario-lab");
    await page.getByRole("button", { name: "Apply scenario" }).click();
    await page.getByRole("link", { name: "View recommended interventions" }).click();

    await page.getByRole("button", { name: "Compare top 3" }).click();
    await expect(page.getByRole("heading", { name: "Comparing the top 3" })).toBeVisible();
    await page.getByRole("button", { name: "Review this package" }).first().click();
    await page.getByRole("checkbox", { name: /I understand the actions/ }).check();
    await page.getByRole("button", { name: "Submit for approval" }).click();
    await page.getByRole("button", { name: "Simulate provider response" }).click();
    await expect(page.getByText("Executed (simulated)")).toBeVisible();
    await page.getByRole("button", { name: "Done" }).click();

    await page.goto("/audit");
    await expect(page.getByText(/records$/)).not.toHaveText("0 of 0 records");
    await page.getByRole("button", { name: "View details for provider case approved" }).first().click();
    await expect(page.getByRole("dialog", { name: "provider case approved" })).toBeVisible();
  });

  test("provider technical details disclose synchronized Plaid status", async ({ page }) => {
    await page.goto("/providers");

    // CardTitle -> div.flex-1 (1) -> CardHeader (2) -> Card (3): the
    // "Technical details" button lives in a sibling CardContent.
    const plaidCard = page.getByRole("heading", { name: "Plaid Sandbox" }).locator("..").locator("..").locator("..");
    await plaidCard.getByRole("button", { name: "Technical details" }).click();
    await expect(plaidCard.getByText("Accounts available")).toBeVisible();
  });
});
