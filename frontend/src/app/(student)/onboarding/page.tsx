"use client";

import { useMutation } from "@tanstack/react-query";
import { CircleCheckIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { MasteryRow } from "@/components/learning/mastery";
import { QuestionnaireStep } from "@/components/learning/questionnaire";
import { QuizRunner, startQuiz } from "@/components/quiz/quiz-runner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, unwrap } from "@/lib/api/client";
import { type Attempt, type FinishResult, useInvalidateLearning, useOnboarding } from "@/lib/learning";
import { cn } from "@/lib/utils";

const STEPS = [
  { key: "questionnaire", label: "How you like to learn" },
  { key: "diagnostic", label: "Where you are now" },
] as const;

export default function OnboardingPage() {
  const status = useOnboarding();
  const invalidate = useInvalidateLearning();
  const [diagResult, setDiagResult] = useState<FinishResult | null>(null);

  if (status.isPending) return <PageSkeleton />;
  if (status.error) return <p className="text-destructive">{status.error.message}</p>;
  const s = status.data;

  if (diagResult) return <DiagnosticDone result={diagResult} />;

  const steps = [
    ...(s.consent_needed || s.pretest_needed ? [{ key: "consent", label: "Pilot study" }] : []),
    ...STEPS,
  ];
  const current = s.next_step === "pretest" ? "consent" : s.next_step;
  const index = steps.findIndex((x) => x.key === current);

  return (
    <div className="mx-auto grid max-w-2xl gap-6">
      <PageHeader title="Let's set you up" description="Two short steps so AdaptAid knows where to start. Nothing here is graded." />
      <ol className="flex flex-wrap gap-2" aria-label="Setup steps">
        {steps.map((step, i) => (
          <li key={step.key} className={cn("flex items-center gap-2 rounded-full border px-3 py-1 text-sm",
            i < index || s.next_step === "done" ? "border-success/50 text-success" : i === index ? "border-primary bg-accent font-bold text-accent-foreground" : "text-muted-foreground")}>
            {i < index || s.next_step === "done" ? <CircleCheckIcon className="size-4" aria-hidden /> : <span className="font-mono text-xs">{i + 1}</span>}
            {step.label}
          </li>
        ))}
      </ol>
      {s.next_step === "consent" ? <ConsentStep text={s.consent_text ?? ""} onDone={() => status.refetch()} /> : null}
      {s.next_step === "pretest" ? <QuizStep kind="pretest" title="Short starting test"
        intro="A few questions on the topics the pilot study covers. Answer as well as you can; it is fine not to know."
        onDone={() => status.refetch()} /> : null}
      {s.next_step === "questionnaire" ? <QuestionnaireStep onDone={() => { invalidate(); status.refetch(); }} /> : null}
      {s.next_step === "diagnostic" ? <QuizStep kind="diagnostic" title="Diagnostic quiz"
        intro="One question per topic in the course, about 10 minutes. You won't see right or wrong yet; we use your answers to choose where to start."
        onDone={(r) => { invalidate(); setDiagResult(r); }} /> : null}
      {s.next_step === "done" ? <AllSet /> : null}
      {!s.in_class ? <JoinClass onJoined={() => status.refetch()} /> : null}
    </div>
  );
}

function ConsentStep({ text, onDone }: { text: string; onDone: () => void }) {
  const consent = useMutation({ mutationFn: () => unwrap(api.POST("/api/onboarding/consent")), onSuccess: onDone });
  return (
    <Card>
      <CardHeader>
        <CardTitle>Taking part in the pilot study</CardTitle>
        <CardDescription>Please read this before you continue.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <p className="leading-7">{text}</p>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => consent.mutate()} disabled={consent.isPending}>I agree to take part</Button>
        </div>
        <p className="text-sm text-muted-foreground">If you do not want to take part, close this page and tell your teacher.</p>
      </CardContent>
    </Card>
  );
}

function QuizStep({ kind, title, intro, onDone }: { kind: "diagnostic" | "pretest"; title: string; intro: string; onDone: (r: FinishResult) => void }) {
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const start = useMutation({ mutationFn: () => startQuiz({ kind }), onSuccess: setAttempt });
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {!attempt ? <CardDescription>{intro}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {attempt ? (
          <QuizRunner attempt={attempt} feedback={false} onFinished={onDone} finishLabel="Finish" />
        ) : (
          <div className="grid gap-2">
            <Button size="lg" className="justify-self-start" onClick={() => start.mutate()} disabled={start.isPending}>
              {start.isPending ? "Loading…" : "Start"}
            </Button>
            {start.error ? <p role="alert" className="text-sm text-destructive">{start.error.message}</p> : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function DiagnosticDone({ result }: { result: FinishResult }) {
  const router = useRouter();
  return (
    <div className="mx-auto grid max-w-2xl gap-6">
      <PageHeader title="You're all set" description={`You answered ${result.n_correct} of ${result.n_total} correctly. Here is where AdaptAid thinks you are on each topic.`} />
      <Card>
        <CardContent className="grid gap-2.5 pt-6">
          {result.changes.map((c) => <MasteryRow key={c.concept_id} name={c.name} p={c.after} status="available" />)}
        </CardContent>
      </Card>
      <Button size="lg" className="justify-self-start" onClick={() => router.push("/home")}>See my recommendations</Button>
    </div>
  );
}

function AllSet() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Setup is complete</CardTitle>
        <CardDescription>You can retake the questionnaire from your profile at any time.</CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild><Link href="/home">Go to my dashboard</Link></Button>
      </CardContent>
    </Card>
  );
}

function JoinClass({ onJoined }: { onJoined: () => void }) {
  const [code, setCode] = useState("");
  const join = useMutation({ mutationFn: () => unwrap(api.POST("/api/classes/join", { body: { code } })), onSuccess: onJoined });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Join your class</CardTitle>
        <CardDescription>Enter the code from your teacher so they can see your progress.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); join.mutate(); }}>
          <input aria-label="Class code" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())}
            className="h-8 w-32 rounded-lg border bg-background px-2.5 font-mono uppercase" placeholder="K7P2QM" />
          <Button type="submit" variant="outline" disabled={code.length < 4 || join.isPending}>Join</Button>
        </form>
        {join.error ? <p role="alert" className="mt-2 text-sm text-destructive">{join.error.message}</p> : null}
      </CardContent>
    </Card>
  );
}
