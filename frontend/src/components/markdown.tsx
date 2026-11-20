"use client";

import { useTheme } from "next-themes";
import { useEffect, useId, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

/** Renders a ```mermaid block as an SVG diagram, in the current theme. */
function Mermaid({ code }: { code: string }) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const { resolvedTheme } = useTheme();
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: resolvedTheme === "dark" ? "dark" : "neutral",
          securityLevel: "strict",
          fontFamily: "var(--font-body), system-ui, sans-serif",
        });
        const { svg } = await mermaid.render(`m${id}${resolvedTheme ?? ""}`, code);
        if (!cancelled) setSvg(svg);
      } catch {
        if (!cancelled) setError(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, id, resolvedTheme]);

  if (error) {
    return <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">{code}</pre>;
  }
  return (
    <div
      className="my-4 flex justify-center overflow-x-auto rounded-md border bg-card p-3 [&_svg]:h-auto [&_svg]:max-w-full"
      aria-label="Diagram"
      role="img"
      // mermaid renders with securityLevel "strict", which sanitises the SVG.
      dangerouslySetInnerHTML={svg ? { __html: svg } : undefined}
    >
      {svg ? undefined : <span className="text-sm text-muted-foreground">Drawing diagram…</span>}
    </div>
  );
}

const components: Components = {
  h1: ({ children }) => <h1 className="mt-2 mb-4 font-heading text-2xl font-bold tracking-tight">{children}</h1>,
  h2: ({ children }) => <h2 className="mt-8 mb-3 font-heading text-xl font-bold">{children}</h2>,
  h3: ({ children }) => <h3 className="mt-6 mb-2 font-heading text-lg font-bold">{children}</h3>,
  p: ({ children }) => <p className="my-3 leading-7">{children}</p>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-6">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-6">{children}</ol>,
  li: ({ children }) => <li className="leading-7">{children}</li>,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-primary underline underline-offset-2">
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-4 border-l-4 border-highlight bg-muted/60 py-1 pl-4">{children}</blockquote>
  ),
  table: ({ children }) => (
    <div className="my-4 overflow-x-auto rounded-md border">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => <th className="border-b bg-muted px-3 py-2 text-left font-bold">{children}</th>,
  td: ({ children }) => <td className="border-b px-3 py-2 align-top tabular">{children}</td>,
  code: ({ className, children }) => {
    const lang = /language-(\w+)/.exec(className ?? "")?.[1];
    const text = String(children).replace(/\n$/, "");
    if (lang === "mermaid") return <Mermaid code={text} />;
    if (!lang && !text.includes("\n")) {
      return <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.85em]">{children}</code>;
    }
    return <code className={cn("font-mono", className)}>{children}</code>;
  },
  pre: ({ children }) => {
    // mermaid blocks render their own container
    const child = Array.isArray(children) ? children[0] : children;
    if (child && typeof child === "object" && "type" in child && child.type === Mermaid) return <>{children}</>;
    return (
      <pre className="my-4 overflow-x-auto rounded-md border bg-muted p-3 font-mono text-[0.85rem] leading-6">
        {children}
      </pre>
    );
  },
};

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn("max-w-none text-[0.97rem]", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
