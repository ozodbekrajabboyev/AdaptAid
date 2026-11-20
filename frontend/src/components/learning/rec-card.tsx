import { ClockIcon, CompassIcon } from "lucide-react";
import Link from "next/link";

import { AidTypeBadge } from "@/components/learning/aid-type";
import { Badge } from "@/components/ui/badge";
import type { RecItem } from "@/lib/learning";
import { cn } from "@/lib/utils";

export function RecCard({ item, featured }: { item: RecItem; featured?: boolean }) {
  const href = `/learn/${item.aid.id}?item=${item.id}`;
  return (
    <article
      className={cn(
        "group relative grid content-start gap-3 rounded-lg border bg-card p-4 transition-colors hover:border-primary/60",
        featured && "border-primary/50",
      )}
      data-testid="rec-card"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <AidTypeBadge type={item.aid.aid_type} />
        {item.is_explore ? (
          <Badge className="gap-1 bg-highlight text-highlight-foreground hover:bg-highlight">
            <CompassIcon className="size-3.5" aria-hidden />
            Trying something new
          </Badge>
        ) : item.match !== null && item.match !== undefined ? (
          <span className="font-mono text-sm font-bold text-primary tabular">{item.match}% match</span>
        ) : null}
      </div>
      <h3 className="font-heading text-base leading-snug font-bold">
        <Link href={href} className="after:absolute after:inset-0 focus-visible:outline-none">
          {item.aid.title}
        </Link>
      </h3>
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <ClockIcon className="size-3" aria-hidden />
          {item.aid.duration_min} min
        </span>
        <span>level {item.aid.difficulty}/5</span>
        <span className="truncate">{item.aid.source}</span>
      </p>
      <div className="rounded-md bg-muted p-2.5 text-sm leading-relaxed">
        <span className="mb-0.5 block text-[0.7rem] font-bold tracking-wider text-muted-foreground uppercase">
          Why this
        </span>
        {item.explanation}
      </div>
      {item.opened ? (
        <span className="text-xs text-muted-foreground">{item.completed ? "Finished" : "Opened"}</span>
      ) : null}
    </article>
  );
}
