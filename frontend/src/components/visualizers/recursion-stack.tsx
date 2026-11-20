"use client";

import { useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

import { StepControls, useStepper } from "./stepper";

type Fn = "factorial" | "fib" | "digit_sum";
type Frame = { label: string; waiting?: string };
type Snap = { stack: Frame[]; text: string; result?: number; returning?: number };

const CODE: Record<Fn, string> = {
  factorial: "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n - 1)",
  fib: "def fib(n):\n    if n <= 1:\n        return n\n    return fib(n - 1) + fib(n - 2)",
  digit_sum: "def digit_sum(n):\n    if n < 10:\n        return n\n    return n % 10 + digit_sum(n // 10)",
};
const LIMITS: Record<Fn, [number, number]> = { factorial: [0, 7], fib: [0, 5], digit_sum: [0, 99999] };

function trace(fn: Fn, n: number): Snap[] {
  const snaps: Snap[] = [];
  const stack: Frame[] = [];
  const snap = (text: string, extra: Partial<Snap> = {}) => snaps.push({ stack: stack.map((f) => ({ ...f })), text, ...extra });

  function run(x: number): number {
    stack.push({ label: `${fn}(${x})` });
    snap(`Call ${fn}(${x}): a new frame is pushed onto the stack.`);
    let value: number;
    if (fn === "factorial") {
      if (x === 0) {
        value = 1;
        snap(`${fn}(0) is the base case: return 1 without another call.`);
      } else {
        stack[stack.length - 1].waiting = `waiting for factorial(${x - 1})`;
        const r = run(x - 1);
        value = x * r;
        stack[stack.length - 1].waiting = undefined;
        snap(`Back in ${fn}(${x}): ${x} × ${r} = ${value}.`);
      }
    } else if (fn === "fib") {
      if (x <= 1) {
        value = x;
        snap(`${fn}(${x}) is a base case: return ${x}.`);
      } else {
        stack[stack.length - 1].waiting = `waiting for fib(${x - 1})`;
        const a = run(x - 1);
        stack[stack.length - 1].waiting = `has fib(${x - 1}) = ${a}, waiting for fib(${x - 2})`;
        const b = run(x - 2);
        value = a + b;
        stack[stack.length - 1].waiting = undefined;
        snap(`Back in ${fn}(${x}): ${a} + ${b} = ${value}.`);
      }
    } else {
      if (x < 10) {
        value = x;
        snap(`${x} has one digit: base case, return ${x}.`);
      } else {
        stack[stack.length - 1].waiting = `waiting for digit_sum(${Math.floor(x / 10)})`;
        const r = run(Math.floor(x / 10));
        value = (x % 10) + r;
        stack[stack.length - 1].waiting = undefined;
        snap(`Back in ${fn}(${x}): ${x % 10} + ${r} = ${value}.`);
      }
    }
    stack.pop();
    snap(`${fn}(${x}) returns ${value}; its frame is popped.`, { returning: value });
    return value;
  }

  snap(`Ready to call ${fn}(${n}).`);
  const result = run(n);
  snaps.push({ stack: [], text: `Done. ${fn}(${n}) = ${result}. The stack is empty again.`, result });
  return snaps;
}

export function RecursionStack() {
  const [fn, setFn] = useState<Fn>("factorial");
  const [n, setN] = useState(4);
  const snaps = useMemo(() => trace(fn, n), [fn, n]);
  const { step, setStep, playing, setPlaying } = useStepper(snaps.length, 900);
  const s = snaps[Math.min(step, snaps.length - 1)];
  const deepest = Math.max(...snaps.map((x) => x.stack.length));

  function choose(next: Fn) {
    setFn(next);
    setN(next === "digit_sum" ? 4096 : next === "fib" ? 4 : 4);
    setStep(() => 0);
    setPlaying(false);
  }

  return (
    <div className="grid gap-4" data-testid="recursion-stack">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <Tabs value={fn} onValueChange={(v) => choose(v as Fn)}>
          <TabsList>
            <TabsTrigger value="factorial">factorial</TabsTrigger>
            <TabsTrigger value="fib">fib</TabsTrigger>
            <TabsTrigger value="digit_sum">digit_sum</TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="grid gap-1">
          <Label htmlFor="rec-n" className="text-xs">n</Label>
          <Input id="rec-n" type="number" className="h-8 w-28" min={LIMITS[fn][0]} max={LIMITS[fn][1]} value={n}
            onChange={(e) => {
              const v = Math.max(LIMITS[fn][0], Math.min(LIMITS[fn][1], Number(e.target.value) || 0));
              setN(v);
              setStep(() => 0);
              setPlaying(false);
            }} />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <pre className="overflow-x-auto rounded-md border bg-muted p-3 font-mono text-[0.82rem] leading-6">{CODE[fn]}</pre>
        <div className="grid content-start gap-1.5 rounded-lg border bg-card p-3" aria-label="Call stack" role="list">
          <span className="text-xs font-bold tracking-wider text-muted-foreground uppercase">
            Call stack (top first) · deepest {deepest}
          </span>
          {s.stack.length === 0 ? (
            <span className="py-6 text-center text-sm text-muted-foreground">empty</span>
          ) : (
            [...s.stack].reverse().map((f, i) => (
              <div key={`${f.label}-${s.stack.length - i}`} role="listitem"
                className={cn("rounded-md border px-3 py-1.5 font-mono text-sm transition-colors",
                  i === 0 ? "border-primary bg-accent text-accent-foreground" : "bg-background")}>
                {f.label}
                {f.waiting ? <span className="block font-sans text-xs text-muted-foreground">{f.waiting}</span> : null}
              </div>
            ))
          )}
        </div>
      </div>
      <p className="min-h-12 rounded-md bg-muted p-3 text-sm" aria-live="polite">
        {s.text}
        {s.result !== undefined ? <strong className="ml-1 text-success">Result: {s.result}</strong> : null}
      </p>
      <StepControls step={step} total={snaps.length} playing={playing} setStep={setStep} setPlaying={setPlaying} />
    </div>
  );
}
