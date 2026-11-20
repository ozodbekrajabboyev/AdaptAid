"use client";

import { PlayIcon } from "lucide-react";

import { PageHeader } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { STATUS_STYLE, useRunJob, useRuns } from "@/lib/admin";
import { cn } from "@/lib/utils";

const JOBS = [
  ["all", "Everything, in order"],
  ["personas", "Learner personas (K-Means)"],
  ["risk", "Risk flags"],
  ["aid_stats", "Aid statistics"],
  ["cf", "Collaborative filtering model"],
  ["bkt", "BKT parameter refit"],
] as const;

function summarise(kind: string, m: Record<string, unknown>): string {
  if (typeof m.status === "string") return m.status;
  if (kind === "personas") return `k=${m.k}, silhouette ${m.silhouette}, stability ${m.stability_ari}`;
  if (kind === "risk") return `levels ${JSON.stringify(m.levels)}`;
  if (kind === "aid_stats") return `${m.aids} aids, ${m.checked} checked uses, mean gain ${m.global_mean_gain}`;
  if (kind === "cf") return `${m.kind}: ${m.interactions} interactions, ${m.users} learners, ${m.items} aids`;
  if (kind === "bkt") {
    const c = (m.concepts ?? {}) as Record<string, { status?: string }>;
    const fitted = Object.values(c).filter((x) => !x.status).length;
    return `${fitted} of ${Object.keys(c).length} concepts refitted`;
  }
  return "";
}

export default function JobsPage() {
  const runs = useRuns();
  const run = useRunJob();
  const busy = runs.data?.some((r) => r.status === "running");
  return (
    <div className="grid gap-5">
      <PageHeader title="Jobs" description="Jobs run every night. Run them now after loading new data or before a demo." />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Run now</CardTitle>
          <CardDescription>{busy ? "A job is running. This page updates by itself." : "Jobs run in the background; results appear below."}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {JOBS.map(([k, label]) => (
            <Button key={k} variant={k === "all" ? "default" : "outline"} size="sm" disabled={run.isPending} onClick={() => run.mutate(k)}>
              <PlayIcon /> {label}
            </Button>
          ))}
        </CardContent>
      </Card>
      <div className="overflow-x-auto rounded-lg border bg-card">
        <Table>
          <TableHeader><TableRow><TableHead>Job</TableHead><TableHead>Status</TableHead><TableHead>Triggered by</TableHead><TableHead>Finished</TableHead><TableHead>Result</TableHead></TableRow></TableHeader>
          <TableBody>
            {(runs.data ?? []).map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-mono">{r.kind}</TableCell>
                <TableCell><Badge className={cn(STATUS_STYLE[r.status])}>{r.status}</Badge></TableCell>
                <TableCell>{r.triggered_by}</TableCell>
                <TableCell className="whitespace-nowrap text-sm">{r.finished_at ? new Date(r.finished_at).toLocaleString() : "…"}</TableCell>
                <TableCell className="max-w-md text-sm text-muted-foreground">{r.status === "failed" ? r.notes.split("\n")[0] : summarise(r.kind, r.metrics)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
