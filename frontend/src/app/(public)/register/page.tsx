import type { Metadata } from "next";
import { Suspense } from "react";

import { RegisterForm } from "./register-form";

export const metadata: Metadata = { title: "Create an account" };

export default function RegisterPage() {
  return (
    <div className="mx-auto grid w-full max-w-md gap-6 pt-10 md:pt-16">
      <div className="grid gap-1">
        <h1 className="font-heading text-3xl font-bold tracking-tight">Create an account</h1>
        <p className="text-muted-foreground">Students join with the class code from their teacher.</p>
      </div>
      <Suspense>
        <RegisterForm />
      </Suspense>
    </div>
  );
}
