"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { AidTypeBadge } from "@/components/learning/aid-type";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { pct, useHistory, useProgress } from "@/lib/learning";

const day = (iso: string) => new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });

export default function ProgressPage() {
  const progress = useProgress();
  const history = useHistory();
  const [concept, setConcept] = useState<string>("");
  const series = progress.data?.series ?? [];
  const selected = series.find((s) => String(s.concept_id) === concept) ?? series[0];
  const points = useMemo(
    () => selected?.points.map((p, i) => ({ n: i + 1, p: Math.round(p.p * 100), t: p.t })) ?? [],
    [selected],
  );

  if (progress.isPending) return <PageSkeleton />;
  const daily = (progress.data?.daily ?? []).map((d) => ({ date: day(d.date), mastery: Math.round(d.mean_mastery * 100), answers: d.answers }));

  return (
    <div className="grid gap-5">
      <PageHeader title="Progress" description="How your estimated mastery has changed, and the aids you have used." />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Average mastery across all concepts</CardTitle>
          <CardDescription>One point per day you answered questions.</CardDescription>
        </CardHeader>
        <CardContent className="h-64">
          {daily.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={daily} margin={{ left: -12, right: 12, top: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="date" tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} />
                <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} />
                <Tooltip formatter={(v) => [`${v}%`, "Mastery"]} contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8 }} />
                <Line type="monotone" dataKey="mastery" stroke="var(--chart-1)" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : <p className="py-16 text-center text-muted-foreground">No answers yet.</p>}
        </CardContent>
      </Card>

      {series.length ? (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
            <div className="grid gap-1">
              <CardTitle className="text-base">One concept, answer by answer</CardTitle>
              <CardDescription>Every answer moves the estimate: up when right, down when wrong.</CardDescription>
            </div>
            <Select value={String(selected?.concept_id ?? "")} onValueChange={setConcept}>
              <SelectTrigger className="w-48" aria-label="Concept"><SelectValue /></SelectTrigger>
              <SelectContent>{series.map((s) => <SelectItem key={s.concept_id} value={String(s.concept_id)}>{s.name}</SelectItem>)}</SelectContent>
            </Select>
          </CardHeader>
          <CardContent className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={points} margin={{ left: -12, right: 12, top: 8 }}>
                <CartesianGrid vertical={false} stroke="var(--border)" />
                <XAxis dataKey="n" tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} label={{ value: "answer", position: "insideBottomRight", offset: -2, fill: "var(--muted-foreground)", fontSize: 11 }} />
                <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} />
                <Tooltip formatter={(v) => [`${v}%`, "Mastery"]} labelFormatter={(n) => `Answer ${n}`} contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8 }} />
                <Line type="stepAfter" dataKey="p" stroke="var(--chart-2)" strokeWidth={2} dot={{ r: 2.5 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent teaching aids</CardTitle>
          <CardDescription>Gain is how much better your quick check went than expected for your level at the time.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Aid</TableHead><TableHead>Concept</TableHead><TableHead>Date</TableHead>
                <TableHead className="text-right">Rating</TableHead><TableHead className="text-right">Gain</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(history.data ?? []).map((h) => (
                <TableRow key={h.use_id}>
                  <TableCell className="max-w-72">
                    <Link href={`/learn/${h.aid_id}?source=direct`} className="grid gap-1 hover:underline">
                      <span className="truncate font-medium">{h.title}</span>
                      <AidTypeBadge type={h.aid_type as never} className="justify-self-start" />
                    </Link>
                  </TableCell>
                  <TableCell>{h.concept_name}</TableCell>
                  <TableCell className="whitespace-nowrap">{day(h.opened_at)}</TableCell>
                  <TableCell className="text-right tabular">{h.rating ?? "–"}</TableCell>
                  <TableCell className="text-right font-mono tabular">
                    {h.gain === null || h.gain === undefined ? (h.check_status === "no_check" ? "no check" : "–")
                      : <span className={h.gain > 0 ? "text-success" : h.gain < 0 ? "text-destructive" : ""}>{h.gain > 0 ? "+" : ""}{pct(h.gain)}</span>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
