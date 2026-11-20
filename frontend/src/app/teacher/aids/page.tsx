"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { DownloadIcon, PlusIcon, UploadIcon } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/app-shell";
import { AID_TYPES, AidTypeBadge } from "@/components/learning/aid-type";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, unwrap } from "@/lib/api/client";
import { useAids, useConcepts } from "@/lib/learning";
import { useQuery } from "@tanstack/react-query";

export default function AidLibraryPage() {
  const courses = useQuery({ queryKey: ["courses"], queryFn: () => unwrap(api.GET("/api/courses")) });
  const courseId = courses.data?.[0]?.id;
  const concepts = useConcepts(courseId);
  const [concept, setConcept] = useState("all");
  const [type, setType] = useState("all");
  const [q, setQ] = useState("");
  const aids = useAids({ concept_id: concept === "all" ? undefined : Number(concept), type: type === "all" ? undefined : type, q: q || undefined });
  const file = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();
  const upload = useMutation({
    mutationFn: async (f: File) => {
      const body = new FormData();
      body.append("file", f);
      const res = await fetch("/api/content/import/aids", { method: "POST", body });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Import failed");
      return res.json() as Promise<{ created: number; updated: number; errors: string[] }>;
    },
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["aids"] });
      if (r.errors.length) toast.warning(`Imported with ${r.errors.length} problem(s): ${r.errors[0]}`);
      else toast.success(`Imported: ${r.created} new, ${r.updated} updated`);
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <div className="grid gap-5">
      <PageHeader title="Aid library" description="The teaching aids the recommender chooses from. Archived aids stay in past records but are no longer recommended."
        actions={<>
          <Button asChild variant="outline" size="sm"><a href="/api/content/export/aids.csv"><DownloadIcon /> Export CSV</a></Button>
          <Button variant="outline" size="sm" onClick={() => file.current?.click()} disabled={upload.isPending}><UploadIcon /> Import CSV</Button>
          <input ref={file} type="file" accept=".csv,text/csv" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); e.target.value = ""; }} />
          <Button asChild size="sm"><Link href="/teacher/aids/new"><PlusIcon /> New aid</Link></Button>
        </>} />
      <div className="flex flex-wrap gap-2">
        <Input aria-label="Search aids" placeholder="Search" className="max-w-xs" value={q} onChange={(e) => setQ(e.target.value)} />
        <Select value={concept} onValueChange={setConcept}>
          <SelectTrigger className="w-48" aria-label="Concept"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All concepts</SelectItem>
            {concepts.data?.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={type} onValueChange={setType}>
          <SelectTrigger className="w-44" aria-label="Format"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All formats</SelectItem>
            {Object.entries(AID_TYPES).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div className="overflow-x-auto rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow><TableHead>Title</TableHead><TableHead>Format</TableHead><TableHead>Concept</TableHead><TableHead className="text-right">Level</TableHead><TableHead className="text-right">Order</TableHead><TableHead>Source</TableHead></TableRow>
          </TableHeader>
          <TableBody>
            {(aids.data ?? []).map((a) => (
              <TableRow key={a.id}>
                <TableCell className="max-w-80"><Link href={`/teacher/aids/${a.id}`} className="font-medium hover:underline">{a.title}</Link></TableCell>
                <TableCell><AidTypeBadge type={a.aid_type} /></TableCell>
                <TableCell>{a.concept_name}</TableCell>
                <TableCell className="text-right tabular">{a.difficulty}</TableCell>
                <TableCell className="text-right tabular">{a.default_order}</TableCell>
                <TableCell className="text-muted-foreground">{a.source}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
