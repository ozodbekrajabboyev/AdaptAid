import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <div className="mx-auto grid w-full max-w-sm gap-6 pt-10 md:pt-16">
      <div className="grid gap-1">
        <h1 className="font-heading text-3xl font-bold tracking-tight">Sign in</h1>
        <p className="text-muted-foreground">Welcome back. Pick up where you left off.</p>
      </div>
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  );
}
