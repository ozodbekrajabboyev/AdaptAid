"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { AidForm } from "@/components/teacher/aid-form";
import { api, unwrap } from "@/lib/api/client";
import { useAid, useConcepts } from "@/lib/learning";

export default function EditAidPage() {
  const { aidId } = useParams<{ aidId: string }>();
  const aid = useAid(Number(aidId));
  const courses = useQuery({ queryKey: ["courses"], queryFn: () => unwrap(api.GET("/api/courses")) });
  const concepts = useConcepts(courses.data?.[0]?.id);
  if (!aid.data || !concepts.data) return <PageSkeleton />;
  const a = aid.data;
  return (
    <div className="grid gap-5">
      <PageHeader title="Edit teaching aid" description={a.title} />
      <AidForm aidId={a.id} concepts={concepts.data} initial={{
        slug: a.slug, title: a.title, description: a.description, concept_id: a.concept_id, aid_type: a.aid_type,
        delivery: a.delivery, url: a.url ?? null, body_md: a.body_md ?? null,
        component_key: (a.component_key ?? null) as "sorting-stepper" | "recursion-stack" | "bst-builder" | null,
        source: a.source, difficulty: a.difficulty, duration_min: a.duration_min, style_ar: a.style[0], style_si: a.style[1],
        style_vv: a.style[2], style_sg: a.style[3], interactivity: a.interactivity, default_order: a.default_order,
      }} />
    </div>
  );
}
