"use client";

import { CopyIcon } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { type ClassOut, useMyClasses } from "@/lib/teacher";

export function ClassSwitcher({ current, onSelect }: { current?: ClassOut; onSelect: (id: number) => void }) {
  const classes = useMyClasses();
  if (!classes.data?.length) {
    return (
      <Button asChild variant="outline" size="sm">
        <Link href="/teacher/classes">Create your first class</Link>
      </Button>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select value={current ? String(current.id) : undefined} onValueChange={(v) => onSelect(Number(v))}>
        <SelectTrigger className="w-56" aria-label="Class"><SelectValue placeholder="Choose a class" /></SelectTrigger>
        <SelectContent>
          {classes.data.map((c) => (
            <SelectItem key={c.id} value={String(c.id)}>{c.name} · {c.n_students} students</SelectItem>
          ))}
        </SelectContent>
      </Select>
      {current ? (
        <Button variant="ghost" size="sm" className="font-mono"
          onClick={() => {
            navigator.clipboard.writeText(current.join_code).then(
              () => toast.success("Join code copied"),
              () => toast.message(`Join code: ${current.join_code}`),
            );
          }}>
          <CopyIcon /> {current.join_code}
        </Button>
      ) : null}
    </div>
  );
}
