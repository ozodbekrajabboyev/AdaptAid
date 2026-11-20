"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { AID_TYPES } from "@/components/learning/aid-type";
import { Markdown } from "@/components/markdown";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { api, unwrap, type Schemas } from "@/lib/api/client";

type AidIn = Schemas["AidIn"];
type AidType = AidIn["aid_type"];

// The tagging rubric (content/dsa/RUBRIC.md): default style vector and interactivity per aid type.
const RUBRIC: Record<AidType, { style: [number, number, number, number]; interactivity: AidIn["interactivity"] }> = {
  video: { style: [-0.3, 0, 0.6, 0.5], interactivity: "expositive" },
  animation: { style: [0.3, 0.2, 0.9, 0.6], interactivity: "mixed" },
  interactive: { style: [0.9, 0.5, 0.8, 0.4], interactivity: "active" },
  notes: { style: [-0.5, 0, -0.8, 0.6], interactivity: "expositive" },
  worked_example: { style: [0.1, 0.8, -0.2, 0.8], interactivity: "expositive" },
  cheat_sheet: { style: [0, 0.2, -0.4, -0.8], interactivity: "expositive" },
  concept_map: { style: [-0.2, -0.5, 0.8, -0.8], interactivity: "expositive" },
  practice: { style: [0.9, 0.6, -0.3, 0.3], interactivity: "active" },
  article: { style: [-0.4, -0.4, -0.7, 0.3], interactivity: "expositive" },
};
const DIMS = [["style_ar", "Active", "Reflective"], ["style_si", "Sensing", "Intuitive"], ["style_vv", "Visual", "Verbal"], ["style_sg", "Sequential", "Global"]] as const;

export function AidForm({ initial, aidId, concepts }: { initial: AidIn; aidId?: number; concepts: Schemas["ConceptOut"][] }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [form, setForm] = useState<AidIn>(initial);
  const set = <K extends keyof AidIn>(k: K, v: AidIn[K]) => setForm((f) => ({ ...f, [k]: v }));

  const save = useMutation({
    mutationFn: () => aidId
      ? unwrap(api.PUT("/api/aids/{aid_id}", { params: { path: { aid_id: aidId } }, body: form }))
      : unwrap(api.POST("/api/aids", { body: form })),
    onSuccess: (a) => {
      qc.invalidateQueries({ queryKey: ["aids"] });
      qc.invalidateQueries({ queryKey: ["aid", a.id] });
      toast.success(aidId ? "Teaching aid saved" : "Teaching aid created");
      router.push("/teacher/aids");
    },
  });
  const archive = useMutation({
    mutationFn: () => unwrap(api.DELETE("/api/aids/{aid_id}", { params: { path: { aid_id: aidId! } } })),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["aids"] }); toast.success("Teaching aid archived"); router.push("/teacher/aids"); },
  });

  function applyRubric(type: AidType) {
    const r = RUBRIC[type];
    setForm((f) => ({ ...f, aid_type: type, style_ar: r.style[0], style_si: r.style[1], style_vv: r.style[2], style_sg: r.style[3], interactivity: r.interactivity }));
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    save.mutate();
  }

  return (
    <form onSubmit={submit} className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
      <Card>
        <CardHeader><CardTitle className="text-base">Content</CardTitle></CardHeader>
        <CardContent>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="title">Title</FieldLabel>
              <Input id="title" required value={form.title} onChange={(e) => set("title", e.target.value)} />
            </Field>
            <Field>
              <FieldLabel htmlFor="slug">Short id</FieldLabel>
              <Input id="slug" required pattern="[a-z0-9-]+" value={form.slug} disabled={!!aidId}
                onChange={(e) => set("slug", e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-"))} />
              <FieldDescription>Lowercase letters, numbers and dashes, e.g. recursion-tower-of-hanoi.</FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="description">Card description</FieldLabel>
              <Textarea id="description" required rows={2} value={form.description} onChange={(e) => set("description", e.target.value)} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field>
                <FieldLabel>Concept</FieldLabel>
                <Select value={String(form.concept_id)} onValueChange={(v) => set("concept_id", Number(v))}>
                  <SelectTrigger aria-label="Concept"><SelectValue /></SelectTrigger>
                  <SelectContent>{concepts.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel>Format</FieldLabel>
                <Select value={form.aid_type} onValueChange={(v) => applyRubric(v as AidType)}>
                  <SelectTrigger aria-label="Format"><SelectValue /></SelectTrigger>
                  <SelectContent>{Object.entries(AID_TYPES).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
            </div>
            <Field>
              <FieldLabel>Delivered as</FieldLabel>
              <Select value={form.delivery} onValueChange={(v) => set("delivery", v as AidIn["delivery"])}>
                <SelectTrigger aria-label="Delivered as"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="native_md">Written here (markdown)</SelectItem>
                  <SelectItem value="external_url">Link to another site</SelectItem>
                  <SelectItem value="interactive_component">Built-in interactive</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            {form.delivery === "external_url" ? (
              <Field>
                <FieldLabel htmlFor="url">Link</FieldLabel>
                <Input id="url" type="url" required placeholder="https://" value={form.url ?? ""} onChange={(e) => set("url", e.target.value)} />
              </Field>
            ) : form.delivery === "interactive_component" ? (
              <Field>
                <FieldLabel>Component</FieldLabel>
                <Select value={form.component_key ?? ""} onValueChange={(v) => set("component_key", v as AidIn["component_key"])}>
                  <SelectTrigger aria-label="Component"><SelectValue placeholder="Choose" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sorting-stepper">Sorting stepper</SelectItem>
                    <SelectItem value="recursion-stack">Recursion call stack</SelectItem>
                    <SelectItem value="bst-builder">BST builder</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
            ) : (
              <Tabs defaultValue="write">
                <TabsList><TabsTrigger value="write">Write</TabsTrigger><TabsTrigger value="preview">Preview</TabsTrigger></TabsList>
                <TabsContent value="write">
                  <Textarea aria-label="Content in markdown" rows={14} className="font-mono text-sm" value={form.body_md ?? ""}
                    onChange={(e) => set("body_md", e.target.value)} placeholder={"# Heading\n\nText, ```python code``` and ```mermaid diagrams```."} />
                </TabsContent>
                <TabsContent value="preview" className="rounded-md border p-4"><Markdown>{form.body_md || "_Nothing yet._"}</Markdown></TabsContent>
              </Tabs>
            )}
            <Field>
              <FieldLabel htmlFor="source">Source</FieldLabel>
              <Input id="source" value={form.source ?? ""} onChange={(e) => set("source", e.target.value)} />
            </Field>
          </FieldGroup>
        </CardContent>
      </Card>

      <div className="grid content-start gap-5">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Learning-style tags</CardTitle>
            <CardDescription>Start from the rubric default for this format, then adjust only for a clear reason.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {DIMS.map(([key, left, right]) => (
              <div key={key} className="grid gap-1.5">
                <div className="flex justify-between text-xs"><span>{left}</span><span className="font-mono tabular">{(form[key] as number).toFixed(1)}</span><span>{right}</span></div>
                <Slider min={-1} max={1} step={0.1} value={[-(form[key] as number)]} aria-label={`${left} to ${right}`}
                  onValueChange={([v]) => set(key, Math.round(-v * 10) / 10)} />
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" className="justify-self-start" onClick={() => applyRubric(form.aid_type)}>Reset to rubric default</Button>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="grid gap-4 pt-6 sm:grid-cols-3">
            <Field>
              <FieldLabel htmlFor="difficulty">Level (1–5)</FieldLabel>
              <Input id="difficulty" type="number" min={1} max={5} value={form.difficulty ?? 2} onChange={(e) => set("difficulty", Number(e.target.value))} />
            </Field>
            <Field>
              <FieldLabel htmlFor="duration">Minutes</FieldLabel>
              <Input id="duration" type="number" min={1} max={240} value={form.duration_min ?? 10} onChange={(e) => set("duration_min", Number(e.target.value))} />
            </Field>
            <Field>
              <FieldLabel htmlFor="order">Course order</FieldLabel>
              <Input id="order" type="number" min={0} value={form.default_order ?? 0} onChange={(e) => set("default_order", Number(e.target.value))} />
            </Field>
          </CardContent>
        </Card>
        {save.error ? <p role="alert" className="text-sm text-destructive">{save.error.message}</p> : null}
        <div className="flex flex-wrap gap-2">
          <Button type="submit" size="lg" disabled={save.isPending}>{aidId ? "Save changes" : "Create teaching aid"}</Button>
          {aidId ? <Button type="button" variant="destructive" onClick={() => archive.mutate()} disabled={archive.isPending}>Archive</Button> : null}
        </div>
      </div>
    </form>
  );
}

export function emptyAid(conceptId: number): AidIn {
  const r = RUBRIC.notes;
  return {
    slug: "", title: "", description: "", concept_id: conceptId, aid_type: "notes", delivery: "native_md", url: null,
    body_md: "", component_key: null, source: "AdaptAid", difficulty: 2, duration_min: 10,
    style_ar: r.style[0], style_si: r.style[1], style_vv: r.style[2], style_sg: r.style[3], interactivity: r.interactivity, default_order: 9,
  };
}
