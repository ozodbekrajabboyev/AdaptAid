"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DownloadIcon } from "lucide-react";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { api, unwrap, type Schemas } from "@/lib/api/client";

type Study = Schemas["StudySettings"];

export default function StudyPage() {
  const q = useQuery({ queryKey: ["admin", "study"], queryFn: () => unwrap(api.GET("/api/admin/settings/study")) });
  if (q.isPending) return <PageSkeleton />;
  if (q.error) return <p className="text-destructive">{q.error.message}</p>;
  return <StudyForm initial={q.data} />;
}

function StudyForm({ initial }: { initial: Study }) {
  const qc = useQueryClient();
  const [s, setS] = useState<Study>(initial);
  const save = useMutation({
    mutationFn: () => unwrap(api.PUT("/api/admin/settings/study", { body: s })),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin", "study"] }); toast.success("Study settings saved"); },
  });
  const submit = (e: FormEvent) => { e.preventDefault(); save.mutate(); };
  const toggle = (k: "active" | "frozen" | "posttest_open", label: string, help: string) => (
    <div className="flex items-start justify-between gap-4 rounded-md border p-3">
      <div className="grid gap-0.5"><Label htmlFor={k}>{label}</Label><span className="text-sm text-muted-foreground">{help}</span></div>
      <Switch id={k} checked={s[k]} onCheckedChange={(v) => setS({ ...s, [k]: v })} />
    </div>
  );

  return (
    <div className="grid gap-5">
      <PageHeader title="Pilot study" description="An A/B comparison: half the class gets AdaptAid's adaptive recommendations, half gets the same aids in course-plan order. Follow docs/STUDY_PROTOCOL.md." />
      <form onSubmit={submit} className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <Card>
          <CardHeader><CardTitle className="text-base">Settings</CardTitle></CardHeader>
          <CardContent>
            <FieldGroup>
              {toggle("active", "Study running", "Students who join a class see the consent form and a pre-test, then get an arm. Simulated students are left out of every model.")}
              {toggle("frozen", "Freeze model parameters", "Stops nightly BKT refits so the adaptive arm gets the same model for the whole study.")}
              {toggle("posttest_open", "Post-test open", "Students see the post-test and the usability survey on their dashboard.")}
              <Field>
                <FieldLabel htmlFor="consent_version">Consent form version</FieldLabel>
                <Input id="consent_version" value={s.consent_version} onChange={(e) => setS({ ...s, consent_version: e.target.value })} />
              </Field>
              <Field>
                <FieldLabel htmlFor="consent_text">Consent text shown to students</FieldLabel>
                <Textarea id="consent_text" rows={7} value={s.consent_text} onChange={(e) => setS({ ...s, consent_text: e.target.value })} />
                <FieldDescription>Get your guide&apos;s approval for this text before the study starts.</FieldDescription>
              </Field>
              {save.error ? <p role="alert" className="text-sm text-destructive">{save.error.message}</p> : null}
              <Button type="submit" className="justify-self-start" disabled={save.isPending}>Save settings</Button>
            </FieldGroup>
          </CardContent>
        </Card>
        <Card className="self-start">
          <CardHeader>
            <CardTitle className="text-base">Results</CardTitle>
            <CardDescription>One row per participant with a pseudonymous id, arm, pre- and post-test scores, normalised gain, usage and SUS score. Analyse it with research/src/pilot_analysis.py.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline"><a href="/api/admin/study/export.csv"><DownloadIcon /> Download CSV</a></Button>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
