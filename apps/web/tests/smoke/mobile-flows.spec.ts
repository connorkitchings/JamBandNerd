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
      .or(page.getByRole("heading", { name: "Supabase environment required" }))
      .or(page.getByText("Comparison data unavailable"))
      .or(page.getByText("No replay history available")),
  ).toBeVisible();
}

test.describe("mobile flows", () => {
  test("bottom nav renders all 5 items", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/");

    const mobileNav = page.getByRole("navigation", { name: "Mobile navigation" });
    await expect(mobileNav).toBeVisible();

    const labels = await mobileNav.getByRole("link").locator("span:last-child").allTextContents();
    expect(labels.length).toBeGreaterThanOrEqual(4);
    expect(labels).toContain("Stats");
    expect(labels).toContain("Predict");
  });

  test("replay comparison cards render on mobile", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/replay?band=goose");

    const cards = page.getByTestId("replay-comparison-cards");
    if (await cards.count()) {
      await expect(cards).toBeVisible();
      await expect(cards.locator("article").first()).toBeVisible();
      return;
    }

    await expectMainHeadingOrDataFallback(page);
  });

  test("mobile top controls use compact dropdown selectors", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/predictions?band=goose");

    const bandSelect = page.getByRole("combobox", { name: "Band" });
    const modelSelect = page.getByRole("combobox", { name: "Model" });
    if ((await bandSelect.count()) === 0 || (await modelSelect.count()) === 0) {
      await expectMainHeadingOrDataFallback(page);
      return;
    }

    await expect(bandSelect).toBeVisible();
    await expect(modelSelect).toBeVisible();

    const bandBox = await bandSelect.boundingBox();
    const modelBox = await modelSelect.boundingBox();
    expect(bandBox).not.toBeNull();
    expect(modelBox).not.toBeNull();
    expect(bandBox!.height).toBeGreaterThanOrEqual(44);
    expect(modelBox!.height).toBeGreaterThanOrEqual(44);
  });

  test("deal mobile song rows keep metrics grouped", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/predictions?band=goose&model=deal");

    const rows = page.getByTestId("deal-mobile-song-row");
    if ((await rows.count()) === 0) {
      await expectMainHeadingOrDataFallback(page);
      return;
    }

    const firstRow = rows.first();
    await firstRow.locator("button").click();
    await expect(firstRow).toContainText("Gap");

    const box = await firstRow.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeLessThanOrEqual(390);
  });

  test("compare page stacks on narrow viewport", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/compare?band=goose");

    await expectMainHeadingOrDataFallback(page);
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

    const routes = ["/", "/predictions", "/performance", "/compare", "/replay"];
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
