"""Concept prerequisite graph: validation, layout layers, frontier and next-concept rules."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable, Mapping, Sequence

from engine.bkt import MASTERED, UNLOCK


class CycleError(ValueError):
    pass


def _prereq_map(nodes: Iterable[int], edges: Iterable[tuple[int, int]]) -> dict[int, set[int]]:
    """edges are (concept, prerequisite) pairs."""
    pre: dict[int, set[int]] = {n: set() for n in nodes}
    for c, p in edges:
        if c not in pre or p not in pre:
            raise ValueError(f"edge ({c}, {p}) refers to an unknown concept")
        pre[c].add(p)
    return pre


def topological_order(nodes: Sequence[int], edges: Iterable[tuple[int, int]]) -> list[int]:
    pre = _prereq_map(nodes, edges)
    children: dict[int, list[int]] = defaultdict(list)
    indeg = {n: len(pre[n]) for n in nodes}
    for c, ps in pre.items():
        for p in ps:
            children[p].append(c)
    queue = deque(n for n in nodes if indeg[n] == 0)
    out: list[int] = []
    while queue:
        n = queue.popleft()
        out.append(n)
        for c in children[n]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    if len(out) != len(nodes):
        stuck = sorted(n for n in nodes if indeg[n] > 0)
        raise CycleError(f"prerequisite cycle among concepts {stuck}")
    return out


def validate_dag(nodes: Sequence[int], edges: Iterable[tuple[int, int]]) -> None:
    topological_order(nodes, list(edges))


def layers(nodes: Sequence[int], edges: Iterable[tuple[int, int]]) -> dict[int, int]:
    """Longest-path depth of each concept (roots are layer 0). Used to lay out the path view."""
    edges = list(edges)
    pre = _prereq_map(nodes, edges)
    depth: dict[int, int] = {}
    for n in topological_order(nodes, edges):
        depth[n] = 1 + max((depth[p] for p in pre[n]), default=-1)
    return depth


def downstream_counts(nodes: Sequence[int], edges: Iterable[tuple[int, int]]) -> dict[int, int]:
    """How many concepts transitively depend on each concept."""
    children: dict[int, set[int]] = defaultdict(set)
    for c, p in edges:
        children[p].add(c)
    out: dict[int, int] = {}
    for n in nodes:
        seen: set[int] = set()
        stack = list(children[n])
        while stack:
            x = stack.pop()
            if x not in seen:
                seen.add(x)
                stack.extend(children[x])
        out[n] = len(seen)
    return out


def status(
    concept: int, mastery: Mapping[int, float], prereqs: Mapping[int, set[int]], unlock: float = UNLOCK
) -> str:
    p = mastery.get(concept, 0.0)
    if p >= MASTERED:
        return "mastered"
    if all(mastery.get(q, 0.0) >= unlock for q in prereqs.get(concept, set())):
        return "in_progress" if p > 0 else "available"
    return "locked"


def frontier(
    nodes: Sequence[int],
    mastery: Mapping[int, float],
    prereqs: Mapping[int, set[int]],
    unlock: float = UNLOCK,
) -> list[int]:
    """Concepts not yet mastered whose prerequisites are all at or above the unlock level."""
    return [n for n in nodes if status(n, mastery, prereqs, unlock) in ("available", "in_progress")]


def next_concept_adaptive(
    candidates: Sequence[int],
    mastery: Mapping[int, float],
    downstream: Mapping[int, int],
    syllabus_order: Mapping[int, int],
) -> int | None:
    """Adaptive rule: the frontier concept with the highest need × (1 + concepts it unlocks).

    Favouring concepts that unlock more of the course gives a learning path that differs
    from the syllabus order. Ties fall back to syllabus order.
    """
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda c: ((1 - mastery.get(c, 0.0)) * (1 + downstream.get(c, 0)), -syllabus_order.get(c, 0)),
    )


def next_concept_static(
    syllabus: Sequence[int],
    mastery: Mapping[int, float],
    passed_check: set[int],
    aids_used: Mapping[int, int],
    aids_to_advance: int = 3,
) -> int | None:
    """Static ("course plan") rule: first concept in syllabus order not yet finished.

    A concept is finished when mastered, when a quick check on it was passed, or after
    `aids_to_advance` aids, the way a fixed course moves on regardless of the student.
    """
    for c in syllabus:
        done = mastery.get(c, 0.0) >= MASTERED or c in passed_check or aids_used.get(c, 0) >= aids_to_advance
        if not done:
            return c
    return None


def projected_route(
    nodes: Sequence[int],
    mastery: Mapping[int, float],
    prereqs: Mapping[int, set[int]],
    downstream: Mapping[int, int],
    syllabus_order: Mapping[int, int],
    steps: int = 3,
) -> list[int]:
    """The next few concepts the adaptive rule would pick, assuming each one gets mastered."""
    m = dict(mastery)
    route: list[int] = []
    for _ in range(steps):
        cand = [c for c in frontier(nodes, m, prereqs) if c not in route]
        nxt = next_concept_adaptive(cand, m, downstream, syllabus_order)
        if nxt is None:
            break
        route.append(nxt)
        m[nxt] = MASTERED
    return route
