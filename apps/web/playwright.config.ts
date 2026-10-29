import { defineConfig, devices } from "@playwright/test";
import { SERVER_LOG_PATH } from "./tests/smoke/assert-no-query-errors";
import { normalizeHostedBaseUrl } from "./tests/smoke/hosted-target";

const PORT = 3101;
const hostedBaseUrl = normalizeHostedBaseUrl(process.env.SMOKE_BASE_URL);
const useHostedBaseUrl = Boolean(hostedBaseUrl);

export default defineConfig({
  testDir: "./tests/smoke",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  globalTeardown: "./tests/smoke/assert-no-query-errors.ts",
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: hostedBaseUrl ?? `http://127.0.0.1:${PORT}`,
    trace: "on-first-retry",
  },
  webServer: useHostedBaseUrl
    ? undefined
    : {
        // tee truncates the log on each start; the global teardown scans it for failed data queries.
        command: `mkdir -p test-results && npm run start -- --hostname 127.0.0.1 --port ${PORT} 2>&1 | tee ${SERVER_LOG_PATH}`,
        url: `http://127.0.0.1:${PORT}`,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
  projects: [
    {
      name: "desktop-chromium",
      use: {
        browserName: "chromium",
        channel: "chromium",
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "mobile-chromium",
      use: {
        browserName: "chromium",
        channel: "chromium",
        ...devices["Pixel 7"],
      },
    },
  ],
});
