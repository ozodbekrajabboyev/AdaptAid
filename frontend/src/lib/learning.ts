"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type Schemas } from "@/lib/api/client";

export type Summary = Schemas["SummaryOut"];
export type RecList = Schemas["RecListOut"];
export type RecItem = Schemas["RecItemOut"];
export type AidDetail = Schemas["AidDetail"];
export type AidSummary = Schemas["AidSummary"];
export type Attempt = Schemas["AttemptOut"];
export type AnswerResult = Schemas["AnswerOut"];
export type FinishResult = Schemas["FinishOut"];
export type AidType = AidSummary["aid_type"];
export type AttemptKind = Attempt["kind"];

export const qk = {
  summary: ["me", "summary"] as const,
  onboarding: ["onboarding"] as const,
  recs: (concept?: number | null) => ["recs", concept ?? "home"] as const,
  path: ["me", "path"] as const,
  progress: ["me", "progress"] as const,
  history: ["me", "history"] as const,
  aid: (id: number) => ["aid", id] as const,
  aids: (filters: Record<string, unknown>) => ["aids", filters] as const,
  concepts: (courseId: number) => ["concepts", courseId] as const,
};

export function useSummary() {
  return useQuery({ queryKey: qk.summary, queryFn: () => unwrap(api.GET("/api/me/summary")) });
}

export function useOnboarding() {
  return useQuery({ queryKey: qk.onboarding, queryFn: () => unwrap(api.GET("/api/onboarding/status")) });
}

export function useRecs(conceptId?: number | null) {
  return useQuery({
    queryKey: qk.recs(conceptId),
    queryFn: () =>
      unwrap(api.GET("/api/recommendations/current", { params: { query: conceptId ? { concept_id: conceptId } : {} } })),
  });
}

export function useRefreshRecs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (conceptId?: number | null) =>
      unwrap(api.POST("/api/recommendations/refresh", { body: { concept_id: conceptId ?? null } })),
    onSuccess: (list, conceptId) => qc.setQueryData(qk.recs(conceptId), list),
  });
}

export function usePath() {
  return useQuery({ queryKey: qk.path, queryFn: () => unwrap(api.GET("/api/me/path")) });
}

export function useProgress() {
  return useQuery({ queryKey: qk.progress, queryFn: () => unwrap(api.GET("/api/me/progress")) });
}

export function useHistory() {
  return useQuery({ queryKey: qk.history, queryFn: () => unwrap(api.GET("/api/me/history")) });
}

export function useAid(id: number) {
  return useQuery({
    queryKey: qk.aid(id),
    queryFn: () => unwrap(api.GET("/api/aids/{aid_id}", { params: { path: { aid_id: id } } })),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useAids(filters: { concept_id?: number; type?: string; q?: string }) {
  return useQuery({
    queryKey: qk.aids(filters),
    queryFn: () => unwrap(api.GET("/api/aids", { params: { query: filters } })),
  });
}

export function useConcepts(courseId: number | undefined) {
  return useQuery({
    queryKey: qk.concepts(courseId ?? 0),
    queryFn: () => unwrap(api.GET("/api/courses/{course_id}/concepts", { params: { path: { course_id: courseId! } } })),
    enabled: !!courseId,
  });
}

/** Invalidate everything that changes after a quiz or an aid session. */
export function useInvalidateLearning() {
  const qc = useQueryClient();
  return () => {
    // The server regenerated the list: drop the old one so it is never shown again.
    qc.removeQueries({ queryKey: ["recs"] });
    for (const key of [qk.summary, qk.path, qk.progress, qk.history, qk.onboarding]) {
      qc.invalidateQueries({ queryKey: key });
    }
  };
}

export function pct(p: number): string {
  return `${Math.round(p * 100)}%`;
}

export type MasteryBand = "mastered" | "good" | "partial" | "low";

export function band(p: number): MasteryBand {
  if (p >= 0.95) return "mastered";
  if (p >= 0.6) return "good";
  if (p >= 0.3) return "partial";
  return "low";
}
