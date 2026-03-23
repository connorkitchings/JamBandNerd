import { defineConfig, devices } from "@playwright/test";

const PORT = 3101;
const hostedBaseUrl = process.env.SMOKE_BASE_URL?.replace(/\/+$/, "");
const useHostedBaseUrl = Boolean(hostedBaseUrl);

export default defineConfig({
  testDir: "./tests/smoke",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
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
        command: `npm run start -- --hostname 127.0.0.1 --port ${PORT}`,
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
