"use client";

import { SearchIcon } from "lucide-react";
import Link from "next/link";
import { useDeferredValue, useState } from "react";

import { PageHeader } from "@/components/app-shell";
import { AID_TYPES, AidTypeBadge } from "@/components/learning/aid-type";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAids, useConcepts, useSummary } from "@/lib/learning";

export default function LibraryPage() {
  const summary = useSummary();
  const concepts = useConcepts(summary.data?.course_id);
  const [concept, setConcept] = useState("all");
  const [type, setType] = useState("all");
  const [q, setQ] = useState("");
  const query = useDeferredValue(q);
  const aids = useAids({
    concept_id: concept === "all" ? undefined : Number(concept),
    type: type === "all" ? undefined : type,
    q: query || undefined,
  });

  return (
    <div className="grid gap-5">
      <PageHeader title="Library" description="Every teaching aid in the course. Your recommendations pick from these for you, but you can open any of them." />
      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-56 flex-1">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input aria-label="Search aids" placeholder="Search titles and descriptions" className="pl-8" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
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
      {aids.isPending ? (
        <div className="grid gap-3 md:grid-cols-2">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-28" />)}</div>
      ) : aids.data?.length ? (
        <div className="grid gap-3 md:grid-cols-2">
          {aids.data.map((a) => (
            <Link key={a.id} href={`/learn/${a.id}?source=library`}
              className="grid content-start gap-2 rounded-lg border bg-card p-4 transition-colors hover:border-primary/60">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <AidTypeBadge type={a.aid_type} />
                <span className="text-xs text-muted-foreground">{a.concept_name}</span>
              </div>
              <span className="font-heading font-bold">{a.title}</span>
              <span className="line-clamp-2 text-sm text-muted-foreground">{a.description}</span>
              <span className="font-mono text-xs text-muted-foreground">{a.duration_min} min · level {a.difficulty}/5 · {a.source}</span>
            </Link>
          ))}
        </div>
      ) : (
        <p className="rounded-lg border bg-card p-8 text-center text-muted-foreground">No aids match these filters.</p>
      )}
    </div>
  );
}
