"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { PageSkeleton } from "@/components/app-shell";
import { StyleProfile } from "@/components/learning/style-profile";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, unwrap, type Schemas } from "@/lib/api/client";
import { cn } from "@/lib/utils";

export function QuestionnaireStep({ onDone, continueLabel = "Continue to the diagnostic" }: { onDone: () => void; continueLabel?: string }) {
  const q = useQuery({ queryKey: ["questionnaire"], queryFn: () => unwrap(api.GET("/api/onboarding/questionnaire")) });
  const [answers, setAnswers] = useState<Record<string, "a" | "b">>({});
  const [style, setStyle] = useState<Schemas["StyleOut"] | null>(null);
  const submit = useMutation({
    mutationFn: () => unwrap(api.POST("/api/onboarding/questionnaire", { body: { answers } })),
    onSuccess: setStyle,
  });
  if (q.isPending) return <PageSkeleton />;
  if (q.error) return <p className="text-destructive">{q.error.message}</p>;
  const items = q.data.items;
  const done = Object.keys(answers).length;

  if (style) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Your starting profile</CardTitle>
          <CardDescription>
            This is only a starting point. As you use teaching aids, AdaptAid moves these sliders toward the formats that actually help you.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-5">
          <StyleProfile style={style} showPrior={false} />
          <Button className="justify-self-start" onClick={onDone}>{continueLabel}</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{q.data.title}</CardTitle>
        <CardDescription>{q.data.intro}</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="questions">
          <TabsList className="mb-4">
            <TabsTrigger value="questions">Answer 20 questions</TabsTrigger>
            <TabsTrigger value="ils">I already have ILS scores</TabsTrigger>
          </TabsList>
          <TabsContent value="questions" className="grid gap-5">
            <div className="grid gap-1.5">
              <Progress value={(done / items.length) * 100} />
              <span className="text-xs text-muted-foreground tabular">{done} of {items.length} answered</span>
            </div>
            <ol className="grid gap-4">
              {items.map((item, i) => (
                <li key={item.key} className="grid gap-2">
                  <p className="font-bold"><span className="mr-2 font-mono text-xs text-muted-foreground">{i + 1}</span>{item.prompt}</p>
                  <div className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label={item.prompt}>
                    {(["a", "b"] as const).map((choice) => (
                      <button key={choice} type="button" role="radio" aria-checked={answers[item.key] === choice}
                        onClick={() => setAnswers((a) => ({ ...a, [item.key]: choice }))}
                        className={cn("rounded-lg border bg-card px-3 py-2.5 text-left text-sm transition-colors hover:border-primary/60",
                          answers[item.key] === choice && "border-primary bg-accent text-accent-foreground")}>
                        {item[choice]}
                      </button>
                    ))}
                  </div>
                </li>
              ))}
            </ol>
            {submit.error ? <p role="alert" className="text-sm text-destructive">{submit.error.message}</p> : null}
            <Button size="lg" className="justify-self-start" disabled={done < items.length || submit.isPending} onClick={() => submit.mutate()}>
              {done < items.length ? `Answer all ${items.length} to continue` : "See my profile"}
            </Button>
            <p className="text-xs text-muted-foreground">{q.data.note}</p>
          </TabsContent>
          <TabsContent value="ils">
            <IlsForm onSaved={setStyle} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

const ILS_DIMS = [
  { key: "ar", poles: ["active", "reflective"] },
  { key: "si", poles: ["sensing", "intuitive"] },
  { key: "vv", poles: ["visual", "verbal"] },
  { key: "sg", poles: ["sequential", "global"] },
] as const;

function IlsForm({ onSaved }: { onSaved: (s: Schemas["StyleOut"]) => void }) {
  const [vals, setVals] = useState<Record<string, [number, string]>>({
    ar: [1, "active"], si: [1, "sensing"], vv: [1, "visual"], sg: [1, "sequential"],
  });
  const save = useMutation({
    mutationFn: () => unwrap(api.POST("/api/onboarding/ils", { body: vals as unknown as Schemas["IlsIn"] })),
    onSuccess: onSaved,
  });
  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">
        If you have taken Felder and Soloman&apos;s Index of Learning Styles, enter your four results, for example &quot;7 visual&quot;.
      </p>
      {ILS_DIMS.map((d) => (
        <div key={d.key} className="flex flex-wrap items-center gap-2">
          <Select value={String(vals[d.key][0])} onValueChange={(v) => setVals((x) => ({ ...x, [d.key]: [Number(v), x[d.key][1]] }))}>
            <SelectTrigger className="w-20" aria-label={`${d.poles.join("/")} score`}><SelectValue /></SelectTrigger>
            <SelectContent>{[1, 3, 5, 7, 9, 11].map((n) => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={vals[d.key][1]} onValueChange={(v) => setVals((x) => ({ ...x, [d.key]: [x[d.key][0], v] }))}>
            <SelectTrigger className="w-36" aria-label={`${d.poles.join("/")} pole`}><SelectValue /></SelectTrigger>
            <SelectContent>{d.poles.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      ))}
      {save.error ? <p role="alert" className="text-sm text-destructive">{save.error.message}</p> : null}
      <Button className="justify-self-start" onClick={() => save.mutate()} disabled={save.isPending}>Use these scores</Button>
    </div>
  );
}

