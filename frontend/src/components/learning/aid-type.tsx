import {
  BookOpenTextIcon,
  CirclePlayIcon,
  FileTextIcon,
  ListChecksIcon,
  type LucideIcon,
  MousePointerClickIcon,
  NetworkIcon,
  NotebookPenIcon,
  ScrollTextIcon,
  SparklesIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { AidType } from "@/lib/learning";
import { cn } from "@/lib/utils";

export const AID_TYPES: Record<AidType, { label: string; icon: LucideIcon }> = {
  video: { label: "Video", icon: CirclePlayIcon },
  animation: { label: "Animation", icon: SparklesIcon },
  interactive: { label: "Interactive", icon: MousePointerClickIcon },
  notes: { label: "Notes", icon: NotebookPenIcon },
  worked_example: { label: "Worked example", icon: ListChecksIcon },
  cheat_sheet: { label: "Cheat sheet", icon: ScrollTextIcon },
  concept_map: { label: "Concept map", icon: NetworkIcon },
  practice: { label: "Practice", icon: BookOpenTextIcon },
  article: { label: "Article", icon: FileTextIcon },
};

export function AidTypeBadge({ type, className }: { type: AidType; className?: string }) {
  const t = AID_TYPES[type];
  return (
    <Badge variant="secondary" className={cn("gap-1 font-normal", className)}>
      <t.icon className="size-3.5" aria-hidden />
      {t.label}
    </Badge>
  );
}
