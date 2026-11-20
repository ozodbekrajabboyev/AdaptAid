"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeftIcon } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { AidTypeBadge } from "@/components/learning/aid-type";
import { MasteryRow } from "@/components/learning/mastery";
import { StyleProfile } from "@/components/learning/style-profile";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, unwrap, type Schemas } from "@/lib/api/client";
import { pct } from "@/lib/learning";
import { RISK_STYLE } from "@/lib/teacher";
import { cn } from "@/lib/utils";

type Detail = {
  id: number; name: string; email: string; synthetic: boolean; persona: string | null;
  summary: Schemas["SummaryOut"]; history: Schemas["HistoryItem"][]; progress: Schemas["ProgressOut"];
  risk: { level: string; score: number; reasons: string[] } | null; features: Record<string, number>;
};

export default function StudentDetailPage() {
  return <Suspense fallback={<PageSkeleton />}><StudentDetail /></Suspense>;
}

function StudentDetail() {
  const { studentId } = useParams<{ studentId: string }>();
  const classId = Number(useSearchParams().get("class"));
  const q = useQuery({
    queryKey: ["teacher", "student", classId, studentId],
    queryFn: async () => (await unwrap(api.GET("/api/teacher/classes/{class_id}/students/{student_id}", {
      params: { path: { class_id: classId, student_id: Number(studentId) } },
    }))) as unknown as Detail,
    enabled: !!classId,
  });
  if (!classId) return <p className="text-muted-foreground">Open a student from the class overview.</p>;
  if (q.isPending) return <PageSkeleton />;
  if (q.error) return <p className="text-destructive">{q.error.message}</p>;
  const d = q.data;
  const s = d.summary;
  const daily = d.progress.daily.map((x) => ({ date: new Date(x.date).toLocaleDateString(undefined, { day: "numeric", month: "short" }), m: Math.round(x.mean_mastery * 100) }));

  return (
    <div className="grid gap-5">
      <Link href="/teacher" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeftIcon className="size-4" /> Class overview</Link>
      <PageHeader title={d.name} description={`${d.email}${d.persona ? ` · ${d.persona}` : ""} · ${s.n_uses} aids used, ${s.n_checks} quick checks`}
        actions={d.risk ? <Badge className={cn("capitalize", RISK_STYLE[d.risk.level])}>{d.risk.level} risk</Badge> : undefined} />
      {d.risk?.reasons.length ? (
        <Card className="border-warning/50"><CardContent className="pt-6 text-sm"><strong>Why flagged:</strong> {d.risk.reasons.join(" · ")}</CardContent></Card>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Mastery</CardTitle></CardHeader>
          <CardContent className="grid gap-2.5">{s.mastery.map((m) => <MasteryRow key={m.concept_id} name={m.name} p={m.p} status={m.status} />)}</CardContent>
        </Card>
        <div className="grid content-start gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Learning preferences</CardTitle>
              <CardDescription>Questionnaire (hollow) and learned from {s.style.n_updates} quick checks (filled).</CardDescription>
            </CardHeader>
            <CardContent><StyleProfile style={s.style} /></CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-base">Average mastery over time</CardTitle></CardHeader>
            <CardContent className="h-44">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={daily} margin={{ left: -16, right: 8, top: 4 }}>
                  <XAxis dataKey="date" tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
                  <Tooltip formatter={(v) => [`${v}%`, "mastery"]} contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8 }} />
                  <Line dataKey="m" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-base">Recent teaching aids</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Aid</TableHead><TableHead>Concept</TableHead><TableHead>Date</TableHead><TableHead className="text-right">Rating</TableHead><TableHead className="text-right">Gain</TableHead></TableRow></TableHeader>
            <TableBody>
              {d.history.map((h) => (
                <TableRow key={h.use_id}>
                  <TableCell className="max-w-72"><span className="block truncate">{h.title}</span><AidTypeBadge type={h.aid_type as never} /></TableCell>
                  <TableCell>{h.concept_name}</TableCell>
                  <TableCell className="whitespace-nowrap">{new Date(h.opened_at).toLocaleDateString()}</TableCell>
                  <TableCell className="text-right tabular">{h.rating ?? "–"}</TableCell>
                  <TableCell className="text-right font-mono tabular">{h.gain === null || h.gain === undefined ? "–" : `${h.gain > 0 ? "+" : ""}${pct(h.gain)}`}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
