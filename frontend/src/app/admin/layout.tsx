"use client";

import { AppShell } from "@/components/app-shell";
import { ADMIN_NAV } from "@/lib/nav";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell nav={ADMIN_NAV} allowed={["admin"]} areaLabel="Administrator">
      {children}
    </AppShell>
  );
}
