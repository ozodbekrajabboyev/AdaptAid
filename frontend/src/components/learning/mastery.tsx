import { LockIcon } from "lucide-react";

import { band, pct } from "@/lib/learning";
import { cn } from "@/lib/utils";

const FILL = {
  mastered: "bg-success",
  good: "bg-primary",
  partial: "bg-warning",
  low: "bg-destructive/80",
} as const;

export function MasteryBar({ p, locked, className }: { p: number; locked?: boolean; className?: string }) {
  return (
    <div className={cn("h-2 overflow-hidden rounded-full bg-muted", className)} role="presentation">
      <div
        className={cn("h-full rounded-full transition-[width] duration-700", locked ? "bg-border" : FILL[band(p)])}
        style={{ width: `${Math.max(2, Math.round(p * 100))}%` }}
      />
    </div>
  );
}

export function MasteryRow({
  name,
  p,
  status,
}: {
  name: string;
  p: number;
  status: string;
}) {
  const locked = status === "locked";
  return (
    <div className="grid grid-cols-[minmax(0,8.5rem)_minmax(0,1fr)_3.5rem] items-center gap-3 text-sm">
      <span className={cn("truncate", locked && "text-muted-foreground")} title={name}>
        {name}
      </span>
      <MasteryBar p={p} locked={locked} />
      <span className="tabular text-right font-mono text-xs text-muted-foreground">
        {locked ? (
          <span className="inline-flex items-center gap-1">
            <LockIcon className="size-3" aria-hidden />
            <span className="sr-only">locked,</span>
            {pct(p)}
          </span>
        ) : (
          pct(p)
        )}
      </span>
    </div>
  );
}

export function MasteryLegend() {
  return (
    <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
      {(
        [
          ["low", "under 30%"],
          ["partial", "30–59%"],
          ["good", "60–94%"],
          ["mastered", "mastered (95%+)"],
        ] as const
      ).map(([b, label]) => (
        <span key={b} className="inline-flex items-center gap-1.5">
          <span className={cn("size-2.5 rounded-full", FILL[b])} />
          {label}
        </span>
      ))}
    </div>
  );
}
