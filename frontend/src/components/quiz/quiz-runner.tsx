"use client";

import { useMutation } from "@tanstack/react-query";
import { CircleCheckIcon, CircleXIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Markdown } from "@/components/markdown";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { api, unwrap } from "@/lib/api/client";
import type { AnswerResult, Attempt, FinishResult } from "@/lib/learning";
import { cn } from "@/lib/utils";

const LETTERS = ["A", "B", "C", "D"];

/**
 * Runs one quiz attempt: one question at a time. With `feedback` the learner sees right or
 * wrong and the explanation after each answer (quick checks, drills); without it
 * (diagnostic, pre/post tests) answers are recorded and the quiz moves on.
 */
export function QuizRunner({
  attempt,
  feedback = true,
  onFinished,
  finishLabel = "See my results",
}: {
  attempt: Attempt;
  feedback?: boolean;
  onFinished: (result: FinishResult) => void;
  finishLabel?: string;
}) {
  const firstOpen = attempt.questions.findIndex((q) => !(String(q.id) in attempt.answered));
  const [index, setIndex] = useState(firstOpen === -1 ? attempt.questions.length - 1 : firstOpen);
  const [chosen, setChosen] = useState<number | null>(null);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [correctCount, setCorrectCount] = useState(0);
  const started = useRef(0); // set when each question is shown (effect below)
  const q = attempt.questions[index];
  const isLast = index === attempt.questions.length - 1;

  useEffect(() => {
    started.current = Date.now();
  }, [index]);

  const answer = useMutation({
    mutationFn: (choice: number) =>
      unwrap(
        api.POST("/api/quiz/attempts/{attempt_id}/answer", {
          params: { path: { attempt_id: attempt.id } },
          body: { question_id: q.id, chosen_index: choice, time_ms: Date.now() - started.current },
        }),
      ),
    onSuccess: (r) => {
      if (r.correct) setCorrectCount((n) => n + 1);
      if (feedback) setResult(r);
      else advance();
    },
  });

  const finish = useMutation({
    mutationFn: () =>
      unwrap(api.POST("/api/quiz/attempts/{attempt_id}/finish", { params: { path: { attempt_id: attempt.id } } })),
    onSuccess: onFinished,
  });

  function advance() {
    if (isLast) {
      finish.mutate();
    } else {
      setIndex((i) => i + 1);
      setChosen(null);
      setResult(null);
    }
  }

  const locked = result !== null || answer.isPending;

  return (
    <div className="grid gap-5" data-testid="quiz">
      <div className="grid gap-2">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Question {index + 1} of {attempt.questions.length}
            {q.concept_name ? ` · ${q.concept_name}` : ""}
          </span>
          {feedback ? <span className="tabular">{correctCount} correct</span> : null}
        </div>
        <Progress value={((index + (result ? 1 : 0)) / attempt.questions.length) * 100} />
      </div>

      <div className="text-[1.02rem] font-bold [&_p]:my-1">
        <Markdown>{q.stem}</Markdown>
      </div>

      <div className="grid gap-2" role="radiogroup" aria-label="Answer options">
        {q.options.map((opt, i) => {
          const isChosen = chosen === i;
          const isRight = result && i === result.correct_index;
          const isWrongChoice = result && isChosen && !result.correct;
          return (
            <button
              key={i}
              type="button"
              role="radio"
              aria-checked={isChosen}
              disabled={locked}
              onClick={() => setChosen(i)}
              className={cn(
                "flex items-start gap-3 rounded-lg border bg-card px-3.5 py-3 text-left text-sm transition-colors",
                !locked && "hover:border-primary/60",
                isChosen && !result && "border-primary bg-accent",
                isRight && "border-success bg-success/10",
                isWrongChoice && "border-destructive bg-destructive/10",
                locked && !isRight && !isWrongChoice && "opacity-70",
              )}
            >
              <span className="mt-0.5 font-mono text-xs text-muted-foreground">{LETTERS[i]}</span>
              <span className="min-w-0 flex-1 [&_p]:my-0">
                <Markdown>{opt}</Markdown>
              </span>
              {isRight ? <CircleCheckIcon className="size-5 shrink-0 text-success" aria-label="Correct answer" /> : null}
              {isWrongChoice ? <CircleXIcon className="size-5 shrink-0 text-destructive" aria-label="Your answer" /> : null}
            </button>
          );
        })}
      </div>

      {result ? (
        <div
          role="status"
          className={cn(
            "rounded-lg border p-3.5 text-sm",
            result.correct ? "border-success/50 bg-success/10" : "border-destructive/40 bg-destructive/5",
          )}
        >
          <p className="mb-1 font-bold">{result.correct ? "Correct." : `Not quite. The answer is ${LETTERS[result.correct_index]}.`}</p>
          <div className="[&_p]:my-1">
            <Markdown>{result.explanation}</Markdown>
          </div>
        </div>
      ) : null}

      {answer.error || finish.error ? (
        <p role="alert" className="text-sm text-destructive">
          {(answer.error ?? finish.error)?.message}
        </p>
      ) : null}

      <div className="flex justify-end gap-2">
        {result ? (
          <Button size="lg" onClick={advance} disabled={finish.isPending}>
            {isLast ? (finish.isPending ? "Saving…" : finishLabel) : "Next question"}
          </Button>
        ) : (
          <Button size="lg" disabled={chosen === null || answer.isPending} onClick={() => chosen !== null && answer.mutate(chosen)}>
            {answer.isPending ? "Checking…" : feedback ? "Check answer" : isLast ? "Submit" : "Next"}
          </Button>
        )}
      </div>
    </div>
  );
}

export async function startQuiz(body: {
  kind: Attempt["kind"];
  concept_id?: number;
  use_id?: number;
  aid_id?: number;
}): Promise<Attempt> {
  return unwrap(api.POST("/api/quiz/start", { body }));
}
