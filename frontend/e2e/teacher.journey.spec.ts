import { expect, request as pwRequest, test } from "@playwright/test";

import { stamp, teacherWithClass } from "./helpers";

const TEACHER = `t-journey-${stamp}@example.com`;

test("a teacher sees a student's mastery, creates a teaching aid and browses the question bank", async ({ page, baseURL }) => {
  test.setTimeout(120_000);
  // Set up a class and a student who has done onboarding, through the API.
  const api = await pwRequest.newContext({ baseURL });
  const code = await teacherWithClass(api, TEACHER);
  const student = await pwRequest.newContext({ baseURL });
  await student.post("/api/auth/register", { data: { email: `s-${stamp}@example.com`, password: "correct-horse-1", full_name: "Rohan Mehta", join_code: code } });
  const answers = Object.fromEntries(Array.from({ length: 20 }, (_, i) => [`q${String(i + 1).padStart(2, "0")}`, i % 2 ? "a" : "b"]));
  expect((await student.post("/api/onboarding/questionnaire", { data: { answers } })).status()).toBe(200);
  const diag = await (await student.post("/api/quiz/start", { data: { kind: "diagnostic" } })).json();
  for (const q of diag.questions) await student.post(`/api/quiz/attempts/${diag.id}/answer`, { data: { question_id: q.id, chosen_index: 0 } });
  expect((await student.post(`/api/quiz/attempts/${diag.id}/finish`)).status()).toBe(200);

  // Teacher signs in
  await page.goto("/login");
  await page.getByLabel("Email").fill(TEACHER);
  await page.getByLabel("Password").fill("correct-horse-1");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/teacher$/);
  await expect(page.getByTestId("heatmap")).toContainText("Rohan Mehta");
  await expect(page.getByTestId("suggestions")).toBeVisible();
  await expect(page.getByTestId("at-risk")).toBeVisible();

  // Student detail
  await page.getByTestId("heatmap").getByRole("link", { name: "Rohan Mehta" }).click();
  await expect(page.getByRole("heading", { name: "Rohan Mehta" })).toBeVisible();
  await expect(page.getByText("Learning preferences")).toBeVisible();

  // Create a teaching aid
  await page.goto("/teacher/aids/new");
  await page.getByLabel("Title").fill("Recursion in five lines");
  await page.getByLabel("Short id").fill(`recursion-five-lines-${stamp}`);
  await page.getByLabel("Card description").fill("A very short summary of recursion.");
  await page.getByLabel("Content in markdown").fill("# Recursion\n\nA function that calls itself on a smaller input, with a base case.");
  await page.getByRole("button", { name: "Create teaching aid" }).click();
  await expect(page).toHaveURL(/\/teacher\/aids$/);
  await page.getByLabel("Search aids").fill("five lines");
  await expect(page.getByRole("link", { name: "Recursion in five lines" })).toBeVisible();

  // Question bank and effectiveness
  await page.goto("/teacher/questions");
  await expect(page.getByText(/\d+ questions/)).toBeVisible();
  await page.goto("/teacher/effectiveness");
  await expect(page.getByRole("columnheader", { name: "Smoothed gain" })).toBeVisible();
});
