import Link from "next/link";

import { Button } from "@/components/ui/button";

const STEPS = [
  { title: "Diagnose", text: "A short questionnaire and a diagnostic quiz show where you are and how you like to learn." },
  { title: "Recommend", text: "AdaptAid ranks videos, animations, notes and exercises for the topic you need next, and says why." },
  { title: "Learn", text: "Use the aid. Your time, completion and rating are recorded." },
  { title: "Check", text: "Three quick questions update your mastery, and your next recommendations adapt." },
];

export default function Landing() {
  return (
    <div className="grid gap-14 pt-10 md:pt-16">
      <section className="grid max-w-3xl gap-5">
        <p className="text-xs font-bold tracking-[0.12em] text-primary uppercase">Adaptive learning platform</p>
        <h1 className="font-heading text-4xl font-bold tracking-tight md:text-6xl">
          The right teaching aid for <span className="mark">what you don&apos;t know yet</span>
        </h1>
        <p className="max-w-prose text-lg text-muted-foreground">
          AdaptAid tracks your mastery of each topic, learns which kinds of material actually work for you, and
          recommends the next aid to use. Teachers see where the class is stuck and which aids to bring to the
          next lecture.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg" className="px-5">
            <Link href="/register">Create an account</Link>
          </Button>
          <Button asChild size="lg" variant="outline" className="px-5">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </section>

      <section aria-labelledby="how" className="grid gap-4">
        <h2 id="how" className="font-heading text-xl font-bold">
          How it adapts
        </h2>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <li key={s.title} className="grid content-start gap-2 rounded-lg border bg-card p-4">
              <span className="grid size-6 place-items-center rounded-full bg-primary font-mono text-xs text-primary-foreground">
                {i + 1}
              </span>
              <h3 className="font-heading font-bold">{s.title}</h3>
              <p className="text-sm text-muted-foreground">{s.text}</p>
            </li>
          ))}
        </ol>
        <p className="text-sm text-muted-foreground">Then back to step 2, after every check.</p>
      </section>
    </div>
  );
}
