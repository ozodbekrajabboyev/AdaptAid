"use client";

import { ArrowRightIcon, FlameIcon, RefreshCwIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { PageSkeleton } from "@/components/app-shell";
import { MasteryLegend, MasteryRow } from "@/components/learning/mastery";
import { RecCard } from "@/components/learning/rec-card";
import { StyleProfile } from "@/components/learning/style-profile";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import { useMe } from "@/lib/auth";
import { pct, useRecs, useRefreshRecs, useSummary } from "@/lib/learning";

const PHASE_LABEL: Record<string, string> = {
  cold: "Getting to know you",
  warm: "Learning your patterns",
  established: "Personalised",
  static: "Course plan",
};

export default function StudentHome() {
  const router = useRouter();
  const { data: me } = useMe();
  const summary = useSummary();
  const recs = useRecs();
  const refresh = useRefreshRecs();
  const seen = useRef<number | null>(null);

  const study = useQuery({ queryKey: ["study", "status"], queryFn: async () => (await unwrap(api.GET("/api/study/status"))) as unknown as { posttest_open: boolean; posttest_done: boolean; survey_done: boolean } });
  const needsOnboarding = summary.data && summary.data.onboarding.next_step !== "done";
  useEffect(() => {
    if (needsOnboarding) router.replace("/onboarding");
  }, [needsOnboarding, router]);

  // Record an impression once per list actually shown.
  useEffect(() => {
    const id = recs.data?.id;
    if (id && recs.data?.items.length && seen.current !== id) {
      seen.current = id;
      void api.POST("/api/recommendations/impression", { body: { list_id: id } });
    }
  }, [recs.data]);

  if (summary.isPending || recs.isPending || needsOnboarding) return <PageSkeleton />;
  if (summary.error) return <p className="text-destructive">{summary.error.message}</p>;
  const s = summary.data;
  const list = recs.data;
  const top = list?.items.find((i) => i.concept_id === s.focus?.concept_id) ?? list?.items[0];
  const firstName = me?.full_name.split(" ")[0] ?? "";

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="grid gap-1">
          <h1 className="font-heading text-2xl font-bold tracking-tight md:text-3xl">Welcome back, {firstName}</h1>
          <p className="text-muted-foreground">
            {s.course_title} · {s.mastered} of {s.total_concepts} concepts mastered
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {s.streak_days > 0 ? (
            <Badge variant="secondary" className="gap-1 text-success">
              <FlameIcon className="size-3.5" aria-hidden /> {s.streak_days}-day streak
            </Badge>
          ) : null}
          <Badge variant="outline">{PHASE_LABEL[list?.phase ?? s.phase] ?? s.phase}</Badge>
        </div>
      </div>

      {study.data?.posttest_open && !(study.data.posttest_done && study.data.survey_done) ? (
        <Link href="/study" className="rounded-lg border border-highlight bg-highlight/30 p-4 text-sm hover:bg-highlight/50">
          <strong>Pilot study:</strong> the final test and a short survey are open. They take about 15 minutes.
        </Link>
      ) : null}

      {s.focus && top ? (
        <section className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-primary bg-accent p-5">
          <div className="grid gap-1">
            <span className="text-xs font-bold tracking-wider text-muted-foreground uppercase">Next up</span>
            <span className="font-heading text-2xl font-bold">{s.focus.name}</span>
            <span className="text-sm text-muted-foreground">
              Mastery {pct(s.focus.mastery)} · about {s.focus.minutes} min with a quick check
            </span>
          </div>
          <Button asChild size="lg" className="px-5">
            <Link href={`/learn/${top.aid.id}?item=${top.id}`}>
              Start with the top pick <ArrowRightIcon />
            </Link>
          </Button>
        </section>
      ) : null}

      <section aria-labelledby="recs-title" className="grid gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="recs-title" className="font-heading text-lg font-bold">Recommended for you</h2>
          <Button variant="ghost" size="sm" onClick={() => refresh.mutate(null)} disabled={refresh.isPending}>
            <RefreshCwIcon className={refresh.isPending ? "animate-spin" : ""} /> Refresh
          </Button>
        </div>
        {list?.items.length ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {list.items.map((item, i) => <RecCard key={item.id} item={item} featured={i === 0} />)}
          </div>
        ) : (
          <Card><CardContent className="py-8 text-center text-muted-foreground">{list?.message ?? "No recommendations yet."}</CardContent></Card>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-[1.15fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Concept mastery</CardTitle>
            <CardDescription>Estimated with Bayesian Knowledge Tracing after every answer. Mastered at 95%.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2.5">
            {s.mastery.map((m) => <MasteryRow key={m.concept_id} name={m.name} p={m.p} status={m.status} />)}
            <div className="pt-2"><MasteryLegend /></div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">How you seem to learn</CardTitle>
            <CardDescription>
              {s.style.n_updates
                ? `From your questionnaire, adjusted by ${s.style.n_updates} quick check${s.style.n_updates === 1 ? "" : "s"}. The hollow dot is where you started.`
                : "From your questionnaire. It will adjust as AdaptAid sees which aids help you."}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <StyleProfile style={s.style} />
            <p className="text-sm text-muted-foreground">
              {s.style.dominant
                ? `Right now you lean most toward ${s.style.dominant} material.`
                : "Your profile is balanced, so formats are mixed."}{" "}
              <Link href="/profile" className="text-primary underline-offset-4 hover:underline">What does this mean?</Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
