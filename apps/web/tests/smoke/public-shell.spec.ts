import { expect, test } from "@playwright/test";

test("desktop routes render the public shell", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only shell check");

  await page.goto("/");

  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Predictions" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Performance" })).toBeVisible();

  await page.goto("/performance");
  await expect(page.getByRole("heading", { name: "Historical Performance" })).toBeVisible();

  await page.goto("/explorer");
  await expect(page.getByRole("heading", { name: "Historical Explorer" })).toBeVisible();

  await page.goto("/compare");
  await expect(page.getByRole("heading", { name: "Model Compare" })).toBeVisible();

  // /predictions now redirects to /
  await page.goto("/predictions");
  await expect(page.getByRole("heading", { name: "Song Board" })).toBeVisible();

  await page.goto("/about");
  await expect(page.getByRole("heading", { name: "About JamBandNerd" })).toBeVisible();
});

test("mobile navigation uses thumb-first ordering", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile-only shell check");

  await page.goto("/");

  const mobileNav = page.getByRole("navigation", { name: "Mobile navigation" });
  await expect(mobileNav).toBeVisible();

  const labels = await mobileNav.getByRole("link").locator("span:last-child").allTextContents();
  expect(labels).toEqual(["Explore", "Stats", "Predict", "Last Show", "About"]);
});

test("mobile detail routes show a back affordance", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile-only detail check");

  await page.goto("/last-show");
  await expect(page.getByRole("button", { name: "Go back" })).toBeVisible();

  await page.goto("/about");
  await expect(page.getByRole("button", { name: "Go back" })).toHaveCount(0);
});

test("preview tables remain scrollable on mobile", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile-only table check");

  await page.goto("/preview/tables");

  // The song board renders inside the preview page
  await expect(page.getByRole("heading", { name: "Song board" })).toBeVisible();
});

