import { expect, test } from "@playwright/test";

import { answerQuiz, stamp, teacherWithClass } from "./helpers";

test.describe.configure({ mode: "serial" });

test("a new student goes from sign-up to a quick check that changes their recommendations", async ({ page, request }) => {
  test.setTimeout(180_000);
  const code = await teacherWithClass(request, `t-student-journey-${stamp}@example.com`);

  // Register with the class code
  await page.goto(`/register?code=${code}`);
  await page.getByLabel("Full name").fill("Kavya Student");
  await page.getByLabel("Email").fill(`kavya-${stamp}@example.com`);
  await page.getByLabel("Password").fill("correct-horse-1");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);

  // Questionnaire: 20 forced-choice items
  await expect(page.getByText("How do you like to learn?")).toBeVisible();
  const groups = page.getByRole("radiogroup");
  const n = await groups.count();
  expect(n).toBe(20);
  for (let i = 0; i < n; i++) await groups.nth(i).getByRole("radio").nth(i % 3 === 0 ? 1 : 0).click();
  await page.getByRole("button", { name: "See my profile" }).click();
  await expect(page.getByText("Your starting profile")).toBeVisible();
  await page.getByRole("button", { name: "Continue to the diagnostic" }).click();

  // Diagnostic: one question per concept, no feedback
  await page.getByRole("button", { name: "Start" }).click();
  await answerQuiz(page, { feedback: false, pick: 1 });
  await expect(page.getByRole("heading", { name: "You're all set" })).toBeVisible();
  await page.getByRole("button", { name: "See my recommendations" }).click();

  // Dashboard with recommendations and reasons
  await expect(page).toHaveURL(/\/home$/);
  const cards = page.getByTestId("rec-card");
  await expect(cards.first()).toBeVisible();
  expect(await cards.count()).toBeGreaterThanOrEqual(3);
  await expect(cards.first().getByText("Why this")).toBeVisible();
  const firstTitles = await cards.locator("h3").allTextContents();

  // Open the top recommendation, finish it, rate it, take the quick check
  await cards.first().locator("h3 a").click();
  await expect(page).toHaveURL(/\/learn\/\d+\?item=\d+/);
  await page.getByRole("button", { name: "I've finished this aid" }).click();
  await page.getByRole("radio", { name: "Yes" }).click();
  await page.getByRole("button", { name: "Take the 3-question quick check" }).click();
  await answerQuiz(page, { feedback: true, pick: 0 });
  const change = page.getByTestId("mastery-change");
  await expect(change).toBeVisible();
  await expect(change).toContainText("→");

  // The list was regenerated after the check
  await page.getByRole("link", { name: "See what's next" }).click();
  await expect(page).toHaveURL(/\/home$/);
  await expect(cards.first()).toBeVisible();
  const newTitles = await cards.locator("h3").allTextContents();
  expect(newTitles).not.toEqual(firstTitles);

  // Other student pages render
  await page.getByRole("link", { name: "Learning path" }).first().click();
  await expect(page.getByTestId("path-graph").locator(".react-flow__node")).toHaveCount(13);
  await page.getByRole("link", { name: "Progress" }).first().click();
  await expect(page.getByText("Average mastery across all concepts")).toBeVisible();
  await page.getByRole("link", { name: "Library" }).first().click();
  await page.getByLabel("Search aids").fill("recursion");
  await expect(page.getByText("Recursion: base case, recursive case and the call stack")).toBeVisible();
});

test("built-in interactive aids work", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(`kavya-${stamp}@example.com`);
  await page.getByLabel("Password").fill("correct-horse-1");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/home$/);
  await page.goto("/library");
  await page.getByLabel("Search aids").fill("Call stack stepper");
  await page.getByText("Call stack stepper").click();
  const viz = page.getByTestId("recursion-stack");
  await expect(viz).toBeVisible();
  for (let i = 0; i < 3; i++) await viz.getByRole("button", { name: "Next step" }).click();
  await expect(viz.getByRole("listitem").first()).toContainText("factorial(");
});
