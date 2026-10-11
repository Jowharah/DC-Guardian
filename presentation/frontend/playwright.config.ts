import {defineConfig} from "@playwright/test";

// Browser tests run against the production build served by `vite preview`;
// the API is mocked per test (e2e/mockApi.ts), so no backend is needed.
// Locally the installed Microsoft Edge is used (set PW_CHANNEL to change it);
// CI uses Playwright's bundled Chromium.
export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", {open: "never"}]] : "list",
  use: {
    baseURL: "http://127.0.0.1:4173",
    channel: process.env.CI ? undefined : (process.env.PW_CHANNEL ?? "msedge"),
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run build && npx vite preview --host 127.0.0.1 --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
