"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api, unwrap, type Schemas } from "@/lib/api/client";

export type ClassOut = Schemas["ClassOut"];

const KEY = "adaptaid.teacher.class";

export function useMyClasses() {
  return useQuery({ queryKey: ["classes", "mine"], queryFn: () => unwrap(api.GET("/api/classes/mine")) });
}

/** The class the teacher is looking at, remembered across pages. */
export function useSelectedClass(): [ClassOut | undefined, (id: number) => void, boolean] {
  const classes = useMyClasses();
  const [id, setId] = useState<number | null>(null);

  useEffect(() => {
    try {
      const saved = Number(window.localStorage.getItem(KEY));
      // eslint-disable-next-line react-hooks/set-state-in-effect -- read once from browser storage after mount
      if (saved) setId(saved);
    } catch {
      /* storage unavailable: fall back to the first class */
    }
  }, []);

  const select = (next: number) => {
    setId(next);
    try {
      window.localStorage.setItem(KEY, String(next));
    } catch {
      /* ignore */
    }
  };
  const list = classes.data ?? [];
  const current = list.find((c) => c.id === id) ?? list[0];
  return [current, select, classes.isPending];
}

export function useOverview(classId?: number) {
  return useQuery({
    queryKey: ["teacher", "overview", classId],
    queryFn: () => unwrap(api.GET("/api/teacher/classes/{class_id}/overview", { params: { path: { class_id: classId! } } })),
    enabled: !!classId,
  });
}

export function useHeatmap(classId?: number) {
  return useQuery({
    queryKey: ["teacher", "heatmap", classId],
    queryFn: () => unwrap(api.GET("/api/teacher/classes/{class_id}/heatmap", { params: { path: { class_id: classId! } } })),
    enabled: !!classId,
  });
}

export function useAtRisk(classId?: number) {
  return useQuery({
    queryKey: ["teacher", "risk", classId],
    queryFn: () => unwrap(api.GET("/api/teacher/classes/{class_id}/at-risk", { params: { path: { class_id: classId! } } })),
    enabled: !!classId,
  });
}

export function useSuggestions(classId?: number) {
  return useQuery({
    queryKey: ["teacher", "suggestions", classId],
    queryFn: () => unwrap(api.GET("/api/teacher/classes/{class_id}/suggestions", { params: { path: { class_id: classId! } } })),
    enabled: !!classId,
  });
}

export const RISK_STYLE: Record<string, string> = {
  high: "bg-destructive/15 text-destructive",
  medium: "bg-warning/20 text-warning",
  low: "bg-success/15 text-success",
};

/** Background colour for a mastery cell, from red (low) to green (mastered). */
export function heatColor(p: number): string {
  if (p >= 0.95) return "color-mix(in oklab, var(--success) 55%, var(--card))";
  if (p >= 0.8) return "color-mix(in oklab, var(--success) 32%, var(--card))";
  if (p >= 0.6) return "color-mix(in oklab, var(--success) 15%, var(--card))";
  if (p >= 0.3) return "color-mix(in oklab, var(--warning) 32%, var(--card))";
  return "color-mix(in oklab, var(--destructive) 34%, var(--card))";
}
