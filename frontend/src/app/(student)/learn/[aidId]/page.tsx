import { Suspense } from "react";

import { PageSkeleton } from "@/components/app-shell";

import { AidView } from "./aid-view";

export default function LearnPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <AidView />
    </Suspense>
  );
}
