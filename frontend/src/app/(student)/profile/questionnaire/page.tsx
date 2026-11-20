"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/app-shell";
import { QuestionnaireStep } from "@/components/learning/questionnaire";
import { useInvalidateLearning } from "@/lib/learning";

export default function RetakeQuestionnaire() {
  const router = useRouter();
  const invalidate = useInvalidateLearning();
  return (
    <div className="mx-auto grid max-w-2xl gap-5">
      <PageHeader title="Retake the questionnaire"
        description="Your answers replace your starting profile. What AdaptAid has learned from your quick checks starts again from this new point." />
      <QuestionnaireStep continueLabel="Back to my profile" onDone={() => { invalidate(); router.push("/profile"); }} />
    </div>
  );
}
