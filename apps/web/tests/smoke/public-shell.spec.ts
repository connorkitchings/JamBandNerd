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
      .or(page.getByRole("heading", { name: "Supabase environment required" }))
      .or(page.locator("main h2"))
      .first(),
  ).toBeVisible();
}

async function expectSinglePrimaryHeading(page: Page) {
  await expect(page.locator("main h1")).toHaveCount(1);
}

test("desktop routes render the public shell", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only shell check");

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/");

  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Predictions" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Performance" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Replay" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "What are they playing next?" })).toBeVisible();
  await expectSinglePrimaryHeading(page);
  await expect(
    page
      .getByRole("heading", { name: "First Look" })
      .or(page.getByRole("heading", { name: "Band registry unavailable" }))
      .first(),
  ).toBeVisible();
  await expect(page.locator('main a[href="/?teaser=phish"]')).toBeVisible();

  const bandPredictionLinks = page.locator('main a[href^="/predictions?band="]');
  if ((await bandPredictionLinks.count()) > 0) {
    await expect(bandPredictionLinks.first()).toHaveAttribute("href", /\/predictions\?band=/);
  }

  await page.goto("/performance");
  await expectPrimaryHeadingOrMissingEnv(page);
  await expectSinglePrimaryHeading(page);

  await page.goto("/predictions");
  await expectPrimaryHeadingOrMissingEnv(page);
  await expectSinglePrimaryHeading(page);

  await page.goto("/replay");
  await expectPrimaryHeadingOrMissingEnv(page);
  await expectSinglePrimaryHeading(page);

  await page.goto("/?band=goose");
  await page.waitForURL(/\/predictions\?band=goose$/);
  await expectPrimaryHeadingOrMissingEnv(page);
  await expectSinglePrimaryHeading(page);

  await page.goto("/about");
  await expect(page.getByRole("heading", { name: "About JamBandNerd" })).toBeVisible();
  await expectSinglePrimaryHeading(page);

  await page.goto("/data-use");
  await expect(page.getByRole("heading", { name: "Data Use" })).toBeVisible();
  await expectSinglePrimaryHeading(page);

  await page.goto("/contact");
  await expect(page.getByRole("heading", { name: "Contact JamBandNerd" })).toBeVisible();
  await expectSinglePrimaryHeading(page);
});

test("removed multi-model routes are unavailable", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only route check");

  await bootstrapHostedPreviewBypass(page);

  for (const route of ["/compare", "/explorer"]) {
    const response = await page.goto(route);
    expect(response?.status()).toBe(404);
  }

  await page.goto("/replay?band=goose&date=2026-01-01");
  await expectPrimaryHeadingOrMissingEnv(page);
});

test("mobile navigation uses thumb-first ordering", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile-only shell check");

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/");

  const mobileNav = page.getByRole("navigation", { name: "Mobile navigation" });
  await expect(mobileNav).toBeVisible();

  const labels = await mobileNav.getByRole("link").locator("span:last-child").allTextContents();
  expect(labels).toEqual(["Home", "Predictions", "Performance", "Replay"]);
  expect(labels).not.toContain("Compare");
});



test("internal table preview is hidden outside development", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile-only table check");

  await bootstrapHostedPreviewBypass(page);
  const response = await page.goto("/preview/tables");

  expect(response?.status()).toBe(404);
});

test("every active band renders predictions, last show, and replay without query errors", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only band sweep");
  test.setTimeout(180_000);

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/");

  // The home page lists every active band as /predictions?band=<slug>.
  const hrefs = await page
    .locator('a[href^="/predictions?band="]')
    .evaluateAll((links) => links.map((link) => link.getAttribute("href") ?? ""));
  const bandSlugs = [
    ...new Set(
      hrefs.map((href) => new URL(href, "http://x").searchParams.get("band") ?? ""),
    ),
  ].filter(Boolean);

  // No bands means the registry could not load (e.g. missing env locally).
  test.skip(bandSlugs.length === 0, "band registry unavailable in this environment");

  for (const band of bandSlugs) {
    for (const route of ["/predictions", "/last-show", "/replay"]) {
      await page.goto(`${route}?band=${encodeURIComponent(band)}`);
      await expectPrimaryHeadingOrMissingEnv(page);

      const failures = page
        .getByRole("heading", { name: /query failed/i })
        .or(page.getByRole("heading", { name: "Band not found" }));
      await expect(failures, `${band}${route}`).toHaveCount(0);
    }

    await page.goto(`/last-show?band=${encodeURIComponent(band)}`);
    // Setlist rows render as table rows; the header row is not a song.
    await expect(
      page.locator("main table tbody tr").first(),
      `${band} /last-show shows at least one song`,
    ).toBeVisible();
  }
});
