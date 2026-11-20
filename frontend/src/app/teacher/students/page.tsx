"use client";

import Link from "next/link";
import { useState } from "react";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { MasteryBar } from "@/components/learning/mastery";
import { ClassSwitcher } from "@/components/teacher/class-switcher";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { pct } from "@/lib/learning";
import { RISK_STYLE, useHeatmap, useSelectedClass } from "@/lib/teacher";
import { cn } from "@/lib/utils";

export default function StudentsPage() {
  const [klass, select, loading] = useSelectedClass();
  const heat = useHeatmap(klass?.id);
  const [q, setQ] = useState("");
  if (loading) return <PageSkeleton />;
  const rows = (heat.data?.students ?? []).map((s, i) => {
    const vals = heat.data!.values[i];
    return { ...s, mean: vals.reduce((a, b) => a + b, 0) / vals.length, mastered: vals.filter((v) => v >= 0.95).length };
  }).filter((s) => s.name.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="grid gap-5">
      <PageHeader title="Students" description="Everyone in the class, with mastery, persona and risk." actions={<ClassSwitcher current={klass} onSelect={select} />} />
      <Input aria-label="Search students" placeholder="Search by name" className="max-w-sm" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="overflow-x-auto rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Student</TableHead><TableHead className="w-56">Average mastery</TableHead>
              <TableHead className="text-right">Mastered</TableHead><TableHead>Persona</TableHead><TableHead>Risk</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((s) => (
              <TableRow key={s.id}>
                <TableCell>
                  <Link href={`/teacher/students/${s.id}?class=${klass?.id}`} className="font-medium hover:underline">{s.name}</Link>
                  {s.synthetic ? <span className="ml-2 text-xs text-muted-foreground">(simulated)</span> : null}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2"><MasteryBar p={s.mean} className="flex-1" /><span className="w-10 text-right font-mono text-xs tabular">{pct(s.mean)}</span></div>
                </TableCell>
                <TableCell className="text-right font-mono tabular">{s.mastered}/{heat.data!.concepts.length}</TableCell>
                <TableCell>{s.persona ?? <span className="text-muted-foreground">–</span>}</TableCell>
                <TableCell><Badge className={cn("capitalize", RISK_STYLE[s.risk_level])}>{s.risk_level}</Badge></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
