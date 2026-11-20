import type { Schemas } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type Style = Schemas["StyleOut"];

const POLE_LABEL: Record<string, string> = {
  active: "Active",
  reflective: "Reflective",
  sensing: "Sensing",
  intuitive: "Intuitive",
  visual: "Visual",
  verbal: "Verbal",
  sequential: "Sequential",
  global: "Global",
};

/** Four bipolar sliders. The filled dot is the learned position; the hollow one the questionnaire prior. */
export function StyleProfile({ style, showPrior = true }: { style: Style; showPrior?: boolean }) {
  return (
    <div className="grid gap-3">
      {style.labels.map(([left, right], i) => {
        const v = style.vector[i];
        const prior = style.prior[i];
        const pos = (x: number) => `${((1 - x) / 2) * 100}%`;
        return (
          <div key={left} className="grid grid-cols-[5.5rem_minmax(0,1fr)_5.5rem] items-center gap-2 text-xs">
            <span className={cn("text-left", v > 0.15 && "font-bold text-foreground")}>{POLE_LABEL[left]}</span>
            <div
              className="relative h-4"
              role="img"
              aria-label={`${POLE_LABEL[left]} versus ${POLE_LABEL[right]}: ${
                Math.abs(v) < 0.15 ? "balanced" : `leans ${v > 0 ? POLE_LABEL[left] : POLE_LABEL[right]}`
              }`}
            >
              <div className="absolute inset-x-0 top-1/2 h-0.5 -translate-y-1/2 rounded bg-border" />
              <div className="absolute top-0.5 left-1/2 h-3 w-px bg-muted-foreground/50" />
              {showPrior && Math.abs(prior - v) > 0.04 ? (
                <span
                  className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-muted-foreground/60 bg-background"
                  style={{ left: pos(prior) }}
                  title="From your questionnaire"
                />
              ) : null}
              <span
                className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background bg-primary shadow-[0_0_0_1px_var(--primary)] transition-[left] duration-700"
                style={{ left: pos(v) }}
              />
            </div>
            <span className={cn("text-right", v < -0.15 && "font-bold text-foreground")}>{POLE_LABEL[right]}</span>
          </div>
        );
      })}
    </div>
  );
}
