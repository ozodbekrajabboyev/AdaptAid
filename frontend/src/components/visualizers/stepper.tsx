"use client";

import { PauseIcon, PlayIcon, StepBackIcon, StepForwardIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

/** Shared step controls: back, play/pause, forward, with a step counter. */
export function useStepper(total: number, speedMs = 700) {
  const [step, setStep] = useState(0);
  const [wantPlay, setPlaying] = useState(false);
  // Playback stops by itself at the last step (derived, not stored).
  const playing = wantPlay && step < total - 1;

  useEffect(() => {
    if (!playing) return;
    const t = setTimeout(() => setStep((s) => Math.min(total - 1, s + 1)), speedMs);
    return () => clearTimeout(t);
  }, [playing, step, total, speedMs]);

  return { step, setStep, playing, setPlaying, atEnd: step >= total - 1 };
}

export function StepControls({
  step,
  total,
  playing,
  setStep,
  setPlaying,
}: {
  step: number;
  total: number;
  playing: boolean;
  setStep: (fn: (s: number) => number) => void;
  setPlaying: (p: boolean) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button variant="outline" size="icon" aria-label="Previous step" disabled={step === 0}
        onClick={() => { setPlaying(false); setStep((s) => Math.max(0, s - 1)); }}>
        <StepBackIcon />
      </Button>
      <Button variant="outline" size="icon" aria-label={playing ? "Pause" : "Play"} disabled={step >= total - 1 && !playing}
        onClick={() => setPlaying(!playing)}>
        {playing ? <PauseIcon /> : <PlayIcon />}
      </Button>
      <Button variant="outline" size="icon" aria-label="Next step" disabled={step >= total - 1}
        onClick={() => { setPlaying(false); setStep((s) => Math.min(total - 1, s + 1)); }}>
        <StepForwardIcon />
      </Button>
      <span className="font-mono text-xs text-muted-foreground tabular">
        step {step + 1} / {total}
      </span>
    </div>
  );
}
