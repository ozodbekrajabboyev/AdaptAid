"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { roleHome, useRegister } from "@/lib/auth";

export function RegisterForm() {
  const params = useSearchParams();
  const router = useRouter();
  const register = useRegister();
  const [role, setRole] = useState<"student" | "teacher">("student");
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    join_code: params.get("code") ?? "",
    invite_code: "",
  });
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  function submit(e: FormEvent) {
    e.preventDefault();
    register.mutate(
      {
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        role,
        join_code: role === "student" && form.join_code ? form.join_code : null,
        invite_code: role === "teacher" ? form.invite_code : null,
      },
      { onSuccess: (me) => router.replace(me.role === "student" ? "/onboarding" : roleHome(me.role)) },
    );
  }

  return (
    <form onSubmit={submit} className="grid gap-5" noValidate>
      <Tabs value={role} onValueChange={(v) => setRole(v as "student" | "teacher")}>
        <TabsList className="w-full">
          <TabsTrigger value="student">I&apos;m a student</TabsTrigger>
          <TabsTrigger value="teacher">I&apos;m a teacher</TabsTrigger>
        </TabsList>
      </Tabs>
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor="full_name">Full name</FieldLabel>
          <Input id="full_name" autoComplete="name" required value={form.full_name} onChange={set("full_name")} />
        </Field>
        <Field>
          <FieldLabel htmlFor="email">Email</FieldLabel>
          <Input id="email" type="email" autoComplete="email" required value={form.email} onChange={set("email")} />
        </Field>
        <Field>
          <FieldLabel htmlFor="password">Password</FieldLabel>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={form.password}
            onChange={set("password")}
          />
          <FieldDescription>At least 8 characters.</FieldDescription>
        </Field>
        {role === "student" ? (
          <Field>
            <FieldLabel htmlFor="join_code">Class code</FieldLabel>
            <Input
              id="join_code"
              autoCapitalize="characters"
              placeholder="e.g. K7P2QM"
              value={form.join_code}
              onChange={set("join_code")}
            />
            <FieldDescription>Optional. You can also join a class later.</FieldDescription>
          </Field>
        ) : (
          <Field>
            <FieldLabel htmlFor="invite_code">Teacher invite code</FieldLabel>
            <Input id="invite_code" required value={form.invite_code} onChange={set("invite_code")} />
            <FieldDescription>Ask the platform administrator for this code.</FieldDescription>
          </Field>
        )}
      </FieldGroup>
      {register.error ? (
        <p role="alert" className="text-sm text-destructive">
          {register.error.message}
        </p>
      ) : null}
      <Button type="submit" size="lg" disabled={register.isPending}>
        {register.isPending ? "Creating account…" : "Create account"}
      </Button>
      <p className="text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="text-primary underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
