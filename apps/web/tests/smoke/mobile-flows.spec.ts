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
    expect(labels).toEqual(["Home", "Compare", "Stats", "Replay", "Predict"]);
  });

  test("replay rail scrolls horizontally on mobile", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/replay?band=goose");

    const rail = page.locator(".overflow-x-auto").first();
    await expect(rail).toBeVisible();
    
    const isScrollable = await rail.evaluate((el) => {
      return el.scrollWidth > el.clientWidth;
    });
    
    expect(isScrollable).toBe(true);
  });

  test("filter pills have adequate touch targets", async ({ page }, testInfo) => {
    test.skip(
      testInfo.project.name !== "mobile-chromium",
      "mobile-only test",
    );

    await bootstrapHostedPreviewBypass(page);
    await page.goto("/predictions?band=goose");

    const filterPill = page.getByRole("link", { name: /goose/i }).first();
    await expect(filterPill).toBeVisible();

    const box = await filterPill.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
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
      (e) => !e.includes("hydration") && !e.includes("warning"),
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
