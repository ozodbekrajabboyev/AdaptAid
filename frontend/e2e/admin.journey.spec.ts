import { expect, test } from "@playwright/test";

test("an administrator runs the jobs and reads the model report", async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto("/login");
  await page.getByLabel("Email").fill("admin-e2e@example.com");
  await page.getByLabel("Password").fill("e2e-admin-pass");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "Administration" })).toBeVisible();

  await page.goto("/admin/jobs");
  await page.getByRole("button", { name: "Everything, in order" }).click();
  // five runs appear and none is left running
  await expect(page.getByRole("row").filter({ hasText: "admin" })).toHaveCount(5, { timeout: 60_000 });
  await expect(page.getByText("running", { exact: true })).toHaveCount(0, { timeout: 60_000 });

  await page.goto("/admin/models");
  await expect(page.getByRole("heading", { name: "Live, from this platform" })).toBeVisible();
  await expect(page.getByText("Recommender weights")).toBeVisible();

  await page.goto("/admin/users");
  await expect(page.getByRole("cell", { name: "admin-e2e@example.com" })).toBeVisible();

  await page.goto("/admin/study");
  await expect(page.getByLabel("Study running")).toBeVisible();
});
