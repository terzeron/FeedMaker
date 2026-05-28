const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  retries: 0,
  use: {
    baseURL: "https://localhost:8082",
    headless: true,
    ignoreHTTPSErrors: true,
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
  webServer: {
    command: "npx vite --host 0.0.0.0 --port 8082 --mode development",
    port: 8082,
    reuseExistingServer: true,
    timeout: 60000,
  },
});
