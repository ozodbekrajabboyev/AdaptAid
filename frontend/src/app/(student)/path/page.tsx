"use client";

import "@xyflow/react/dist/style.css";

import { Background, type Edge, MarkerType, type Node, Position, ReactFlow } from "@xyflow/react";
import { useTheme } from "next-themes";
import Link from "next/link";
import { useMemo, useState } from "react";

import { PageHeader, PageSkeleton } from "@/components/app-shell";
import { AidTypeBadge } from "@/components/learning/aid-type";
import { MasteryBar } from "@/components/learning/mastery";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { Schemas } from "@/lib/api/client";
import { pct, usePath, useRecs } from "@/lib/learning";
import { cn } from "@/lib/utils";

type PNode = Schemas["PathNode"];

const STATUS_STYLE: Record<string, string> = {
  mastered: "border-success bg-success/10",
  in_progress: "border-primary bg-card",
  available: "border-primary/60 bg-card",
  locked: "border-dashed border-border bg-muted text-muted-foreground",
};
const STATUS_LABEL: Record<string, string> = {
  mastered: "Mastered",
  in_progress: "In progress",
  available: "Unlocked",
  locked: "Locked",
};

function ConceptNode({ data }: { data: PNode }) {
  return (
    <div className={cn("grid w-44 gap-1.5 rounded-lg border-2 px-3 py-2 text-left shadow-sm", STATUS_STYLE[data.status],
      data.projected_rank === 1 && "ring-2 ring-highlight ring-offset-2 ring-offset-background")}>
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm font-bold">{data.name}</span>
        {data.projected_rank ? (
          <span className="rounded bg-highlight px-1.5 font-mono text-[10px] text-highlight-foreground">next {data.projected_rank}</span>
        ) : null}
      </div>
      <MasteryBar p={data.p} locked={data.status === "locked"} />
      <span className="flex justify-between text-[11px] text-muted-foreground">
        <span>{STATUS_LABEL[data.status]}</span>
        <span className="font-mono tabular">{pct(data.p)}</span>
      </span>
    </div>
  );
}

const nodeTypes = { concept: ConceptNode };

export default function PathPage() {
  const path = usePath();
  const { resolvedTheme } = useTheme();
  const [selected, setSelected] = useState<PNode | null>(null);

  const { nodes, edges } = useMemo(() => {
    if (!path.data) return { nodes: [] as Node[], edges: [] as Edge[] };
    const byLayer = new Map<number, PNode[]>();
    for (const n of path.data.nodes) byLayer.set(n.layer, [...(byLayer.get(n.layer) ?? []), n]);
    const nodes: Node[] = [];
    for (const [layer, list] of byLayer) {
      list.sort((a, b) => a.order - b.order);
      list.forEach((n, i) => {
        nodes.push({
          id: String(n.id), type: "concept", data: n, draggable: false,
          position: { x: layer * 230, y: (i - (list.length - 1) / 2) * 110 },
          sourcePosition: Position.Right, targetPosition: Position.Left,
        });
      });
    }
    const route = path.data.route;
    const onRoute = new Set(route.slice(1).map((c, i) => `${route[i]}-${c}`));
    const edges: Edge[] = path.data.edges.map(([from, to]) => ({
      id: `${from}-${to}`, source: String(from), target: String(to),
      animated: onRoute.has(`${from}-${to}`),
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { strokeWidth: 1.5 },
    }));
    return { nodes, edges };
  }, [path.data]);

  if (path.isPending) return <PageSkeleton />;
  if (path.error) return <p className="text-destructive">{path.error.message}</p>;

  return (
    <div className="grid gap-4">
      <PageHeader title="Learning path"
        description="Concepts unlock when their prerequisites reach 70% mastery. The highlighted concepts are where AdaptAid would take you next, based on what you still need and what each concept unlocks." />
      <div className="h-[560px] overflow-hidden rounded-lg border bg-card" data-testid="path-graph">
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.3} maxZoom={1.5}
          forceColorMode={resolvedTheme === "dark" ? "dark" : "light"} nodesConnectable={false} proOptions={{ hideAttribution: true }}
          onNodeClick={(_, n) => setSelected(n.data as PNode)}>
          <Background gap={24} />
        </ReactFlow>
      </div>
      <p className="text-sm text-muted-foreground">
        Your route so far: {path.data.route.length ? path.data.route.map((id) => path.data.nodes.find((n) => n.id === id)?.name).join(" → ") : "not started yet"}.
        Click a concept to see its teaching aids.
      </p>
      <ConceptSheet node={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function ConceptSheet({ node, onClose }: { node: PNode | null; onClose: () => void }) {
  const recs = useRecs(node && node.status !== "locked" ? node.id : null);
  return (
    <Sheet open={!!node} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-md">
        {node ? (
          <>
            <SheetHeader>
              <SheetTitle>{node.name}</SheetTitle>
              <SheetDescription>{STATUS_LABEL[node.status]} · mastery {pct(node.p)}</SheetDescription>
            </SheetHeader>
            <div className="grid gap-3 px-4 pb-6">
              {node.status === "locked" ? (
                <p className="text-sm text-muted-foreground">Finish its prerequisites first. They are the concepts with arrows pointing into it.</p>
              ) : recs.isPending ? (
                <p className="text-sm text-muted-foreground">Loading aids…</p>
              ) : (
                recs.data?.items.map((item) => (
                  <Link key={item.id} href={`/learn/${item.aid.id}?item=${item.id}`}
                    className="grid gap-1.5 rounded-lg border p-3 hover:border-primary/60">
                    <AidTypeBadge type={item.aid.aid_type} className="justify-self-start" />
                    <span className="font-bold">{item.aid.title}</span>
                    <span className="text-xs text-muted-foreground">{item.explanation}</span>
                  </Link>
                ))
              )}
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
