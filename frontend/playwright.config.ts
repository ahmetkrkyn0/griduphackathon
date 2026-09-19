import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: "http://127.0.0.1:5187",
    channel: "msedge",
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev:mock -- --host 127.0.0.1 --port 5187 --strictPort",
    url: "http://127.0.0.1:5187",
    reuseExistingServer: !process.env.CI,
  },
});
