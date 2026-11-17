import { expect, test as base, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { getHostedAuthHeaders, normalizeHostedBaseUrl, validateHostedAuthResponse, validateHostedRedirect } from "./hosted-target";

export const hostedBaseUrl = normalizeHostedBaseUrl(process.env.SMOKE_BASE_URL);
const unavailableHeading = /Supabase environment required|Band registry unavailable|query failed|^No (predictions|accuracy rows|replay history|replay dates|prediction snapshot) available$/i;

export async function expectHealthyHostedPage(page: Page) {
  if (!hostedBaseUrl) return;
  await expect(page.getByRole("heading", { name: unavailableHeading })).toHaveCount(0);
}

// Wait for streamed data or an explicit data-state message before deciding whether
// a local run can skip. Hosted runs must always reach the real data selector.
export async function requireData(page: Page, locator: Locator, reason: string, minimum = 1) {
  if (!hostedBaseUrl) {
    await expect(locator.first().or(page.getByRole("heading", { name: unavailableHeading })).first()).toBeVisible();
    test.skip((await locator.count()) < minimum, reason);
  }
  await expect.poll(() => locator.count(), { message: reason }).toBeGreaterThanOrEqual(minimum);
  await expect(locator.first()).toBeVisible();
  await expectHealthyHostedPage(page);
}

const authHeaders = getHostedAuthHeaders(
  hostedBaseUrl,
  process.env.VERCEL_PROTECTION_BYPASS_TOKEN,
  process.env.VERCEL_OIDC_TOKEN,
);
const usesOidc = Boolean(authHeaders?.["x-vercel-trusted-oidc-idp-token"]);

export const test = base.extend({
  context: async ({ context }, runTest) => {
    if (hostedBaseUrl && authHeaders && usesOidc) {
      // OIDC authenticates each request; unlike bypass secrets it does not issue
      // a cookie. Fetch without following redirects so no header crosses origins.
      await context.route("**/*", async (route) => {
        if (new URL(route.request().url()).origin !== hostedBaseUrl) {
          await route.continue();
          return;
        }
        let response;
        try {
          response = await route.fetch({
            headers: { ...route.request().headers(), ...authHeaders },
            maxRedirects: 0,
          });
        } catch {
          throw new Error("Origin-scoped preview browser request failed.");
        }
        validateHostedRedirect(hostedBaseUrl, response.headers().location);
        await route.fulfill({ response });
      });
    } else if (hostedBaseUrl && authHeaders) {
      // Bypass secrets support one bootstrap request and an origin-scoped cookie.
      let response;
      try {
        response = await context.request.get(hostedBaseUrl, { headers: authHeaders, maxRedirects: 0 });
      } catch {
        // Playwright request errors can include headers; never log credentials.
        throw new Error("Preview authentication request failed before navigation.");
      }
      validateHostedAuthResponse(hostedBaseUrl, response.status(), response.headers().location);
      const cookies = await context.cookies(hostedBaseUrl);
      const hostname = new URL(hostedBaseUrl).hostname;
      if (!cookies.length || cookies.some((cookie) => cookie.domain.replace(/^\./, "") !== hostname)) {
        throw new Error("Preview authentication did not establish an origin-scoped cookie.");
      }
      await context.clearCookies();
      await context.addCookies(cookies.map(({ name, value, expires, httpOnly, secure, sameSite }) => ({
        name, value, expires, httpOnly, secure, sameSite, url: hostedBaseUrl,
      })));
    }
    await runTest(context);
  },
  request: async ({ context }, runTest) => {
    if (!hostedBaseUrl || !authHeaders || !usesOidc) {
      await runTest(context.request);
      return;
    }
    // Route handlers do not intercept APIRequestContext. Current smoke API
    // assertions use GET only; keep the same cookie jar and scope each GET too.
    const request = new Proxy(context.request, {
      get(target, key) {
        if (key === "get") {
          const get: APIRequestContext["get"] = async (url, options = {}) => {
            const targetUrl = new URL(url, hostedBaseUrl);
            if (targetUrl.origin !== hostedBaseUrl) {
              throw new Error("Preview API request is outside the configured origin.");
            }
            let response;
            try {
              response = await target.get(targetUrl.toString(), {
                ...options,
                headers: { ...options.headers, ...authHeaders },
                maxRedirects: 0,
              });
            } catch {
              throw new Error("Origin-scoped preview API request failed.");
            }
            validateHostedRedirect(hostedBaseUrl, response.headers().location);
            return response;
          };
          return get;
        }
        const value = Reflect.get(target, key);
        return typeof value === "function" ? value.bind(target) : value;
      },
    });
    await runTest(request);
  },
  page: async ({ page }, runTest) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("response", (response) => {
      if (hostedBaseUrl && response.request().isNavigationRequest() &&
          new URL(response.url()).origin === hostedBaseUrl && response.status() >= 500) {
        errors.push(`Page returned HTTP ${response.status()}`);
      }
    });
    await runTest(page);
    if (hostedBaseUrl) {
      await expectHealthyHostedPage(page);
      expect(errors, "Hosted pages must render without runtime errors").toEqual([]);
    }
  },
});

export { expect };
