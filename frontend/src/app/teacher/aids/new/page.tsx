"use client";

import { useQuery } from "@tanstack/react-query";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { AidForm, emptyAid } from "@/components/teacher/aid-form";
import { api, unwrap } from "@/lib/api/client";
import { useConcepts } from "@/lib/learning";

export default function NewAidPage() {
  const courses = useQuery({ queryKey: ["courses"], queryFn: () => unwrap(api.GET("/api/courses")) });
  const concepts = useConcepts(courses.data?.[0]?.id);
  if (!concepts.data) return <PageSkeleton />;
  return (
    <div className="grid gap-5">
      <PageHeader title="New teaching aid" description="Add a resource and tag it so the recommender knows who it suits." />
      <AidForm initial={emptyAid(concepts.data[0].id)} concepts={concepts.data} />
    </div>
  );
}
