"use client";

import { AppShell } from "@/components/app-shell";
import { TEACHER_NAV } from "@/lib/nav";

export default function TeacherLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell nav={TEACHER_NAV} allowed={["teacher", "admin"]} areaLabel="Teacher">
      {children}
    </AppShell>
  );
}
