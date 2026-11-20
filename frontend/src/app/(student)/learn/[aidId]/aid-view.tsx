"use client";

import { useMutation } from "@tanstack/react-query";
import { ArrowLeftIcon, ClockIcon, ExternalLinkIcon, ThumbsDownIcon, ThumbsUpIcon, MehIcon } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { PageSkeleton } from "@/components/app-shell";
import { AidTypeBadge } from "@/components/learning/aid-type";
import { MasteryBar } from "@/components/learning/mastery";
import { Markdown } from "@/components/markdown";
import { QuizRunner, startQuiz } from "@/components/quiz/quiz-runner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BstBuilder } from "@/components/visualizers/bst-builder";
import { RecursionStack } from "@/components/visualizers/recursion-stack";
import { SortingStepper } from "@/components/visualizers/sorting-stepper";
import { api, unwrap } from "@/lib/api/client";
import { type AidDetail, type Attempt, type FinishResult, pct, useAid, useInvalidateLearning } from "@/lib/learning";
import { cn } from "@/lib/utils";

// Guards against React StrictMode's double effect in development sending two "open" events.
const opened = new Map<string, Promise<number | null>>();

function useAidSession(aid: AidDetail | undefined, itemId: number | null, source: string) {
  const [token] = useState(() => Math.random().toString(36).slice(2));
  const [useId, setUseId] = useState<number | null>(null);
  const [pOpen, setPOpen] = useState<number | null>(null);

  useEffect(() => {
    if (!aid) return;
    const key = `${token}:${aid.id}`;
    if (!opened.has(key)) {
      opened.set(key, unwrap(api.POST("/api/events", {
        body: { aid_id: aid.id, event: "open", item_id: itemId, source: (itemId ? "rec" : source) as "rec" | "library" | "path" | "direct" },
      })).then((r) => { setPOpen(r.p_open ?? null); return r.use_id ?? null; }).catch(() => null));
    }
    void opened.get(key)!.then(setUseId);
  }, [aid, itemId, source, token]);

  // Heartbeat every 30 s while the tab is visible: time spent with the aid.
  useEffect(() => {
    if (!aid || !useId) return;
    const t = setInterval(() => {
      if (document.visibilityState === "visible") {
        void api.POST("/api/events", { body: { aid_id: aid.id, event: "heartbeat", use_id: useId, seconds: 30, source: "direct" } });
      }
    }, 30_000);
    return () => clearInterval(t);
  }, [aid, useId]);

  return { useId, pOpen };
}

export function AidView() {
  const { aidId } = useParams<{ aidId: string }>();
  const params = useSearchParams();
  const itemId = params.get("item") ? Number(params.get("item")) : null;
  const source = params.get("source") ?? "direct";
  const aid = useAid(Number(aidId));
  const { useId, pOpen } = useAidSession(aid.data, itemId, source);

  if (aid.isPending) return <PageSkeleton />;
  if (aid.error) return <p className="text-destructive">{aid.error.message}</p>;
  const a = aid.data;

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <Link href="/home" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeftIcon className="size-4" /> Back to recommendations
      </Link>
      <header className="grid gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <AidTypeBadge type={a.aid_type} />
          <span className="text-sm text-muted-foreground">{a.concept_name}</span>
        </div>
        <h1 className="font-heading text-2xl font-bold tracking-tight md:text-3xl">{a.title}</h1>
        <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1"><ClockIcon className="size-3.5" />{a.duration_min} min</span>
          <span>level {a.difficulty}/5</span>
          <span>{a.source}</span>
        </p>
      </header>

      <AidBody aid={a} />
      {a.aid_type === "practice" && a.n_drill_questions > 0 ? <Drill aid={a} /> : null}
      <AfterAid aid={a} useId={useId} pOpen={pOpen} />
    </div>
  );
}

function AidBody({ aid }: { aid: AidDetail }) {
  if (aid.delivery === "native_md") {
    return (
      <Card>
        <CardContent className="pt-6">
          <Markdown>{aid.body_md ?? ""}</Markdown>
        </CardContent>
      </Card>
    );
  }
  if (aid.delivery === "interactive_component") {
    const Comp = { "sorting-stepper": SortingStepper, "recursion-stack": RecursionStack, "bst-builder": BstBuilder }[
      aid.component_key ?? ""
    ];
    return (
      <Card>
        <CardHeader>
          <CardDescription>{aid.description}</CardDescription>
        </CardHeader>
        <CardContent>{Comp ? <Comp /> : <p className="text-muted-foreground">This interactive aid is not available.</p>}</CardContent>
      </Card>
    );
  }
  const host = aid.url ? new URL(aid.url).hostname.replace(/^www\./, "") : "";
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">This aid opens on {host}</CardTitle>
        <CardDescription>{aid.description}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <Button asChild size="lg" className="justify-self-start">
          <a href={aid.url ?? "#"} target="_blank" rel="noreferrer">
            Open {aid.aid_type === "video" ? "the video" : aid.aid_type === "animation" ? "the animation" : "the article"}
            <ExternalLinkIcon />
          </a>
        </Button>
        <p className="text-sm text-muted-foreground">
          It opens in a new tab. Come back here when you are done to mark it finished and take the quick check.
        </p>
      </CardContent>
    </Card>
  );
}

function Drill({ aid }: { aid: AidDetail }) {
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [done, setDone] = useState<FinishResult | null>(null);
  const start = useMutation({ mutationFn: () => startQuiz({ kind: "drill", aid_id: aid.id }), onSuccess: setAttempt });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Drill questions</CardTitle>
        <CardDescription>{aid.n_drill_questions} questions with explanations. They count toward your mastery.</CardDescription>
      </CardHeader>
      <CardContent>
        {done ? (
          <p className="text-sm">You got {done.n_correct} of {done.n_total} right. Now mark the aid finished and take the quick check.</p>
        ) : attempt ? (
          <QuizRunner attempt={attempt} onFinished={setDone} finishLabel="Finish the drill" />
        ) : (
          <Button onClick={() => start.mutate()} disabled={start.isPending}>Start the drill</Button>
        )}
      </CardContent>
    </Card>
  );
}

function AfterAid({ aid, useId, pOpen }: { aid: AidDetail; useId: number | null; pOpen: number | null }) {
  const invalidate = useInvalidateLearning();
  const [finished, setFinished] = useState(false);
  const [rating, setRating] = useState<number | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [result, setResult] = useState<FinishResult | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  const event = useMutation({
    mutationFn: (body: { event: "complete" | "rate"; rating?: number }) =>
      unwrap(api.POST("/api/events", { body: { aid_id: aid.id, use_id: useId, source: "direct", ...body } })),
  });
  const start = useMutation({
    mutationFn: () => startQuiz({ kind: "check", use_id: useId ?? undefined }),
    onSuccess: setAttempt,
  });

  useEffect(() => {
    if (result) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [result]);

  if (result) {
    const change = result.changes[0];
    const gain = result.gain;
    const verdict = gain === null || gain === undefined
      ? "These questions were repeats, so this check did not count toward measuring the aid."
      : gain > 0.05 ? "You did better than expected. This aid seems to work for you."
      : gain < -0.05 ? "That was harder than expected. AdaptAid will try a different kind of aid next."
      : "About what we expected for your level.";
    return (
      <Card ref={resultRef} className="border-success/50">
        <CardHeader>
          <CardTitle>{result.n_correct} of {result.n_total} correct</CardTitle>
          <CardDescription>{verdict}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {change ? (
            <div className="grid gap-2" data-testid="mastery-change">
              <div className="flex items-baseline justify-between text-sm">
                <span>{change.name} mastery</span>
                <span className="font-mono text-lg font-bold tabular">{pct(change.before)} → {pct(change.after)}</span>
              </div>
              <MasteryBar p={change.after} className="h-3" />
            </div>
          ) : null}
          <Button asChild size="lg" className="justify-self-start" onClick={invalidate}>
            <Link href="/home">See what&apos;s next</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (attempt) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Quick check · {aid.concept_name}</CardTitle>
          <CardDescription>Three questions. Your mastery updates after each one.</CardDescription>
        </CardHeader>
        <CardContent>
          <QuizRunner attempt={attempt} onFinished={(r) => { setResult(r); invalidate(); }} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="grid gap-4 pt-6">
        {!finished ? (
          <div className="flex flex-wrap items-center gap-3">
            <Button size="lg" onClick={() => { setFinished(true); event.mutate({ event: "complete" }); }} disabled={!useId}>
              I&apos;ve finished this aid
            </Button>
            <span className="text-sm text-muted-foreground">
              {pOpen !== null ? `You started at ${pct(pOpen)} on ${aid.concept_name}.` : ""}
            </span>
          </div>
        ) : (
          <>
            <div className="grid gap-2">
              <span className="text-sm font-bold">Did this help?</span>
              <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Did this help?">
                {([[5, "Yes", ThumbsUpIcon], [3, "Somewhat", MehIcon], [1, "No", ThumbsDownIcon]] as const).map(([value, label, Icon]) => (
                  <Button key={value} variant="outline" size="sm" role="radio" aria-checked={rating === value}
                    className={cn(rating === value && "border-primary bg-accent text-accent-foreground")}
                    onClick={() => { setRating(value); event.mutate({ event: "rate", rating: value }); }}>
                    <Icon /> {label}
                  </Button>
                ))}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button size="lg" onClick={() => start.mutate()} disabled={start.isPending || !useId}>
                Take the 3-question quick check
              </Button>
              <span className="text-sm text-muted-foreground">It shows how much this aid helped.</span>
            </div>
            {start.error ? <p role="alert" className="text-sm text-destructive">{start.error.message}</p> : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
