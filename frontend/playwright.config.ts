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

// PW_BASE_URL + PW_NO_SERVER=1: run against servers you started yourself (e.g. `make dev` with demo data).
const external = process.env.PW_NO_SERVER === "1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  timeout: 60_000,
  use: {
    baseURL: process.env.PW_BASE_URL ?? `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "contract", testMatch: /.*\.contract\.spec\.ts/ },
    { name: "e2e", testMatch: /.*\.journey\.spec\.ts/, use: { ...devices["Desktop Chrome"] } },
    { name: "screens", testMatch: /.*\.screens\.ts/, use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: external ? undefined : [
    {
      command: `cd ../backend && .venv/bin/python -m app.cli reset-db --force && .venv/bin/python -m app.cli seed && .venv/bin/python -m app.cli create-admin --email admin-e2e@example.com --full-name "E2E Admin" --password e2e-admin-pass && .venv/bin/uvicorn app.main:app --port ${API_PORT}`,
      url: `http://localhost:${API_PORT}/api/health`,
      env: {
        DATABASE_URL: E2E_DB,
        ENABLE_CONTRACT_ROUTES: "true",
        APP_ENV: "test",
        COOKIE_SECURE: "false",
        TEACHER_INVITE_CODE: "TEACH-E2E",
      },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
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
