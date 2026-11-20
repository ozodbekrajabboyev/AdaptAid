"use client";

import Link from "next/link";
import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { ClassSwitcher } from "@/components/teacher/class-switcher";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { pct } from "@/lib/learning";
import { heatColor, RISK_STYLE, useAtRisk, useHeatmap, useOverview, useSelectedClass, useSuggestions } from "@/lib/teacher";
import { cn } from "@/lib/utils";

export default function TeacherOverview() {
  const [klass, select, loading] = useSelectedClass();
  const overview = useOverview(klass?.id);
  const heat = useHeatmap(klass?.id);
  const risk = useAtRisk(klass?.id);
  const sugg = useSuggestions(klass?.id);

  if (loading) return <PageSkeleton />;
  const o = overview.data;

  return (
    <div className="grid gap-6">
      <PageHeader title="Class overview"
        description={o ? `${o.class_name} · ${o.course_title}${o.updated_at ? ` · models updated ${new Date(o.updated_at).toLocaleString()}` : ""}` : "Mastery, risk and teaching-aid suggestions for your class."}
        actions={<ClassSwitcher current={klass} onSelect={select} />} />
      {!klass ? (
        <Card><CardContent className="py-10 text-center text-muted-foreground">Create a class and share its join code with students to see their progress here.</CardContent></Card>
      ) : !o ? <PageSkeleton /> : (
        <>
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-5" aria-label="Key figures">
            <Kpi label="Students" value={String(o.kpis.n_students)} sub={`${o.kpis.active_this_week} active this week`} />
            <Kpi label="Average mastery" value={pct(o.kpis.avg_mastery)} />
            <Kpi label="Aids used this week" value={String(o.kpis.aids_used_week)} />
            <Kpi label="Average gain per aid" value={o.kpis.avg_gain_week === null || o.kpis.avg_gain_week === undefined ? "–" : `${o.kpis.avg_gain_week > 0 ? "+" : ""}${pct(o.kpis.avg_gain_week)}`}
              sub="this week, vs expected" />
            <Kpi label="At risk" value={String(o.kpis.at_risk)} tone={o.kpis.at_risk ? "bad" : undefined} sub="high-risk students" />
          </section>

          <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
            <Card className="min-w-0 self-start">
              <CardHeader>
                <CardTitle className="text-base">Mastery heatmap</CardTitle>
                <CardDescription>Each cell is a student&apos;s estimated mastery of a concept. Click a name for details.</CardDescription>
              </CardHeader>
              <CardContent>
                {heat.data ? (
                  <div className="max-h-[78vh] overflow-auto rounded-md border" data-testid="heatmap">
                    <table className="w-full border-separate border-spacing-0.5 text-xs">
                      <thead className="sticky top-0 z-10 bg-card">
                        <tr>
                          <th className="sticky left-0 z-20 bg-card px-2 py-1.5 text-left font-normal text-muted-foreground">Student</th>
                          {heat.data.concepts.map((c) => (
                            <th key={c.id as number} className="h-24 px-0.5 align-bottom font-normal text-muted-foreground">
                              <span className="inline-block max-h-24 [writing-mode:vertical-rl] rotate-180 truncate">{String(c.name)}</span>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {heat.data.students.map((s, i) => (
                          <tr key={s.id}>
                            <td className="sticky left-0 z-10 bg-card px-2 py-1 whitespace-nowrap">
                              <Link href={`/teacher/students/${s.id}?class=${klass.id}`} className="hover:underline">{s.name}</Link>
                              {s.risk_level === "high" ? <span className="ml-1.5 inline-block size-2 rounded-full bg-destructive" aria-label="high risk" /> : null}
                            </td>
                            {heat.data.values[i].map((p, j) => (
                              <td key={j} className="h-6 min-w-8 rounded-sm text-center font-mono tabular" style={{ background: heatColor(p) }}
                                title={`${s.name} · ${String(heat.data.concepts[j].name)}: ${pct(p)}`}>
                                {Math.round(p * 100)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <PageSkeleton />}
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                  {[[0.1, "under 30"], [0.4, "30–59"], [0.7, "60–79"], [0.85, "80–94"], [0.97, "mastered"]].map(([p, l]) => (
                    <span key={String(l)} className="inline-flex items-center gap-1.5">
                      <span className="size-3 rounded-sm" style={{ background: heatColor(p as number) }} />{l}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div className="grid content-start gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Teaching aids for your next class</CardTitle>
                  <CardDescription>Concepts where many students are stuck (unlocked but below 60%), with aids that suit most of them and none of them badly.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4" data-testid="suggestions">
                  {sugg.data?.length ? sugg.data.map((c) => (
                    <div key={c.concept_id} className="grid gap-1.5 border-l-[3px] border-primary pl-3">
                      <p className="font-heading font-bold">{c.concept_name} · {Math.round(c.share_below * 100)}% of the class stuck</p>
                      {c.class_lean ? <p className="text-xs text-muted-foreground">Struggling students lean {c.class_lean}.</p> : null}
                      {c.aids.map((a, i) => (
                        <p key={a.aid_id} className="text-sm">
                          {i === 0 ? "Use " : "Or "}
                          <Link href={`/teacher/aids/${a.aid_id}`} className="font-bold hover:underline">{a.title}</Link>{" "}
                          <span className="text-muted-foreground">({a.format_label}{a.mean_gain !== null && a.mean_gain !== undefined && a.n_checked >= 5 ? `, average gain ${a.mean_gain > 0 ? "+" : ""}${pct(a.mean_gain)} over ${a.n_checked} uses` : ""})</span>
                        </p>
                      ))}
                      {c.alternatives.map((g) => (
                        <p key={g.aid_id} className="text-xs text-muted-foreground">
                          For {g.students.slice(0, 4).join(", ")}{g.students.length > 4 ? ` and ${g.students.length - 4} more` : ""}: assign <span className="font-medium text-foreground">{g.title}</span> ({g.format_label}).
                        </p>
                      ))}
                    </div>
                  )) : <p className="text-sm text-muted-foreground">No concept has many stuck students right now.</p>}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Students who may need help</CardTitle>
                  <CardDescription>Flags come with the reason, so you know what to talk about.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-2.5" data-testid="at-risk">
                  {risk.data?.length ? risk.data.slice(0, 8).map((r) => (
                    <Link key={r.id} href={`/teacher/students/${r.id}?class=${klass.id}`} className="grid gap-1 rounded-md border p-2.5 hover:border-primary/60">
                      <span className="flex items-center justify-between gap-2">
                        <span className="font-medium">{r.name}</span>
                        <Badge className={cn("capitalize", RISK_STYLE[r.level])}>{r.level}</Badge>
                      </span>
                      <span className="text-xs text-muted-foreground">{r.reasons.join(" · ")}</span>
                    </Link>
                  )) : <p className="text-sm text-muted-foreground">Nobody is flagged right now.</p>}
                </CardContent>
              </Card>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Where the class is stuck</CardTitle>
                <CardDescription>Stuck: the concept is unlocked but below 60%. Not reached: its prerequisites are not done yet.</CardDescription>
              </CardHeader>
              <CardContent className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={o.concepts.map((c) => ({ name: c.name, stuck: Math.round(c.share_below * 100), locked: Math.round(c.share_locked * 100) }))} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
                    <YAxis type="category" dataKey="name" width={150} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
                    <Tooltip formatter={(v, k) => [`${v}%`, k === "stuck" ? "stuck" : "not reached yet"]} contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8 }} />
                    <Legend formatter={(k) => (k === "stuck" ? "stuck" : "not reached yet")} />
                    <Bar dataKey="stuck" stackId="a" fill="var(--warning)" />
                    <Bar dataKey="locked" stackId="a" fill="var(--border)" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Learner personas</CardTitle>
                <CardDescription>Groups found by K-Means clustering on how students engage (refreshed nightly).</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-2.5">
                {o.personas.length ? o.personas.map((p) => (
                  <div key={p.label} className="grid grid-cols-[10rem_minmax(0,1fr)_2.5rem] items-center gap-3 text-sm">
                    <span className="truncate">{p.label}</span>
                    <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                      <div className="h-full rounded-full bg-chart-4" style={{ width: `${(p.count / o.kpis.n_students) * 100}%` }} />
                    </div>
                    <span className="text-right font-mono text-xs tabular">{p.count}</span>
                  </div>
                )) : <p className="text-sm text-muted-foreground">Personas appear once at least 20 students have used a few aids.</p>}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function Kpi({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "bad" }) {
  return (
    <div className="grid gap-0.5 rounded-lg border bg-card p-3.5">
      <span className="text-xs tracking-wide text-muted-foreground uppercase">{label}</span>
      <span className={cn("font-mono text-2xl font-bold tabular", tone === "bad" && "text-destructive")}>{value}</span>
      {sub ? <span className="text-xs text-muted-foreground">{sub}</span> : null}
    </div>
  );
}
