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
  await page.goto("/goose");

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
  await expect(page.locator('main a[href="/phish"]').first()).toBeVisible();

  for (const route of ["/goose/performance", "/goose/predictions", "/goose/replay"]) {
    await page.goto(route);
    await expectPrimaryHeadingOrMissingEnv(page);
    await expectSinglePrimaryHeading(page);
  }

  await page.goto("/");
  await page.waitForURL(/\/[a-z0-9_-]+$/);
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

  await page.goto("/goose/replay/2026-01-01");
  await expectPrimaryHeadingOrMissingEnv(page);
});

test("unknown bands and malformed replay dates return 404", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only route check");

  await bootstrapHostedPreviewBypass(page);

  for (const route of ["/not-a-band", "/not-a-band/predictions", "/goose/replay/not-a-date"]) {
    const response = await page.goto(route);
    expect(response?.status(), route).toBe(404);
  }
});

test("legacy URLs permanently redirect to band paths", async ({ request }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only route check");

  const redirects: Array<[string, RegExp]> = [
    ["/?band=phish", /\/phish$/],
    ["/predictions?band=phish", /\/phish\/predictions$/],
    ["/performance?band=phish&k=25&metric=hits", /\/phish\/performance\?k=25&metric=hits$/],
    ["/replay?band=phish&date=2026-01-01", /\/phish\/replay\/2026-01-01$/],
    ["/last-show?band=phish", /\/phish\/replay$/],
    ["/predictions", /\/wsp\/predictions$/],
  ];

  for (const [legacyUrl, expectedLocation] of redirects) {
    const response = await request.get(legacyUrl, { maxRedirects: 0 });
    expect(response.status(), legacyUrl).toBe(308);
    expect(response.headers()["location"], legacyUrl).toMatch(expectedLocation);
  }
});

test("the root redirects to the remembered band, defaulting to WSP", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only route check");

  const first = await request.get("/", { maxRedirects: 0 });
  expect(first.status()).toBe(307);
  expect(first.headers()["location"]).toMatch(/\/wsp$/);
  expect(first.headers()["cache-control"]).toContain("no-store");

  const garbage = await request.get("/", {
    headers: { cookie: "jbn-band=../x" },
    maxRedirects: 0,
  });
  expect(garbage.status()).toBe(307);
  expect(garbage.headers()["location"]).toMatch(/\/wsp$/);

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/phish");
  await expect
    .poll(async () => (await page.context().cookies()).find((c) => c.name === "jbn-band")?.value)
    .toBe("phish");

  const remembered = await page.context().request.get("/", { maxRedirects: 0 });
  expect(remembered.status()).toBe(307);
  expect(remembered.headers()["location"]).toMatch(/\/phish$/);
});

test("the selected band carries across pages",async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only navigation check");

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/goose/predictions");

  const bandLinks = page.locator('main a[href$="/predictions"]');
  // Without a band registry (e.g. missing env locally) there is no picker to use.
  test.skip((await bandLinks.count()) < 2, "band registry unavailable in this environment");

  const otherBand = page
    .locator('main a[href$="/predictions"]:not([aria-current="page"])')
    .first();
  const otherHref = (await otherBand.getAttribute("href")) ?? "";
  const otherSlug = otherHref.split("/")[1];
  await otherBand.click();
  await page.waitForURL(`**/${otherSlug}/predictions`);

  const nav = page.getByRole("navigation", { name: "Primary navigation" });
  await nav.getByRole("link", { name: "Performance" }).click();
  await page.waitForURL(`**/${otherSlug}/performance`);
  await expect(nav.getByRole("link", { name: "Performance" })).toHaveAttribute(
    "aria-current",
    "page",
  );

  await nav.getByRole("link", { name: "Replay" }).click();
  await page.waitForURL(`**/${otherSlug}/replay`);
});

test("performance toggles update the URL without a navigation", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only toggle check");

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/goose/performance");

  const top25 = page.getByRole("button", { name: "Top 25", pressed: false });
  test.skip((await top25.count()) === 0, "performance data unavailable in this environment");

  await top25.click();
  await expect(page.getByRole("button", { name: "Top 25", pressed: true })).toBeVisible();
  await expect(page).toHaveURL(/\/goose\/performance\?k=25$/);

  await page.goto("/goose/performance?k=50&metric=hits");
  await expect(page.getByRole("button", { name: "Top 50", pressed: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Hits", pressed: true })).toBeVisible();
});

test("mobile navigation uses thumb-first ordering", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "mobile-only shell check");

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/goose");

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

test("every active band renders predictions, replay, and performance without query errors", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only band sweep");
  test.setTimeout(180_000);

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/goose");

  // The overview lists every active band as /<slug>.
  const hrefs = await page
    .locator('main a[href^="/"]')
    .evaluateAll((links) => links.map((link) => link.getAttribute("href") ?? ""));
  const bandSlugs = [
    ...new Set(hrefs.filter((href) => /^\/[a-z0-9_-]+$/.test(href)).map((href) => href.slice(1))),
  ].filter((slug) => !["about", "contact", "data-use"].includes(slug));

  // No bands means the registry could not load (e.g. missing env locally).
  test.skip(bandSlugs.length === 0, "band registry unavailable in this environment");

  for (const band of bandSlugs) {
    for (const route of ["predictions", "performance", "replay"]) {
      await page.goto(`/${encodeURIComponent(band)}/${route}`);
      await expectPrimaryHeadingOrMissingEnv(page);

      const failures = page.getByRole("heading", { name: /query failed/i });
      await expect(failures, `${band}/${route}`).toHaveCount(0);
    }

    await page.goto(`/${encodeURIComponent(band)}/replay`);
    // Setlist rows render as table rows; the header row is not a song.
    await expect(
      page.locator("main table tbody tr").first(),
      `${band} replay shows at least one song`,
    ).toBeVisible();
  }
});

test("band pills share one row on the desktop predictions page", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "desktop-only layout check");

  await bootstrapHostedPreviewBypass(page);
  await page.goto("/wsp/predictions");

  const pills = page.getByRole("navigation", { name: "Band" }).getByRole("link");
  test.skip((await pills.count()) < 2, "band registry unavailable in this environment");

  const tops = await pills.evaluateAll((links) =>
    links.map((link) => Math.round(link.getBoundingClientRect().top)),
  );
  expect(new Set(tops).size, `pill tops: ${tops.join(",")}`).toBe(1);
});
