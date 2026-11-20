import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright runs its own backend (port 8100, database adaptaid_e2e) and a production
 * build of the frontend (port 3100), so tests never touch your dev servers or dev data.
 * Set PW_WEB_CMD="npx next dev -p 3100" for a faster local loop.
 */
const API_PORT = 8100;
const WEB_PORT = 3100;
const E2E_DB =
  process.env.E2E_DATABASE_URL ?? "postgresql+psycopg://adaptaid:adaptaid@localhost:5434/adaptaid_e2e";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  timeout: 60_000,
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "contract", testMatch: /.*\.contract\.spec\.ts/ },
    { name: "e2e", testMatch: /.*\.journey\.spec\.ts/, use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      command: `../backend/.venv/bin/uvicorn app.main:app --app-dir ../backend --port ${API_PORT}`,
      url: `http://localhost:${API_PORT}/api/health`,
      env: {
        DATABASE_URL: E2E_DB,
        ENABLE_CONTRACT_ROUTES: "true",
        APP_ENV: "test",
        COOKIE_SECURE: "false",
      },
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: process.env.PW_WEB_CMD ?? `npm run build && PORT=${WEB_PORT} npm run start:standalone`,
      url: `http://localhost:${WEB_PORT}/api/health`,
      env: { BACKEND_URL: `http://localhost:${API_PORT}` },
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
    },
  ],
});
