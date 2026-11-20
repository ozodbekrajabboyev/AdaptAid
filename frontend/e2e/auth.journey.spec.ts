import { expect, test } from "@playwright/test";

const stamp = Date.now();

test("guests are sent to sign in, then back to the page they wanted", async ({ page }) => {
  await page.goto("/teacher");
  await expect(page).toHaveURL(/\/login\?next=%2Fteacher/);
});

test("a teacher registers, lands on the teacher area and can sign out", async ({ page }) => {
  await page.goto("/register");
  await page.getByRole("tab", { name: "I'm a teacher" }).click();
  await page.getByLabel("Full name").fill("Priya Teacher");
  await page.getByLabel("Email").fill(`teacher-${stamp}@example.com`);
  await page.getByLabel("Password").fill("correct-horse-1");
  await page.getByLabel("Teacher invite code").fill("TEACH-E2E");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/teacher$/);
  await expect(page.getByRole("heading", { name: "Class overview" })).toBeVisible();

  // Signed-in users skip the login page.
  await page.goto("/login");
  await expect(page).toHaveURL(/\/teacher$/);

  await page.getByTestId("user-menu").click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("a student cannot open teacher or admin pages", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Ravi Student");
  await page.getByLabel("Email").fill(`student-${stamp}@example.com`);
  await page.getByLabel("Password").fill("correct-horse-1");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);

  await page.goto("/teacher");
  await expect(page).toHaveURL(/\/home$/);
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/home$/);
});

test("wrong password shows a clear message", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`student-${stamp}@example.com`);
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Email or password is not correct.")).toBeVisible();
});
