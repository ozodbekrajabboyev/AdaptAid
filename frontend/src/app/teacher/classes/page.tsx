"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, unwrap } from "@/lib/api/client";
import { useMyClasses } from "@/lib/teacher";

export default function ClassesPage() {
  const classes = useMyClasses();
  const courses = useQuery({ queryKey: ["courses"], queryFn: () => unwrap(api.GET("/api/courses")) });
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const create = useMutation({
    mutationFn: () => unwrap(api.POST("/api/classes", { body: { name, course_id: courses.data![0].id } })),
    onSuccess: (c) => { qc.invalidateQueries({ queryKey: ["classes"] }); setName(""); toast.success(`Created ${c.name}. Join code ${c.join_code}`); },
  });
  const submit = (e: FormEvent) => { e.preventDefault(); create.mutate(); };
  return (
    <div className="grid gap-5">
      <PageHeader title="Classes" description="Students join a class with its code, on the sign-up page or in their profile." />
      <div className="overflow-x-auto rounded-lg border bg-card">
        <Table>
          <TableHeader><TableRow><TableHead>Class</TableHead><TableHead>Course</TableHead><TableHead>Join code</TableHead><TableHead className="text-right">Students</TableHead></TableRow></TableHeader>
          <TableBody>
            {(classes.data ?? []).map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-medium">{c.name}</TableCell>
                <TableCell>{c.course_title}</TableCell>
                <TableCell className="font-mono">{c.join_code}</TableCell>
                <TableCell className="text-right tabular">{c.n_students}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Card className="max-w-lg">
        <CardHeader><CardTitle className="text-base">Create a class</CardTitle><CardDescription>For the course {courses.data?.[0]?.title ?? ""}.</CardDescription></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
            <Field className="min-w-56 flex-1"><FieldLabel htmlFor="class-name">Class name</FieldLabel>
              <Input id="class-name" required minLength={2} placeholder="CSE 3A, 2026" value={name} onChange={(e) => setName(e.target.value)} /></Field>
            <Button type="submit" disabled={create.isPending || !courses.data?.length}>Create class</Button>
          </form>
          {create.error ? <p role="alert" className="mt-2 text-sm text-destructive">{create.error.message}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
