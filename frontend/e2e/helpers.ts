import { type APIRequestContext, expect, type Page } from "@playwright/test";

export const stamp = Date.now();

/** Answer every question of the quiz on screen, always picking option `pick` (0-3). */
export async function answerQuiz(page: Page, opts: { feedback: boolean; pick?: number }) {
  const quiz = page.getByTestId("quiz");
  await expect(quiz).toBeVisible();
  for (let guard = 0; guard < 40; guard++) {
    const options = quiz.getByRole("radio");
    await options.nth(opts.pick ?? 0).click();
    if (opts.feedback) {
      await quiz.getByRole("button", { name: "Check answer" }).click();
      const next = quiz.getByRole("button", { name: /Next question|See my results|Finish/ });
      await expect(next).toBeVisible();
      const label = (await next.textContent()) ?? "";
      await next.click();
      if (!label.startsWith("Next")) return;
    } else {
      const next = quiz.getByRole("button", { name: /^(Next|Submit)$/ });
      const label = (await next.textContent()) ?? "";
      await next.click();
      if (label === "Submit") return;
      await expect(quiz.getByText(`Question ${guard + 2} of`)).toBeVisible();
    }
  }
  throw new Error("quiz did not finish");
}

/** Create a teacher and a class through the API; returns the join code. */
export async function teacherWithClass(request: APIRequestContext, email: string): Promise<string> {
  const reg = await request.post("/api/auth/register", {
    data: { email, password: "correct-horse-1", full_name: "Asha Teacher", role: "teacher", invite_code: "TEACH-E2E" },
  });
  expect(reg.status()).toBe(201);
  const courses = await (await request.get("/api/courses")).json();
  const klass = await request.post("/api/classes", { data: { name: "E2E Class", course_id: courses[0].id } });
  expect(klass.status()).toBe(201);
  const code = (await klass.json()).join_code as string;
  await request.post("/api/auth/logout");
  return code;
}
