"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { AidTypeBadge } from "@/components/learning/aid-type";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, unwrap } from "@/lib/api/client";
import { pct } from "@/lib/learning";
import { cn } from "@/lib/utils";

export default function EffectivenessPage() {
  const rows = useQuery({ queryKey: ["teacher", "effectiveness"], queryFn: () => unwrap(api.GET("/api/teacher/aid-effectiveness")) });
  if (rows.isPending) return <PageSkeleton />;
  const max = Math.max(0.01, ...(rows.data ?? []).map((r) => Math.abs(r.smoothed_gain)));
  return (
    <div className="grid gap-5">
      <PageHeader title="Aid effectiveness"
        description="Gain is how much better students did on the quick check after an aid than Bayesian Knowledge Tracing expected for their level. Aids with few uses are pulled toward the average, so a lucky first use does not top the table." />
      <div className="overflow-x-auto rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Aid</TableHead><TableHead>Concept</TableHead><TableHead className="w-56">Smoothed gain</TableHead>
              <TableHead className="text-right">Checked uses</TableHead><TableHead className="text-right">Improved</TableHead>
              <TableHead className="text-right">Finished</TableHead><TableHead className="text-right">Rating</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(rows.data ?? []).map((r) => (
              <TableRow key={r.aid_id}>
                <TableCell className="max-w-80">
                  <Link href={`/teacher/aids/${r.aid_id}`} className="block truncate font-medium hover:underline">{r.title}</Link>
                  <AidTypeBadge type={r.aid_type as never} />
                </TableCell>
                <TableCell>{r.concept_name}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className="relative h-2 flex-1 rounded-full bg-muted">
                      <div className="absolute top-0 left-1/2 h-2 w-px bg-muted-foreground/50" />
                      <div className={cn("absolute top-0 h-2 rounded-full", r.smoothed_gain >= 0 ? "left-1/2 bg-success" : "right-1/2 bg-destructive")}
                        style={{ width: `${(Math.abs(r.smoothed_gain) / max) * 50}%` }} />
                    </div>
                    <span className="w-12 text-right font-mono text-xs tabular">{r.smoothed_gain > 0 ? "+" : ""}{pct(r.smoothed_gain)}</span>
                  </div>
                </TableCell>
                <TableCell className="text-right tabular">{r.n_checked}</TableCell>
                <TableCell className="text-right tabular">{r.improved_share === null || r.improved_share === undefined ? "–" : pct(r.improved_share)}</TableCell>
                <TableCell className="text-right tabular">{r.completion_rate === null || r.completion_rate === undefined ? "–" : pct(r.completion_rate)}</TableCell>
                <TableCell className="text-right tabular">{r.mean_rating?.toFixed(1) ?? "–"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
