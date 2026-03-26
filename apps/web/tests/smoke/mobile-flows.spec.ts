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
    expect(labels).toEqual(["Home", "Stats", "Predict", "Compare", "Replay"]);
  });

  test("replay comparison cards render on mobile", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/replay?band=goose");

    const cards = page.getByTestId("replay-comparison-cards");
    await expect(cards).toBeVisible();
    await expect(cards.locator("article").first()).toBeVisible();
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
    await expect(bandSelect).toBeVisible();
    await expect(modelSelect).toBeVisible();

    const bandBox = await bandSelect.boundingBox();
    const modelBox = await modelSelect.boundingBox();
    expect(bandBox).not.toBeNull();
    expect(modelBox).not.toBeNull();
    expect(bandBox!.height).toBeGreaterThanOrEqual(44);
    expect(modelBox!.height).toBeGreaterThanOrEqual(44);
  });

  test("compare page stacks on narrow viewport", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/compare?band=goose");

    const summaryCards = page.locator("section.grid");
    await expect(summaryCards).toBeVisible();
    
    const cards = summaryCards.locator("> div");
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test("no console errors on key flows", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    await bootstrapHostedPreviewBypass(page);
    
    const routes = ["/", "/predictions", "/performance", "/compare", "/replay"];
    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState("networkidle");
    }

    const criticalErrors = errors.filter(
      (e) =>
        !e.includes("hydration") &&
        !e.includes("warning") &&
        !e.includes("status of 404"),
    );
    expect(criticalErrors).toHaveLength(0);
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
