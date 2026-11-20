"use client";

import { ShuffleIcon } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

import { StepControls, useStepper } from "./stepper";

type Algo = "bubble" | "insertion" | "selection";
type Frame = { a: number[]; compare: number[]; swapped: boolean; sortedFrom: number; sortedTo: number; text: string; comps: number; swaps: number };

function frames(input: number[], algo: Algo): Frame[] {
  const a = [...input];
  const out: Frame[] = [];
  let comps = 0;
  let swaps = 0;
  const push = (compare: number[], swapped: boolean, sortedFrom: number, sortedTo: number, text: string) =>
    out.push({ a: [...a], compare, swapped, sortedFrom, sortedTo, text, comps, swaps });
  const n = a.length;
  push([], false, n, n, "Start: an unsorted list.");
  if (algo === "bubble") {
    for (let end = n - 1; end > 0; end--) {
      let any = false;
      for (let j = 0; j < end; j++) {
        comps++;
        if (a[j] > a[j + 1]) {
          [a[j], a[j + 1]] = [a[j + 1], a[j]];
          swaps++;
          any = true;
          push([j, j + 1], true, end + 1, n, `${a[j + 1]} > ${a[j]}, so swap them.`);
        } else push([j, j + 1], false, end + 1, n, `${a[j]} ≤ ${a[j + 1]}: already in order.`);
      }
      push([], false, end, n, `Pass done: ${a[end]} has bubbled to its final place.`);
      if (!any) {
        push([], false, 0, n, "No swaps in this pass, so the list is sorted. Bubble sort can stop early.");
        return out;
      }
    }
  } else if (algo === "insertion") {
    for (let i = 1; i < n; i++) {
      const key = a[i];
      let j = i - 1;
      push([i], false, 0, i, `Take ${key} and insert it into the sorted part on the left.`);
      while (j >= 0) {
        comps++;
        if (a[j] > key) {
          a[j + 1] = a[j];
          a[j] = key;
          swaps++;
          push([j, j + 1], true, 0, i + 1, `${a[j + 1]} > ${key}: shift it right.`);
          j--;
        } else {
          push([j, j + 1], false, 0, i + 1, `${a[j]} ≤ ${key}: ${key} stops here.`);
          break;
        }
      }
    }
  } else {
    for (let i = 0; i < n - 1; i++) {
      let min = i;
      for (let j = i + 1; j < n; j++) {
        comps++;
        if (a[j] < a[min]) min = j;
        push([min, j], false, 0, i, `Smallest so far in the unsorted part: ${a[min]}.`);
      }
      if (min !== i) {
        [a[i], a[min]] = [a[min], a[i]];
        swaps++;
      }
      push([i], min !== i, 0, i + 1, `Put ${a[i]} at position ${i}. It is final.`);
    }
  }
  push([], false, 0, n, `Sorted with ${comps} comparisons and ${swaps} ${algo === "insertion" ? "shifts" : "swaps"}.`);
  return out;
}

function randomList(n = 8) {
  return Array.from({ length: n }, () => 5 + Math.floor(Math.random() * 90));
}

export function SortingStepper() {
  const [algo, setAlgo] = useState<Algo>("bubble");
  const [input, setInput] = useState<number[]>([42, 17, 88, 5, 63, 29, 71, 12]);
  const fs = useMemo(() => frames(input, algo), [input, algo]);
  const { step, setStep, playing, setPlaying } = useStepper(fs.length, 650);
  const f = fs[Math.min(step, fs.length - 1)];
  const max = Math.max(...input);

  return (
    <div className="grid gap-4" data-testid="sorting-stepper">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs value={algo} onValueChange={(v) => { setAlgo(v as Algo); setStep(() => 0); setPlaying(false); }}>
          <TabsList>
            <TabsTrigger value="bubble">Bubble</TabsTrigger>
            <TabsTrigger value="insertion">Insertion</TabsTrigger>
            <TabsTrigger value="selection">Selection</TabsTrigger>
          </TabsList>
        </Tabs>
        <Button variant="outline" size="sm" onClick={() => { setInput(randomList()); setStep(() => 0); setPlaying(false); }}>
          <ShuffleIcon /> New list
        </Button>
      </div>
      <div className="flex h-52 items-end gap-1.5 rounded-lg border bg-card p-3" aria-label={`List: ${f.a.join(", ")}`} role="img">
        {f.a.map((v, i) => {
          const sorted = i >= f.sortedFrom && i < f.sortedTo;
          const active = f.compare.includes(i);
          return (
            <div key={i} className="flex flex-1 flex-col items-center gap-1">
              <div
                className={cn(
                  "w-full rounded-t-md transition-all duration-300",
                  active ? (f.swapped ? "bg-warning" : "bg-primary") : sorted ? "bg-success/80" : "bg-muted-foreground/35",
                )}
                style={{ height: `${(v / max) * 150}px` }}
              />
              <span className="font-mono text-xs tabular">{v}</span>
            </div>
          );
        })}
      </div>
      <p className="min-h-12 rounded-md bg-muted p-3 text-sm" aria-live="polite">{f.text}</p>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <StepControls step={step} total={fs.length} playing={playing} setStep={setStep} setPlaying={setPlaying} />
        <span className="font-mono text-xs text-muted-foreground tabular">
          comparisons {f.comps} · {algo === "insertion" ? "shifts" : "swaps"} {f.swaps}
        </span>
      </div>
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-primary" />comparing</span>
        <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-warning" />swapped / shifted</span>
        <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-sm bg-success/80" />in final place</span>
      </div>
    </div>
  );
}
