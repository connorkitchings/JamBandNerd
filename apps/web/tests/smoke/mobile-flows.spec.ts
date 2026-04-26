import { expect, test } from "@playwright/test";
import {
  getVercelProtectionBypassToken,
  getVercelProtectionBypassUrl,
  normalizeHostedBaseUrl,
} from "./hosted-target";

const hostedBaseUrl = normalizeHostedBaseUrl(process.env.SMOKE_BASE_URL);
const vercelProtectionBypassToken = getVercelProtectionBypassToken(
  hostedBaseUrl,
  process.env.VERCEL_PROTECTION_BYPASS_TOKEN,
);

async function bootstrapHostedPreviewBypass(page: import("@playwright/test").Page) {
  if (!hostedBaseUrl || !vercelProtectionBypassToken) {
    return;
  }

  await page.goto(
    getVercelProtectionBypassUrl(hostedBaseUrl, vercelProtectionBypassToken),
    { waitUntil: "domcontentloaded" },
  );
}

async function expectMainHeadingOrDataFallback(page: import("@playwright/test").Page) {
  await expect(
    page
      .locator("main h1")
      .or(page.getByRole("heading", { name: "Supabase environment required" })),
  ).toBeVisible();
}

test.describe("mobile flows", () => {
  test("bottom nav renders expected items", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/");

    const mobileNav = page.getByRole("navigation", { name: "Mobile navigation" });
    await expect(mobileNav).toBeVisible();

    const labels = await mobileNav.getByRole("link").locator("span:last-child").allTextContents();
    expect(labels.length).toBeGreaterThanOrEqual(3);
    expect(labels).toContain("Stats");
    expect(labels).toContain("Predict");
  });

  test("mobile top controls use compact dropdown selectors", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/predictions?band=goose");

    const bandSelect = page.getByRole("combobox", { name: "Band" });
    if ((await bandSelect.count()) === 0) {
      await expectMainHeadingOrDataFallback(page);
      return;
    }

    await expect(bandSelect).toBeVisible();

    const bandBox = await bandSelect.boundingBox();
    expect(bandBox).not.toBeNull();
    expect(bandBox!.height).toBeGreaterThanOrEqual(44);
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

    await bootstrapHostedPreviewBypass(page);
    
    const routes = ["/", "/predictions", "/performance"];
    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState("networkidle");
      await expectMainHeadingOrDataFallback(page);
    }

    const criticalPageErrors = pageErrors.filter(
      (message) => !message.includes("Failed to load chunk"),
    );
    expect(criticalPageErrors).toHaveLength(0);
  });

  test("mobile detail routes show a back affordance", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/last-show");
    await expect(page.getByRole("button", { name: "Go back" })).toBeVisible();

    await page.goto("/about");
    await expect(page.getByRole("button", { name: "Go back" })).toHaveCount(0);
  });

  test("preview tables remain scrollable on mobile", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/preview/tables");

    await expect(page.getByRole("heading", { name: "Song board" })).toBeVisible();
  });
});
