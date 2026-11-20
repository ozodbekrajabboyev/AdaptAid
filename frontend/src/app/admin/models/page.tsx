"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ErrorBar, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { type ModelReport, useModelReport } from "@/lib/admin";

const fmt = (v: unknown, d = 3) => (typeof v === "number" ? v.toFixed(d) : v === null || v === undefined ? "–" : String(v));
const pctf = (v: unknown) => (typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "–");
const TT = { background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8 };
const AX = { fill: "var(--muted-foreground)", fontSize: 11 };

export default function ModelReportPage() {
  const [synthetic, setSynthetic] = useState(true);
  const report = useModelReport(synthetic);
  if (report.isPending) return <PageSkeleton />;
  if (report.error) return <p className="text-destructive">{report.error.message}</p>;
  const r = report.data;
  return (
    <div className="grid gap-6">
      <PageHeader title="Model report"
        description="Offline results come from the research scripts (public datasets and the learner simulator). Live results come from this platform's own logs." />
      <Offline offline={r.offline} />
      <section className="grid gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-heading text-xl font-bold">Live, from this platform</h2>
          <Label className="flex items-center gap-2 text-sm font-normal">
            <Switch checked={synthetic} onCheckedChange={setSynthetic} /> Include simulated demo students
          </Label>
        </div>
        <Live live={r.live} />
        <Current runs={r.latest_runs} config={r.config} />
      </section>
    </div>
  );
}

function Offline({ offline }: { offline: ModelReport["offline"] }) {
  const sim = offline.simulation as undefined | {
    policy_summary: { affinity_level: string; policy: string; auc_known: number; auc_known_sd: number; final_known: number; curve: number[] }[];
    paired_differences: { a: string; b: string; affinity_level: string; mean_diff: number; ci95: [number, number] }[];
    style_recovery: { style_case: string; final_style_cos: number; start_style_cos: number }[];
    checks: Record<string, boolean>;
    tuning: { adopted: boolean; rule: string };
  };
  const others = Object.entries(offline).filter(([k]) => k !== "simulation");
  if (!sim && !others.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Offline evaluation</CardTitle>
          <CardDescription>Not imported yet. Run <code>make research</code>, then <code>adaptaid import-research</code>.</CardDescription>
        </CardHeader>
      </Card>
    );
  }
  return (
    <section className="grid gap-4">
      <h2 className="font-heading text-xl font-bold">Offline evaluation</h2>
      {sim ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Adaptive vs course plan (simulated learners)</CardTitle>
              <CardDescription>Area under the &ldquo;share of concepts known&rdquo; curve, mean ± sd over reporting seeds, by how much format matching really matters.</CardDescription>
            </CardHeader>
            <CardContent className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={["none", "small", "large"].map((lvl) => {
                  const row: Record<string, number | string> = { level: lvl };
                  for (const p of ["static", "random", "no_style", "hybrid"]) {
                    const x = sim.policy_summary.find((s) => s.affinity_level === lvl && s.policy === p);
                    if (x) { row[p] = x.auc_known; row[`${p}_sd`] = x.auc_known_sd; }
                  }
                  return row;
                })}>
                  <CartesianGrid vertical={false} stroke="var(--border)" />
                  <XAxis dataKey="level" tick={AX} />
                  <YAxis tick={AX} domain={[0.2, "auto"]} />
                  <Tooltip contentStyle={TT} />
                  <Legend />
                  {(["static", "random", "no_style", "hybrid"] as const).map((p, i) => (
                    <Bar key={p} dataKey={p} fill={["var(--chart-5)", "var(--muted-foreground)", "var(--chart-4)", "var(--chart-1)"][i]}>
                      <ErrorBar dataKey={`${p}_sd`} width={4} stroke="var(--foreground)" />
                    </Bar>
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Paired differences (95% CI)</CardTitle>
              <CardDescription>Same simulated learners under both policies. Green: the interval excludes zero.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader><TableRow><TableHead>Comparison</TableHead><TableHead>Format effect</TableHead><TableHead className="text-right">Difference</TableHead><TableHead className="text-right">95% CI</TableHead></TableRow></TableHeader>
                <TableBody>
                  {sim.paired_differences.map((d) => (
                    <TableRow key={`${d.a}-${d.b}-${d.affinity_level}`}>
                      <TableCell>{d.a} − {d.b}</TableCell><TableCell>{d.affinity_level}</TableCell>
                      <TableCell className={`text-right font-mono tabular ${d.ci95[0] > 0 ? "text-success" : ""}`}>{d.mean_diff > 0 ? "+" : ""}{d.mean_diff.toFixed(4)}</TableCell>
                      <TableCell className="text-right font-mono text-xs tabular">[{d.ci95[0].toFixed(3)}, {d.ci95[1].toFixed(3)}]</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Learning curves (large format effect)</CardTitle>
              <CardDescription>Share of concepts truly known by simulated learners after each session.</CardDescription>
            </CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={(sim.policy_summary.find((s) => s.affinity_level === "large" && s.policy === "hybrid")?.curve ?? []).map((_, i) => {
                  const row: Record<string, number> = { session: i + 1 };
                  for (const p of ["hybrid", "static", "random"]) {
                    const c = sim.policy_summary.find((s) => s.affinity_level === "large" && s.policy === p)?.curve;
                    if (c) row[p] = c[i];
                  }
                  return row;
                })}>
                  <CartesianGrid vertical={false} stroke="var(--border)" />
                  <XAxis dataKey="session" tick={AX} />
                  <YAxis tick={AX} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
                  <Tooltip contentStyle={TT} formatter={(v) => `${(Number(v) * 100).toFixed(1)}%`} />
                  <Legend />
                  <Line dataKey="hybrid" stroke="var(--chart-1)" strokeWidth={2.5} dot={false} />
                  <Line dataKey="random" stroke="var(--muted-foreground)" strokeWidth={1.5} dot={false} />
                  <Line dataKey="static" stroke="var(--chart-5)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Does the learned style find the truth?</CardTitle>
              <CardDescription>Cosine between the learned and the true format preference, by questionnaire quality.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <Table>
                <TableHeader><TableRow><TableHead>Questionnaire</TableHead><TableHead>Learning from outcomes</TableHead><TableHead className="text-right">Start</TableHead><TableHead className="text-right">End</TableHead></TableRow></TableHeader>
                <TableBody>
                  {sim.style_recovery.map((s) => {
                    const [prior, mode] = s.style_case.split("/");
                    return (
                      <TableRow key={s.style_case}>
                        <TableCell className="capitalize">{prior}</TableCell><TableCell>{mode === "with_update" ? "on" : "off"}</TableCell>
                        <TableCell className="text-right font-mono tabular">{s.start_style_cos.toFixed(3)}</TableCell>
                        <TableCell className="text-right font-mono tabular">{s.final_style_cos.toFixed(3)}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
              <ul className="grid gap-1 text-sm">
                {Object.entries(sim.checks).map(([k, v]) => <li key={k}>{v ? "✓" : "✗"} {k.replaceAll("_", " ")}</li>)}
              </ul>
              <p className="text-xs text-muted-foreground">Weights: {sim.tuning.adopted ? "tuned weights adopted" : "blueprint weights kept"} ({sim.tuning.rule}).</p>
            </CardContent>
          </Card>
        </div>
      ) : null}
      {others.map(([kind, payload]) => <OfflineTable key={kind} kind={kind} payload={payload} />)}
    </section>
  );
}

function OfflineTable({ kind, payload }: { kind: string; payload: Record<string, unknown> }) {
  const title = { bkt_eval: "Knowledge tracing on ASSISTments 2009", risk: "At-risk classifier on OULAD", cf_offline: "Collaborative filtering on OULAD clicks", personas: "Personas on OULAD" }[kind] ?? kind;
  const rows = (payload.table ?? []) as Record<string, unknown>[];
  const cols = rows.length ? Object.keys(rows[0]) : [];
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        {payload.note ? <CardDescription>{String(payload.note)}</CardDescription> : null}
      </CardHeader>
      <CardContent className="overflow-x-auto">
        {rows.length ? (
          <Table>
            <TableHeader><TableRow>{cols.map((c) => <TableHead key={c}>{c.replaceAll("_", " ")}</TableHead>)}</TableRow></TableHeader>
            <TableBody>{rows.map((row, i) => <TableRow key={i}>{cols.map((c) => <TableCell key={c} className="font-mono text-xs tabular">{fmt(row[c])}</TableCell>)}</TableRow>)}</TableBody>
          </Table>
        ) : <pre className="text-xs">{JSON.stringify(payload, null, 1).slice(0, 1500)}</pre>}
      </CardContent>
    </Card>
  );
}

function Live({ live }: { live: ModelReport["live"] }) {
  const policies = Object.entries(live.policies);
  return (
    <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recommendation outcomes by policy</CardTitle>
          <CardDescription>{live.students} students, {live.aid_uses} aid sessions, {live.checked_uses} with a quick check.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Policy</TableHead><TableHead className="text-right">Lists</TableHead><TableHead className="text-right">Cards seen</TableHead><TableHead className="text-right">Opened</TableHead><TableHead className="text-right">Finished</TableHead><TableHead className="text-right">Mean gain</TableHead><TableHead className="text-right">Improved</TableHead></TableRow></TableHeader>
            <TableBody>
              {policies.map(([name, p]) => (
                <TableRow key={name}>
                  <TableCell className="font-medium">{name === "static" ? "course plan (control)" : name}</TableCell>
                  <TableCell className="text-right tabular">{p.lists}</TableCell>
                  <TableCell className="text-right tabular">{p.items_shown}</TableCell>
                  <TableCell className="text-right tabular">{pctf(p.ctr)}</TableCell>
                  <TableCell className="text-right tabular">{pctf(p.completion_rate)}</TableCell>
                  <TableCell className="text-right font-mono tabular">{fmt(p.mean_gain)}</TableCell>
                  <TableCell className="text-right tabular">{pctf(p.improved_share)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="mt-2 text-xs text-muted-foreground">Opened = share of shown cards that were opened. Gain = quick-check result minus what BKT expected at the student&apos;s level.</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">Lists by data phase</CardTitle><CardDescription>The hybrid switches weights as it learns about each student.</CardDescription></CardHeader>
        <CardContent className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={Object.entries(live.phases).map(([phase, n]) => ({ phase, n }))}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="phase" tick={AX} /><YAxis tick={AX} />
              <Tooltip contentStyle={TT} />
              <Bar dataKey="n" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}

function Current({ runs, config }: { runs: ModelReport["latest_runs"]; config: ModelReport["config"] }) {
  const p = runs.personas?.metrics as undefined | { k?: number; silhouette?: number; stability_ari?: number; silhouette_by_k?: Record<string, number>; sizes?: Record<string, number> };
  const cf = runs.cf?.metrics as undefined | Record<string, unknown>;
  const bkt = (runs.bkt?.metrics?.concepts ?? {}) as Record<string, Record<string, number | string>>;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader><CardTitle className="text-base">Current models</CardTitle></CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <p><strong>Personas:</strong> {p?.k ? `k = ${p.k}, silhouette ${fmt(p.silhouette)}, stability (ARI) ${fmt(p.stability_ari)}` : "not trained yet"}</p>
          {p?.silhouette_by_k ? <p className="text-xs text-muted-foreground">Silhouette by k: {Object.entries(p.silhouette_by_k).map(([k, v]) => `k=${k}: ${v}`).join(", ")}</p> : null}
          {p?.sizes ? <p className="text-xs text-muted-foreground">{Object.entries(p.sizes).map(([n, c]) => `${n} (${c})`).join(" · ")}</p> : null}
          <p><strong>Collaborative filtering:</strong> {cf?.kind ? `${String(cf.kind).toUpperCase()} on ${cf.interactions} interactions from ${cf.users} learners` : "not trained yet"}</p>
          <p><strong>Recommender weights</strong> (version {config.weights_version}, {config.weights.source ?? "custom"}):</p>
          <Table>
            <TableHeader><TableRow><TableHead>Phase</TableHead>{["need", "style", "level", "cf", "help"].map((s) => <TableHead key={s} className="text-right">{s}</TableHead>)}</TableRow></TableHeader>
            <TableBody>
              {Object.entries(config.weights.weights).map(([phase, w]) => (
                <TableRow key={phase}><TableCell>{phase}</TableCell>{["need", "style", "level", "cf", "help"].map((s) => <TableCell key={s} className="text-right font-mono tabular">{fmt(w[s], 2)}</TableCell>)}</TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">BKT parameters (last refit)</CardTitle>
          <CardDescription>Fitted per concept by bounded grid search on this platform&apos;s answers. In-sample AUC; the held-out AUC is in the offline report.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Concept</TableHead><TableHead className="text-right">Answers</TableHead><TableHead className="text-right">Prior</TableHead><TableHead className="text-right">Learn</TableHead><TableHead className="text-right">Guess</TableHead><TableHead className="text-right">Slip</TableHead><TableHead className="text-right">AUC</TableHead></TableRow></TableHeader>
            <TableBody>
              {Object.entries(bkt).map(([slug, c]) => (
                <TableRow key={slug}>
                  <TableCell>{slug}</TableCell><TableCell className="text-right tabular">{c.responses}</TableCell>
                  {["prior", "learn", "guess", "slip", "auc_in_sample"].map((k) => <TableCell key={k} className="text-right font-mono text-xs tabular">{fmt(c[k])}</TableCell>)}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
