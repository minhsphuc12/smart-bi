// @ts-check
const { defineConfig, devices } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const apiDir = path.join(__dirname, "../api");
const venvPython = path.join(apiDir, ".venv/bin/python");
const apiPython = fs.existsSync(venvPython) ? venvPython : "python3";

/**
 * Isolated ports so `npm run test:e2e` does not fight with a developer stack on 3000/8000.
 * Override with PW_WEB_PORT / PW_API_PORT if needed.
 */
const webPort = process.env.PW_WEB_PORT || "3100";
const apiPort = process.env.PW_API_PORT || "8100";
const apiBase = `http://127.0.0.1:${apiPort}`;

module.exports = defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    trace: "on-first-retry"
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${apiPython} -m uvicorn app.main:app --port ${apiPort}`,
      cwd: apiDir,
      url: `${apiBase}/health`,
      reuseExistingServer: false,
      timeout: 90_000
    },
    {
      command: `npm run dev -- -p ${webPort}`,
      cwd: __dirname,
      url: `http://127.0.0.1:${webPort}`,
      env: {
        ...process.env,
        NEXT_PUBLIC_API_URL: apiBase
      },
      reuseExistingServer: false,
      timeout: 120_000
    }
  ]
});
