"use client";

import { AppShell } from "@/components/app-shell";
import { STUDENT_NAV } from "@/lib/nav";

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell nav={STUDENT_NAV} allowed={["student"]} areaLabel="Student">
      {children}
    </AppShell>
  );
}
