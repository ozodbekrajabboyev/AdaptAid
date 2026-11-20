"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { StyleProfile } from "@/components/learning/style-profile";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, unwrap } from "@/lib/api/client";
import { useMe } from "@/lib/auth";
import { useSummary } from "@/lib/learning";

const DIMENSIONS = [
  ["Active / reflective", "Active learners understand by doing: practice drills and interactive visuals. Reflective learners prefer to think it through first: notes and articles."],
  ["Sensing / intuitive", "Sensing learners like concrete examples and step-by-step procedures. Intuitive learners like ideas, theory and how concepts relate."],
  ["Visual / verbal", "Visual learners remember diagrams, animations and videos. Verbal learners remember written and spoken explanations."],
  ["Sequential / global", "Sequential learners go step by step. Global learners want the big picture first, like a concept map or cheat sheet."],
];

export default function ProfilePage() {
  const { data: me } = useMe();
  const summary = useSummary();
  const classes = useQuery({ queryKey: ["classes", "mine"], queryFn: () => unwrap(api.GET("/api/classes/mine")) });
  const [code, setCode] = useState("");
  const join = useMutation({
    mutationFn: () => unwrap(api.POST("/api/classes/join", { body: { code } })),
    onSuccess: () => { setCode(""); void classes.refetch(); },
  });

  if (summary.isPending) return <PageSkeleton />;
  const s = summary.data!;

  return (
    <div className="grid gap-5">
      <PageHeader title="My profile" description={`${me?.full_name ?? ""} · ${me?.email ?? ""}`} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Learning preferences</CardTitle>
            <CardDescription>
              Started from your questionnaire (hollow dots) and updated after {s.style.n_updates} quick check{s.style.n_updates === 1 ? "" : "s"} (filled dots).
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <StyleProfile style={s.style} />
            <Button asChild variant="outline" className="justify-self-start"><Link href="/profile/questionnaire">Retake the questionnaire</Link></Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">What the four scales mean</CardTitle>
            <CardDescription>Based on the Felder–Silverman model.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm">
            {DIMENSIONS.map(([t, d]) => (
              <div key={t}><p className="font-bold">{t}</p><p className="text-muted-foreground">{d}</p></div>
            ))}
            <p className="rounded-md bg-muted p-3 text-muted-foreground">
              Research on matching teaching to learning styles is mixed, so AdaptAid treats these as preferences, not labels.
              What you actually learn from each aid counts for more, and it always mixes in other formats.
            </p>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Classes</CardTitle>
          <CardDescription>Your teacher sees your mastery and progress in the classes you join.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          {classes.data?.length ? (
            <ul className="grid gap-1 text-sm">
              {classes.data.map((c) => <li key={c.id}><strong>{c.name}</strong> · {c.course_title} · {c.teacher_name}</li>)}
            </ul>
          ) : <p className="text-sm text-muted-foreground">You have not joined a class yet.</p>}
          <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); join.mutate(); }}>
            <Input aria-label="Class code" className="w-36 font-mono uppercase" placeholder="Class code" value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())} />
            <Button type="submit" variant="outline" disabled={code.length < 4 || join.isPending}>Join class</Button>
          </form>
          {join.error ? <p role="alert" className="text-sm text-destructive">{join.error.message}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
