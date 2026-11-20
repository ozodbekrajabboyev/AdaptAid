import Link from "next/link";

import { cn } from "@/lib/utils";

export function Brand({ className, href = "/" }: { className?: string; href?: string }) {
  return (
    <Link href={href} className={cn("font-heading text-lg font-bold tracking-tight", className)}>
      Adapt<span className="text-primary">Aid</span>
    </Link>
  );
}
