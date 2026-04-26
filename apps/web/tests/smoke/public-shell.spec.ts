import { expect, test, type Page } from "@playwright/test";
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

async function bootstrapHostedPreviewBypass(page: Page) {
  if (!hostedBaseUrl || !vercelProtectionBypassToken) {
    return;
  }

  await page.goto(
    getVercelProtectionBypassUrl(hostedBaseUrl, vercelProtectionBypassToken),
    { waitUntil: "domcontentloaded" },
  );
}

async function expectPrimaryHeadingOrMissingEnv(page: Page) {
  await expect(
    page
      .locator("main h1")
      .or(page.getByRole("heading", { name: "Supabase environment required" })),
  ).toBeVisible();
}

test("desktop routes render the public shell", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only shell check");

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/");

  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Predictions" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Performance" })).toBeVisible();
  await expect(page.locator("main h1")).toBeVisible();

  await page.goto("/performance");
  await expectPrimaryHeadingOrMissingEnv(page);

  await page.goto("/predictions");
  await expectPrimaryHeadingOrMissingEnv(page);

  await page.goto("/?band=goose");
  await page.waitForURL(/\/predictions\?band=goose$/);
  await expectPrimaryHeadingOrMissingEnv(page);

  await page.goto("/about");
  await expect(page.getByRole("heading", { name: "About JamBandNerd" })).toBeVisible();

  await page.goto("/data-use");
  await expect(page.getByRole("heading", { name: "Data Use" })).toBeVisible();

  await page.goto("/admin/setlist");
  await expect(
    page
      .getByRole("heading", { name: "Admin Access" })
      .or(page.getByRole("heading", { name: "Admin Unavailable" }))
      .or(page.getByRole("heading", { name: "Add Setlist" })),
  ).toBeVisible();
});

test("mobile navigation uses thumb-first ordering", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile-only shell check");

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/");

  const mobileNav = page.getByRole("navigation", { name: "Mobile navigation" });
  await expect(mobileNav).toBeVisible();

  const labels = await mobileNav.getByRole("link").locator("span:last-child").allTextContents();
  expect(labels.length).toBeGreaterThanOrEqual(3);
  expect(labels).toContain("Stats");
  expect(labels).toContain("Predict");
});

test("mobile detail routes show a back affordance", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile-only detail check");

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/last-show");
  await expect(page.getByRole("button", { name: "Go back" })).toBeVisible();

  await page.goto("/about");
  await expect(page.getByRole("button", { name: "Go back" })).toHaveCount(0);
});

test("preview tables remain scrollable on mobile", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile-only table check");

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/preview/tables");

  await expect(page.getByRole("heading", { name: "Song board" })).toBeVisible();
});
