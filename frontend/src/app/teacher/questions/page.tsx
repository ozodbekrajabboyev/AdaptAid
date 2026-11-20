"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DownloadIcon, PlusIcon } from "lucide-react";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/app-shell";
import { Markdown } from "@/components/markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, unwrap, type Schemas } from "@/lib/api/client";
import { useConcepts } from "@/lib/learning";

type Q = Schemas["QuestionOut"];
type QIn = Schemas["QuestionIn"];
const POOLS: Record<string, string> = { diagnostic: "Diagnostic", check: "Quick check", drill: "Drill", study: "Pilot study" };

export default function QuestionBankPage() {
  const courses = useQuery({ queryKey: ["courses"], queryFn: () => unwrap(api.GET("/api/courses")) });
  const concepts = useConcepts(courses.data?.[0]?.id);
  const [concept, setConcept] = useState<string>("");
  const [pool, setPool] = useState("all");
  const conceptId = Number(concept || concepts.data?.[0]?.id || 0);
  const qs = useQuery({
    queryKey: ["questions", conceptId, pool],
    queryFn: () => unwrap(api.GET("/api/questions", { params: { query: { concept_id: conceptId, pool: pool === "all" ? undefined : pool as Q["pool"] } } })),
    enabled: !!conceptId,
  });
  const [editing, setEditing] = useState<{ id?: number; value: QIn } | null>(null);

  return (
    <div className="grid gap-5">
      <PageHeader title="Question bank" description="Quick checks draw unseen questions from the check pool first. Pilot-study questions are kept out of every other pool."
        actions={<>
          <Button asChild variant="outline" size="sm"><a href="/api/content/export/questions.csv"><DownloadIcon /> Export CSV</a></Button>
          <Button size="sm" disabled={!conceptId} onClick={() => setEditing({ value: { key: "", concept_id: conceptId, stem: "", options: ["", "", "", ""], correct_index: 0, explanation: "", difficulty: 2, pool: "check" } })}>
            <PlusIcon /> New question
          </Button>
        </>} />
      <div className="flex flex-wrap gap-2">
        <Select value={String(conceptId || "")} onValueChange={setConcept}>
          <SelectTrigger className="w-56" aria-label="Concept"><SelectValue placeholder="Concept" /></SelectTrigger>
          <SelectContent>{concepts.data?.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={pool} onValueChange={setPool}>
          <SelectTrigger className="w-44" aria-label="Pool"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All pools</SelectItem>
            {Object.entries(POOLS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
          </SelectContent>
        </Select>
        <span className="self-center text-sm text-muted-foreground">{qs.data?.length ?? 0} questions</span>
      </div>
      <div className="grid gap-3">
        {(qs.data ?? []).map((q) => (
          <button key={q.id} type="button" onClick={() => setEditing({ id: q.id, value: { key: q.key, concept_id: q.concept_id, stem: q.stem, options: q.options, correct_index: q.correct_index, explanation: q.explanation, difficulty: q.difficulty, pool: q.pool, form: q.form as QIn["form"], aid_id: q.aid_id } })}
            className="grid gap-2 rounded-lg border bg-card p-4 text-left hover:border-primary/60">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge variant="secondary">{POOLS[q.pool]}{q.form ? ` · form ${q.form}` : ""}</Badge>
              <span className="font-mono text-muted-foreground">{q.key}</span>
              <span className="text-muted-foreground">difficulty {q.difficulty}</span>
            </div>
            <div className="line-clamp-4 text-sm [&_p]:my-1 [&_pre]:my-1"><Markdown>{q.stem}</Markdown></div>
            <p className="text-sm"><span className="text-muted-foreground">Answer:</span> <span className="font-medium">{q.options[q.correct_index]}</span></p>
          </button>
        ))}
      </div>
      <QuestionDialog editing={editing} onClose={() => setEditing(null)} />
    </div>
  );
}

function QuestionDialog({ editing, onClose }: { editing: { id?: number; value: QIn } | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<QIn | null>(null);
  const [prev, setPrev] = useState(editing);
  if (editing !== prev) {
    setPrev(editing);
    setForm(editing?.value ?? null);
  }
  const save = useMutation({
    mutationFn: () => editing?.id
      ? unwrap(api.PUT("/api/questions/{question_id}", { params: { path: { question_id: editing.id } }, body: form! }))
      : unwrap(api.POST("/api/questions", { body: form! })),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["questions"] }); toast.success("Question saved"); onClose(); },
  });
  const submit = (e: FormEvent) => { e.preventDefault(); save.mutate(); };
  return (
    <Dialog open={!!editing} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{editing?.id ? "Edit question" : "New question"}</DialogTitle>
          <DialogDescription>Four options, one correct. Explain why the tempting wrong answer is wrong.</DialogDescription>
        </DialogHeader>
        {form ? (
          <form onSubmit={submit}>
            <FieldGroup>
              <div className="grid gap-4 sm:grid-cols-3">
                <Field><FieldLabel htmlFor="q-key">Key</FieldLabel><Input id="q-key" required pattern="[a-z0-9-]+" value={form.key} disabled={!!editing?.id} onChange={(e) => setForm({ ...form, key: e.target.value })} /></Field>
                <Field>
                  <FieldLabel>Pool</FieldLabel>
                  <Select value={form.pool} onValueChange={(v) => setForm({ ...form, pool: v as QIn["pool"] })}>
                    <SelectTrigger aria-label="Pool"><SelectValue /></SelectTrigger>
                    <SelectContent>{Object.entries(POOLS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                  </Select>
                </Field>
                <Field><FieldLabel htmlFor="q-diff">Difficulty (1–3)</FieldLabel><Input id="q-diff" type="number" min={1} max={3} value={form.difficulty ?? 2} onChange={(e) => setForm({ ...form, difficulty: Number(e.target.value) })} /></Field>
              </div>
              <Field><FieldLabel htmlFor="q-stem">Question (markdown)</FieldLabel><Textarea id="q-stem" rows={5} className="font-mono text-sm" required value={form.stem} onChange={(e) => setForm({ ...form, stem: e.target.value })} /></Field>
              {form.options.map((o, i) => (
                <Field key={i}>
                  <FieldLabel htmlFor={`q-opt-${i}`}>
                    Option {"ABCD"[i]}
                    <label className="ml-3 inline-flex items-center gap-1 text-xs font-normal">
                      <input type="radio" name="correct" checked={form.correct_index === i} onChange={() => setForm({ ...form, correct_index: i })} /> correct
                    </label>
                  </FieldLabel>
                  <Input id={`q-opt-${i}`} required value={o} onChange={(e) => setForm({ ...form, options: form.options.map((x, j) => (j === i ? e.target.value : x)) })} />
                </Field>
              ))}
              <Field><FieldLabel htmlFor="q-expl">Explanation</FieldLabel><Textarea id="q-expl" rows={3} required value={form.explanation} onChange={(e) => setForm({ ...form, explanation: e.target.value })} /></Field>
              {save.error ? <p role="alert" className="text-sm text-destructive">{save.error.message}</p> : null}
              <Button type="submit" disabled={save.isPending} className="justify-self-start">Save question</Button>
            </FieldGroup>
          </form>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
