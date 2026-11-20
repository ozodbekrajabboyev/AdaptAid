"use client";

import { PageHeader } from "@/components/app-shell";
import { useMe } from "@/lib/auth";

export default function StudentHome() {
  const { data: me } = useMe();
  return <PageHeader title={`Welcome, ${me?.full_name.split(" ")[0] ?? ""}`} description="Your learning dashboard." />;
}
