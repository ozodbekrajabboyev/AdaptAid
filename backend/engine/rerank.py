"""Re-ranking: diversity with Maximal Marginal Relevance, plus one exploration slot."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from engine.style import cosine
from engine.types import Scored


def aid_similarity(a: Scored, b: Scored) -> float:
    """1.0 for the same format; otherwise how close their style vectors are (0–0.3)."""
    if a.aid.aid_type == b.aid.aid_type:
        return 1.0
    return 0.3 * (1 + cosine(a.aid.style, b.aid.style)) / 2


def mmr(scored: Sequence[Scored], k: int, lam: float = 0.7) -> list[Scored]:
    """Greedy MMR (Carbonell & Goldstein, 1998): relevance minus redundancy with picks so far."""
    pool = list(scored)
    picked: list[Scored] = []
    while pool and len(picked) < k:
        best = max(
            pool,
            key=lambda s: lam * s.score - (1 - lam) * max((aid_similarity(s, p) for p in picked), default=0.0),
        )
        picked.append(best)
        pool.remove(best)
    return picked


def with_explore_slot(
    picked: list[Scored], pool: Sequence[Scored], format_counts: Mapping[str, int], k: int
) -> list[Scored]:
    """Put the best aid of the learner's least-used format (absent from the list) in the last slot.

    Without this the system would only ever show formats it already believes in, and the
    learning-preference model could never discover that its prior was wrong.
    """
    if k < 3:
        return picked
    shown = {s.aid.aid_type for s in picked}
    rest = [s for s in pool if s not in picked and s.aid.aid_type not in shown]
    if not rest:
        return picked
    least = min(format_counts.get(s.aid.aid_type, 0) for s in rest)
    options = [s for s in rest if format_counts.get(s.aid.aid_type, 0) == least]
    choice = max(options, key=lambda s: s.score)
    choice.is_explore = True
    if len(picked) >= k:
        picked = picked[: k - 1]
    return [*picked, choice]
