import type { Page } from "@playwright/test";
import { expect, test, requireData, expectHealthyHostedPage } from "./fixtures";

async function expectMainHeadingOrDataFallback(page: Page) {
  await expect(
    page
      .locator("main h1")
      .or(page.getByRole("heading", { name: "Supabase environment required" }))
      .or(page.locator("main h2"))
      .first(),
  ).toBeVisible();
  await expectHealthyHostedPage(page);
}

test.describe("mobile flows", () => {
  test("bottom nav renders expected items", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

      await page.goto("/goose");

    const mobileNav = page.getByRole("navigation", { name: "Mobile navigation" });
    await expect(mobileNav).toBeVisible();

    const labels = await mobileNav.getByRole("link").locator("span:last-child").allTextContents();
    expect(labels).toEqual(["Home", "Predictions", "Performance", "Replay"]);
    expect(labels).not.toContain("Compare");
  });

  test("mobile top controls use compact dropdown selectors", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

      await page.goto("/goose/predictions");

    const bandSelect = page.getByRole("combobox", { name: "Band" });
    await requireData(page, bandSelect, "mobile band selector requires the registry");

    await expect(bandSelect).toBeVisible();
    await expect(bandSelect).toHaveValue("/goose/predictions");

    const bandBox = await bandSelect.boundingBox();
    expect(bandBox).not.toBeNull();
    expect(bandBox!.height).toBeGreaterThanOrEqual(44);
  });

  test("overview band switcher is visible in the first viewport", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

      await page.goto("/goose");

    const switcher = page.getByRole("navigation", { name: "Band" });
    await requireData(page, switcher, "overview band switcher requires the registry");

    const current = switcher.getByRole("link", { name: "Goose" });
    await expect(current).toBeInViewport();
    await expect(current).toHaveAttribute("aria-current", "page");
    const box = await current.boundingBox();
    expect(box!.height).toBeGreaterThanOrEqual(44);

    const phish = switcher.getByRole("link", { name: "Phish" });
    await expect(phish).toBeInViewport();
    await phish.click();
    await expect(page).toHaveURL(/\/phish$/);
  });

  test("switching band keeps the current page", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

      await page.goto("/goose/predictions");

    const bandSelect = page.getByRole("combobox", { name: "Band" });
    await requireData(page, bandSelect, "mobile band selector requires the registry");

    await expect(bandSelect).toBeInViewport();
    await bandSelect.selectOption("/phish/predictions");
    await expect(page).toHaveURL(/\/phish\/predictions$/);
  });

  test("key mobile flows render without page crashes", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    const pageErrors: string[] = [];
    page.on("pageerror", (error) => {
      pageErrors.push(error.message);
    });

    const routes = [
      "/",
      "/goose",
      "/goose/predictions",
      "/goose/performance",
      "/goose/replay",
      "/about",
      "/contact",
      "/data-use",
    ];
    for (const route of routes) {
      await page.goto(route);
      await expectMainHeadingOrDataFallback(page);
    }

    expect(pageErrors).toHaveLength(0);
  });

  test("internal table preview is hidden outside development", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

      const response = await page.goto("/preview/tables");

    expect(response?.status()).toBe(404);
  });
});
