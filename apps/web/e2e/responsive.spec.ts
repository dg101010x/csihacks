import { test, expect, type Page } from "@playwright/test";

const routes = [
  { path: "/", title: "Command Center" },
  { path: "/timeline", title: "Timeline" },
  { path: "/scenario-lab", title: "Scenario Lab" },
  { path: "/interventions", title: "Interventions" },
  { path: "/constitution", title: "Constitution" },
  { path: "/audit", title: "Audit" },
  { path: "/providers", title: "Providers" },
  { path: "/data", title: "Data" },
];

async function expectUsableLayout(page: Page, title: string) {
  await expect(page.getByRole("heading", { name: title, level: 1 })).toBeVisible();
  await expect(page.locator("main")).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1))
    .toBe(true);
}

for (const viewport of [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1440, height: 900 },
]) {
  test.describe(`${viewport.name} layout (${viewport.width}×${viewport.height})`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    for (const route of routes) {
      test(`${route.path} remains usable`, async ({ page }) => {
        const response = await page.goto(route.path);
        expect(response?.status()).toBeLessThan(400);
        await expectUsableLayout(page, route.title);

        if (viewport.name === "mobile") {
          await expect(page.getByRole("button", { name: "Open navigation" })).toBeVisible();
          await expect(page.getByRole("combobox", { name: "Forecast model" })).toBeVisible();
        }
      });
    }
  });
}

test.describe("dark theme", () => {
  for (const route of routes) {
    test(`${route.path} applies the dark surface tokens`, async ({ page }) => {
      await page.goto(route.path);
      await expectUsableLayout(page, route.title);

      const lightBackground = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      await page.evaluate(() => {
        document.documentElement.classList.add("dark");
        document.documentElement.dataset.theme = "dark";
      });
      const darkTheme = await page.evaluate(() => ({
        background: getComputedStyle(document.body).backgroundColor,
        colorScheme: getComputedStyle(document.documentElement).colorScheme,
      }));

      expect(darkTheme.background).not.toBe(lightBackground);
      expect(darkTheme.colorScheme).toBe("dark");
    });
  }
});
