"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { QuizRunner } from "@/components/quiz/quiz-runner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { api, unwrap } from "@/lib/api/client";
import type { Attempt } from "@/lib/learning";
import { cn } from "@/lib/utils";

type StudyStatus = { active: boolean; participating: boolean; pretest_done: boolean; posttest_open: boolean; posttest_done: boolean; survey_done: boolean };
type Survey = { scale: string[]; items: string[]; satisfaction: { scale: string[]; items: string[]; open_question: string } };

export default function StudyPage() {
  const qc = useQueryClient();
  const status = useQuery({ queryKey: ["study", "status"], queryFn: async () => (await unwrap(api.GET("/api/study/status"))) as unknown as StudyStatus });
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const start = useMutation({ mutationFn: () => unwrap(api.POST("/api/study/posttest")), onSuccess: setAttempt });

  if (status.isPending) return <PageSkeleton />;
  const s = status.data!;
  const refresh = () => qc.invalidateQueries({ queryKey: ["study"] });

  return (
    <div className="mx-auto grid max-w-2xl gap-5">
      <PageHeader title="Pilot study" description="Thank you for taking part. These last steps take about 15 minutes." />
      {!s.participating ? (
        <Card><CardContent className="pt-6 text-muted-foreground">You are not part of the pilot study.</CardContent></Card>
      ) : !s.posttest_done ? (
        <Card>
          <CardHeader>
            <CardTitle>Final test</CardTitle>
            <CardDescription>The same topics as the starting test, with different questions. You won&apos;t see right or wrong.</CardDescription>
          </CardHeader>
          <CardContent>
            {!s.posttest_open ? <p className="text-muted-foreground">Your teacher will open the final test at the end of the study.</p>
              : attempt ? <QuizRunner attempt={attempt} feedback={false} finishLabel="Finish" onFinished={refresh} />
              : <Button size="lg" onClick={() => start.mutate()} disabled={start.isPending}>Start the final test</Button>}
            {start.error ? <p role="alert" className="mt-2 text-sm text-destructive">{start.error.message}</p> : null}
          </CardContent>
        </Card>
      ) : !s.survey_done ? <SurveyForm onDone={refresh} /> : (
        <Card>
          <CardHeader><CardTitle>All done. Thank you!</CardTitle><CardDescription>You can keep using AdaptAid as before.</CardDescription></CardHeader>
          <CardContent><Button asChild><Link href="/home">Back to my dashboard</Link></Button></CardContent>
        </Card>
      )}
    </div>
  );
}

function Likert({ label, value, onChange, scale }: { label: string; value: number | undefined; onChange: (v: number) => void; scale: string[] }) {
  return (
    <div className="grid gap-2">
      <p className="text-sm font-medium">{label}</p>
      <div className="grid grid-cols-5 gap-1.5" role="radiogroup" aria-label={label}>
        {scale.map((s, i) => (
          <button key={s} type="button" role="radio" aria-checked={value === i + 1} onClick={() => onChange(i + 1)}
            className={cn("rounded-md border px-1 py-2 text-center text-[11px] leading-tight hover:border-primary/60",
              value === i + 1 && "border-primary bg-accent text-accent-foreground")}>
            <span className="block font-mono text-sm">{i + 1}</span>{s}
          </button>
        ))}
      </div>
    </div>
  );
}

function SurveyForm({ onDone }: { onDone: () => void }) {
  const survey = useQuery({ queryKey: ["study", "survey"], queryFn: async () => (await unwrap(api.GET("/api/study/survey"))) as unknown as Survey });
  const [sus, setSus] = useState<Record<number, number>>({});
  const [sat, setSat] = useState<Record<number, number>>({});
  const [comment, setComment] = useState("");
  const submit = useMutation({
    mutationFn: () => unwrap(api.POST("/api/study/survey", { body: { sus: Array.from({ length: 10 }, (_, i) => sus[i]), satisfaction: Array.from({ length: 5 }, (_, i) => sat[i]), comment } })),
    onSuccess: onDone,
  });
  if (!survey.data) return <PageSkeleton />;
  const done = Object.keys(sus).length === 10 && Object.keys(sat).length === 5;
  return (
    <Card>
      <CardHeader><CardTitle>About using AdaptAid</CardTitle><CardDescription>Fifteen short statements. Pick how much you agree.</CardDescription></CardHeader>
      <CardContent className="grid gap-5">
        {survey.data.items.map((item, i) => <Likert key={item} label={`${i + 1}. ${item}`} value={sus[i]} scale={survey.data.scale} onChange={(v) => setSus({ ...sus, [i]: v })} />)}
        {survey.data.satisfaction.items.map((item, i) => <Likert key={item} label={`${i + 11}. ${item}`} value={sat[i]} scale={survey.data.satisfaction.scale} onChange={(v) => setSat({ ...sat, [i]: v })} />)}
        <div className="grid gap-2">
          <label htmlFor="comment" className="text-sm font-medium">{survey.data.satisfaction.open_question} (optional)</label>
          <Textarea id="comment" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
        </div>
        {submit.error ? <p role="alert" className="text-sm text-destructive">{submit.error.message}</p> : null}
        <Button size="lg" className="justify-self-start" disabled={!done || submit.isPending} onClick={() => submit.mutate()}>
          {done ? "Send my answers" : "Answer every statement to continue"}
        </Button>
      </CardContent>
    </Card>
  );
}
