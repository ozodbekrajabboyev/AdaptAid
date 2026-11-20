"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, unwrap, type Schemas } from "@/lib/api/client";

type Role = Schemas["AdminUser"]["role"];

export default function UsersPage() {
  const qc = useQueryClient();
  const [role, setRole] = useState<string>("all");
  const [q, setQ] = useState("");
  const [synthetic, setSynthetic] = useState(false);
  const users = useQuery({
    queryKey: ["admin", "users", role, q, synthetic],
    queryFn: () => unwrap(api.GET("/api/admin/users", { params: { query: { role: role === "all" ? undefined : (role as Role), q: q || undefined, include_synthetic: synthetic } } })),
  });
  const [form, setForm] = useState({ email: "", full_name: "", role: "teacher" as Role, password: "" });
  const create = useMutation({
    mutationFn: () => unwrap(api.POST("/api/admin/users", { body: form })),
    onSuccess: (u) => { toast.success(`Created ${u.email}`); setForm({ email: "", full_name: "", role: "teacher", password: "" }); qc.invalidateQueries({ queryKey: ["admin", "users"] }); },
  });
  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => unwrap(api.POST("/api/admin/users/{user_id}/active", { params: { path: { user_id: id } }, body: { active } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
    onError: (e) => toast.error(e.message),
  });
  const reset = useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) => unwrap(api.POST("/api/admin/users/{user_id}/password", { params: { path: { user_id: id } }, body: { password } })),
    onSuccess: () => toast.success("Password changed"),
    onError: (e) => toast.error(e.message),
  });
  const submit = (e: FormEvent) => { e.preventDefault(); create.mutate(); };

  return (
    <div className="grid gap-5">
      <PageHeader title="Users" description="Create teacher and administrator accounts, reset passwords, and deactivate accounts." />
      <div className="flex flex-wrap items-center gap-3">
        <Input aria-label="Search users" placeholder="Search name or email" className="max-w-xs" value={q} onChange={(e) => setQ(e.target.value)} />
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger className="w-40" aria-label="Role"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All roles</SelectItem><SelectItem value="student">Students</SelectItem>
            <SelectItem value="teacher">Teachers</SelectItem><SelectItem value="admin">Administrators</SelectItem>
          </SelectContent>
        </Select>
        <Label className="flex items-center gap-2 text-sm font-normal"><Checkbox checked={synthetic} onCheckedChange={(v) => setSynthetic(!!v)} /> Show simulated students</Label>
      </div>
      <div className="overflow-x-auto rounded-lg border bg-card">
        <Table>
          <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Email</TableHead><TableHead>Role</TableHead><TableHead>Last active</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {(users.data ?? []).map((u) => (
              <TableRow key={u.id} className={u.is_active ? "" : "opacity-60"}>
                <TableCell className="font-medium">{u.full_name}{u.is_synthetic ? <span className="ml-1 text-xs text-muted-foreground">(simulated)</span> : null}</TableCell>
                <TableCell>{u.email}</TableCell>
                <TableCell><Badge variant="secondary" className="capitalize">{u.role}</Badge></TableCell>
                <TableCell className="text-sm text-muted-foreground">{u.last_active_at ? new Date(u.last_active_at).toLocaleDateString() : "–"}</TableCell>
                <TableCell className="text-right whitespace-nowrap">
                  <Button variant="ghost" size="sm" onClick={() => {
                    const password = Math.random().toString(36).slice(2, 8) + Math.random().toString(36).slice(2, 8);
                    reset.mutate({ id: u.id, password }, { onSuccess: () => toast.message(`New password for ${u.email}: ${password}`, { duration: 20000 }) });
                  }}>Reset password</Button>
                  <Button variant="ghost" size="sm" onClick={() => toggle.mutate({ id: u.id, active: !u.is_active })}>{u.is_active ? "Deactivate" : "Activate"}</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Card className="max-w-2xl">
        <CardHeader><CardTitle className="text-base">Create an account</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
            <Field><FieldLabel htmlFor="nu-name">Full name</FieldLabel><Input id="nu-name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
            <Field><FieldLabel htmlFor="nu-email">Email</FieldLabel><Input id="nu-email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field>
              <FieldLabel>Role</FieldLabel>
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v as Role })}>
                <SelectTrigger aria-label="New account role"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="teacher">Teacher</SelectItem><SelectItem value="admin">Administrator</SelectItem><SelectItem value="student">Student</SelectItem></SelectContent>
              </Select>
            </Field>
            <Field><FieldLabel htmlFor="nu-pass">Temporary password</FieldLabel><Input id="nu-pass" type="text" minLength={8} required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
            {create.error ? <p role="alert" className="text-sm text-destructive sm:col-span-2">{create.error.message}</p> : null}
            <Button type="submit" className="justify-self-start" disabled={create.isPending}>Create account</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
