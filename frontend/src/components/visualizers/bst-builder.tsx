"use client";

import { RotateCcwIcon, SearchIcon, PlusIcon } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type Node = { key: number; left: Node | null; right: Node | null };

function insert(root: Node | null, key: number): { root: Node; path: number[]; dup: boolean } {
  const path: number[] = [];
  if (!root) return { root: { key, left: null, right: null }, path: [key], dup: false };
  let cur = root;
  while (true) {
    path.push(cur.key);
    if (key === cur.key) return { root, path, dup: true };
    const side = key < cur.key ? "left" : "right";
    if (!cur[side]) {
      cur[side] = { key, left: null, right: null };
      path.push(key);
      return { root, path, dup: false };
    }
    cur = cur[side]!;
  }
}

function search(root: Node | null, key: number): { path: number[]; found: boolean } {
  const path: number[] = [];
  let cur = root;
  while (cur) {
    path.push(cur.key);
    if (key === cur.key) return { path, found: true };
    cur = key < cur.key ? cur.left : cur.right;
  }
  return { path, found: false };
}

function clone(n: Node | null): Node | null {
  return n ? { key: n.key, left: clone(n.left), right: clone(n.right) } : null;
}

function layout(root: Node | null) {
  const pos: { key: number; x: number; y: number; parent?: number }[] = [];
  let i = 0;
  const walk = (n: Node | null, depth: number, parent?: number) => {
    if (!n) return;
    walk(n.left, depth + 1, n.key);
    pos.push({ key: n.key, x: i++, y: depth, parent });
    walk(n.right, depth + 1, n.key);
  };
  walk(root, 0);
  return pos;
}

function height(n: Node | null): number {
  return n ? 1 + Math.max(height(n.left), height(n.right)) : -1;
}

export function BstBuilder() {
  const [root, setRoot] = useState<Node | null>(() => [50, 30, 70, 20, 40, 60, 80].reduce<Node | null>((r, k) => insert(r, k).root, null));
  const [value, setValue] = useState("");
  const [path, setPath] = useState<number[]>([]);
  const [message, setMessage] = useState("Insert or search for a key. The highlighted path shows every comparison.");
  const nodes = useMemo(() => layout(root), [root]);
  const h = height(root);
  const W = Math.max(nodes.length, 1) * 52 + 20;
  const H = (Math.max(h, 0) + 1) * 64 + 20;
  const at = new Map(nodes.map((n) => [n.key, n]));

  function readKey(): number | null {
    const k = Number(value);
    if (!Number.isInteger(k) || k < 0 || k > 999) {
      setMessage("Enter a whole number from 0 to 999.");
      return null;
    }
    return k;
  }

  function onInsert(e: FormEvent) {
    e.preventDefault();
    const k = readKey();
    if (k === null) return;
    const r = insert(clone(root), k);
    setRoot(r.root);
    setPath(r.path);
    setMessage(r.dup ? `${k} is already in the tree (no duplicates).`
      : `Inserted ${k} after ${r.path.length - 1} comparison${r.path.length === 2 ? "" : "s"}: ${r.path.slice(0, -1).map((p) => `${k} ${k < p ? "<" : ">"} ${p}`).join(", ") || "it is the root"}.`);
    setValue("");
  }

  function onSearch() {
    const k = readKey();
    if (k === null) return;
    const r = search(root, k);
    setPath(r.path);
    setMessage(r.found ? `Found ${k} after ${r.path.length} comparison${r.path.length === 1 ? "" : "s"}.`
      : `${k} is not in the tree. The search fell off after ${r.path.length} comparison${r.path.length === 1 ? "" : "s"}.`);
  }

  function sortedDemo() {
    const r = [10, 20, 30, 40, 50, 60, 70].reduce<Node | null>((acc, k) => insert(acc, k).root, null);
    setRoot(r);
    setPath([]);
    setMessage("Keys inserted in sorted order make a chain: height 6 for 7 keys. Searching is now O(n), not O(log n).");
  }

  const inorder = nodes.map((n) => n.key).join(", ");

  return (
    <div className="grid gap-4" data-testid="bst-builder">
      <form onSubmit={onInsert} className="flex flex-wrap items-end gap-2">
        <div className="grid gap-1">
          <Label htmlFor="bst-key" className="text-xs">Key</Label>
          <Input id="bst-key" inputMode="numeric" className="h-8 w-28" value={value} onChange={(e) => setValue(e.target.value)} />
        </div>
        <Button type="submit" size="sm"><PlusIcon /> Insert</Button>
        <Button type="button" size="sm" variant="outline" onClick={onSearch}><SearchIcon /> Search</Button>
        <Button type="button" size="sm" variant="outline" onClick={sortedDemo}>Insert 10…70 in order</Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => { setRoot(null); setPath([]); setMessage("Empty tree."); }}>
          <RotateCcwIcon /> Clear
        </Button>
      </form>
      <div className="overflow-x-auto rounded-lg border bg-card p-2">
        <svg width={W} height={H} role="img" aria-label={`Binary search tree, inorder ${inorder || "empty"}`}>
          {nodes.map((n) => {
            const p = n.parent !== undefined ? at.get(n.parent) : undefined;
            if (!p) return null;
            const on = path.includes(n.key) && path.includes(p.key);
            return (
              <line key={`e${n.key}`} x1={p.x * 52 + 36} y1={p.y * 64 + 30} x2={n.x * 52 + 36} y2={n.y * 64 + 30}
                className={on ? "stroke-primary" : "stroke-border"} strokeWidth={on ? 3 : 2} />
            );
          })}
          {nodes.map((n) => {
            const on = path.includes(n.key);
            const last = path[path.length - 1] === n.key;
            return (
              <g key={n.key} transform={`translate(${n.x * 52 + 36}, ${n.y * 64 + 30})`}>
                <circle r={19} className={cn(last ? "fill-primary" : on ? "fill-accent" : "fill-background",
                  on ? "stroke-primary" : "stroke-muted-foreground/50")} strokeWidth={2} />
                <text textAnchor="middle" dy="0.35em" className={cn("font-mono text-[13px]", last ? "fill-primary-foreground" : "fill-foreground")}>
                  {n.key}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <p className="rounded-md bg-muted p-3 text-sm" aria-live="polite">{message}</p>
      <p className="font-mono text-xs text-muted-foreground">
        height {h < 0 ? "–" : h} (edges) · inorder: {inorder || "–"}
      </p>
    </div>
  );
}
