/**
 * Screenshots of every key screen for review and for the report (docs/report-assets/screenshots).
 * Run against dev servers with demo data:
 *   make dev            # in another terminal, after `adaptaid seed-demo`
 *   PW_NO_SERVER=1 PW_BASE_URL=http://localhost:3000 npx playwright test --project=screens
 */
import { type Page, test } from "@playwright/test";
import path from "node:path";

const OUT = path.resolve(__dirname, "../../docs/report-assets/screenshots");
const PASSWORD = "demo-pass-2026";

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/(home|teacher|admin)$/);
}

async function shoot(page: Page, name: string, url: string, opts: { dark?: boolean; full?: boolean; wait?: string } = {}) {
  await page.emulateMedia({ colorScheme: opts.dark ? "dark" : "light" });
  await page.goto(url);
  await page.waitForLoadState("networkidle");
  if (opts.wait) await page.getByText(opts.wait).first().waitFor();
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/${name}${opts.dark ? "-dark" : ""}.png`, fullPage: opts.full ?? true });
}

test.describe.configure({ mode: "serial" });

test("student screens", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page, "student@adaptaid.demo");
  await shoot(page, "student-home", "/home", { wait: "Recommended for you" });
  await shoot(page, "student-home", "/home", { dark: true, wait: "Recommended for you" });
  await shoot(page, "student-path", "/path", { full: false });
  await shoot(page, "student-progress", "/progress", { wait: "Average mastery" });
  await shoot(page, "student-profile", "/profile");
  const first = page.getByTestId("rec-card").first();
  await page.goto("/home");
  await first.waitFor();
  const href = await first.locator("h3 a").getAttribute("href");
  await shoot(page, "student-aid", href!, { full: true });
  await page.goto("/library");
  await page.getByLabel("Search aids").fill("Call stack stepper");
  await page.getByText("Call stack stepper").click();
  for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Next step" }).click();
  await page.screenshot({ path: `${OUT}/student-interactive.png`, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await shoot(page, "student-home-phone", "/home", { wait: "Recommended for you" });
});

test("teacher screens", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page, "teacher@adaptaid.demo");
  await shoot(page, "teacher-overview", "/teacher", { wait: "Mastery heatmap" });
  await shoot(page, "teacher-overview", "/teacher", { dark: true, wait: "Mastery heatmap" });
  await shoot(page, "teacher-students", "/teacher/students");
  const link = page.getByRole("link", { name: "Diya Kapoor" }).first();
  await page.goto("/teacher/students");
  await link.click();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/teacher-student-detail.png`, fullPage: true });
  await shoot(page, "teacher-effectiveness", "/teacher/effectiveness");
  await shoot(page, "teacher-aid-form", "/teacher/aids/new");
  await page.setViewportSize({ width: 390, height: 844 });
  await shoot(page, "teacher-overview-phone", "/teacher", { wait: "Mastery heatmap" });
});

test("admin screens", async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page, "admin@adaptaid.demo");
  await shoot(page, "admin-models", "/admin/models", { wait: "Live, from this platform" });
  await shoot(page, "admin-jobs", "/admin/jobs");
});
