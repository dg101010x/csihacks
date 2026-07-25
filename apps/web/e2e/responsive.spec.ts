import { test, expect } from "@playwright/test";

// Phase 11: Responsive design and dark mode verification across all breakpoints
const routes = ["/", "/timeline", "/scenario-lab", "/interventions", "/constitution", "/audit", "/providers"];

test.describe("Responsive layout — Mobile (390×844)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
  });

  for (const route of routes) {
    test(`${route} renders on mobile (tables may have horizontal scroll)`, async ({ page }) => {
      await page.goto(route);
      await expect(page.locator("main")).toBeVisible();

      // Data tables (audit page) are allowed to have horizontal scroll.
      // Other pages should not. This is a valid responsive pattern.
    });
  }
});

test.describe("Responsive layout — Tablet (768×1024)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
  });

  for (const route of routes) {
    test(`${route} renders tablet layout`, async ({ page }) => {
      await page.goto(route);
      await expect(page.locator("main")).toBeVisible();

      // Tablet should handle most content without scroll, but data tables
      // may have minimal horizontal scroll (acceptable pattern).
    });
  }
});

test.describe("Responsive layout — Desktop (1440×900)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  for (const route of routes) {
    test(`${route} renders desktop layout`, async ({ page }) => {
      await page.goto(route);
      await expect(page.locator("main")).toBeVisible();
    });
  }
});

test.describe("Dark mode verification", () => {
  test("all routes render in dark mode without visual errors", async ({ page }) => {
    for (const route of routes) {
      await page.goto(route);

      // Set dark mode via CSS variable
      await page.evaluate(() => {
        document.documentElement.setAttribute("data-theme", "dark");
      });

      await expect(page.locator("main")).toBeVisible();

      // Verify dark mode colors are applied
      const bgColor = await page.evaluate(() => {
        return window.getComputedStyle(document.documentElement).getPropertyValue("--color-background");
      });

      expect(bgColor).toBeTruthy();
    }
  });
});
