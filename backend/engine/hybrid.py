"""Hybrid scoring: a weighted combination of five signals whose weights switch by data phase.

This is a *weighted* hybrid (several scores combined) and a *switching* hybrid (the
weights change as the system learns about the learner), in Burke's (2002) taxonomy.

    score(aid) = sum_k w_k x_k / sum_k w_k   over the signals available for that aid

Re-normalising over available signals means an aid with no CF score yet is not
penalised for it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from engine.signals import level_fit, need, percentile_ranks
from engine.style import similarity
from engine.types import AidInfo, LearnerView, Scored

SIGNALS = ("need", "style", "level", "cf", "help")

DEFAULT_WEIGHTS: dict[str, dict[str, float]] = {
    "cold": {"need": 0.45, "style": 0.30, "level": 0.25, "cf": 0.0, "help": 0.0},
    "warm": {"need": 0.35, "style": 0.20, "level": 0.20, "cf": 0.10, "help": 0.15},
    "established": {"need": 0.30, "style": 0.10, "level": 0.15, "cf": 0.25, "help": 0.20},
}
PHASE_THRESHOLDS = (5, 30)


def phase_for(n_uses: int, thresholds: tuple[int, int] = PHASE_THRESHOLDS) -> str:
    if n_uses < thresholds[0]:
        return "cold"
    if n_uses < thresholds[1]:
        return "warm"
    return "established"


def score_candidates(
    candidates: Sequence[tuple[AidInfo, int]],
    learner: LearnerView,
    weights: Mapping[str, float],
    enabled: Iterable[str] = SIGNALS,
) -> list[Scored]:
    """Score (aid, concept) candidates. Returns them sorted best first."""
    enabled = set(enabled)
    cf_pct = percentile_ranks([learner.cf_scores.get(a.id) for a, _ in candidates])
    help_pct = percentile_ranks([learner.help_scores.get(a.id) for a, _ in candidates])

    out: list[Scored] = []
    for i, (aid, concept) in enumerate(candidates):
        p = learner.mastery.get(concept, 0.0)
        parts: dict[str, float | None] = {
            "need": need(p),
            "style": similarity(learner.style, aid.style),
            "level": level_fit(aid.difficulty, p),
            "cf": cf_pct[i],
            "help": help_pct[i],
        }
        total, wsum = 0.0, 0.0
        for k in SIGNALS:
            x, w = parts[k], weights.get(k, 0.0)
            if k in enabled and x is not None and w > 0:
                total += w * x
                wsum += w
        score = total / wsum if wsum > 0 else 0.0
        out.append(Scored(aid=aid, concept_id=concept, parts=parts, score=round(score, 6)))
    out.sort(key=lambda s: (-s.score, s.aid.default_order, s.aid.id))
    return out
