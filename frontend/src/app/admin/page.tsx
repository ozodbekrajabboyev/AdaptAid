"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { STATUS_STYLE, useRuns } from "@/lib/admin";
import { api, unwrap } from "@/lib/api/client";
import { cn } from "@/lib/utils";

export default function AdminHome() {
  const users = useQuery({ queryKey: ["admin", "users", "all"], queryFn: () => unwrap(api.GET("/api/admin/users", { params: { query: { include_synthetic: true } } })) });
  const runs = useRuns();
  const study = useQuery({ queryKey: ["admin", "study"], queryFn: () => unwrap(api.GET("/api/admin/settings/study")) });
  if (users.isPending) return <PageSkeleton />;
  const list = users.data ?? [];
  const count = (role: string, synthetic = false) => list.filter((u) => u.role === role && u.is_synthetic === synthetic).length;
  const latest = new Map<string, NonNullable<typeof runs.data>[number]>();
  for (const r of runs.data ?? []) if (!latest.has(r.kind)) latest.set(r.kind, r);

  return (
    <div className="grid gap-5">
      <PageHeader title="Administration" description="Accounts, models, background jobs and the pilot study." />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Students" value={count("student")} sub={`${count("student", true)} simulated demo students`} href="/admin/users" />
        <Stat label="Teachers" value={count("teacher")} href="/admin/users" />
        <Stat label="Administrators" value={count("admin")} href="/admin/users" />
        <Stat label="Pilot study" value={study.data?.active ? "Running" : "Off"} sub={study.data?.frozen ? "parameters frozen" : undefined} href="/admin/study" />
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Latest model runs</CardTitle>
          <CardDescription>Nightly jobs rebuild personas, risk flags, aid statistics, the collaborative-filtering model and BKT parameters.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-2">
          {["personas", "risk", "aid_stats", "cf", "bkt"].map((k) => {
            const r = latest.get(k);
            return (
              <div key={k} className="flex flex-wrap items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
                <span className="font-mono">{k}</span>
                {r ? (
                  <span className="flex items-center gap-2">
                    <Badge className={cn(STATUS_STYLE[r.status])}>{r.status}</Badge>
                    <span className="text-xs text-muted-foreground">{r.finished_at ? new Date(r.finished_at).toLocaleString() : "running"}</span>
                  </span>
                ) : <span className="text-xs text-muted-foreground">never run</span>}
              </div>
            );
          })}
          <Link href="/admin/jobs" className="text-sm text-primary hover:underline">Run jobs now</Link>
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value, sub, href }: { label: string; value: number | string; sub?: string; href: string }) {
  return (
    <Link href={href} className="grid gap-0.5 rounded-lg border bg-card p-4 hover:border-primary/60">
      <span className="text-xs tracking-wide text-muted-foreground uppercase">{label}</span>
      <span className="font-mono text-2xl font-bold tabular">{value}</span>
      {sub ? <span className="text-xs text-muted-foreground">{sub}</span> : null}
    </Link>
  );
}
