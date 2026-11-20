"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";

export const STATUS_STYLE: Record<string, string> = {
  success: "bg-success/15 text-success",
  running: "bg-primary/15 text-primary",
  failed: "bg-destructive/15 text-destructive",
  skipped: "bg-muted text-muted-foreground",
};

export function useRuns(poll = false) {
  return useQuery({
    queryKey: ["admin", "jobs"],
    queryFn: () => unwrap(api.GET("/api/admin/jobs")),
    refetchInterval: (q) => (poll || q.state.data?.some((r) => r.status === "running") ? 2500 : false),
  });
}

export function useRunJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (kind: "all" | "personas" | "risk" | "aid_stats" | "cf" | "bkt") =>
      unwrap(api.POST("/api/admin/jobs/{kind}", { params: { path: { kind } } })),
    onSuccess: () => setTimeout(() => qc.invalidateQueries({ queryKey: ["admin", "jobs"] }), 400),
  });
}

/** Loose type for the model report: offline payloads are research JSON files. */
export type ModelReport = {
  offline: Record<string, Record<string, unknown>>;
  live: {
    include_synthetic: boolean;
    students: number;
    aid_uses: number;
    checked_uses: number;
    mean_gain: number | null;
    phases: Record<string, number>;
    policies: Record<string, { lists: number; items_shown: number; ctr: number | null; completion_rate: number | null; checked: number; mean_gain: number | null; improved_share: number | null }>;
  };
  latest_runs: Record<string, { status: string; finished_at: string | null; metrics: Record<string, unknown> }>;
  config: { weights: { weights: Record<string, Record<string, number>>; source?: string }; weights_version: number; style_update: Record<string, number> };
};

export function useModelReport(includeSynthetic: boolean) {
  return useQuery({
    queryKey: ["admin", "model-report", includeSynthetic],
    queryFn: async () => (await unwrap(api.GET("/api/admin/model-report", { params: { query: { include_synthetic: includeSynthetic } } }))) as unknown as ModelReport,
  });
}
