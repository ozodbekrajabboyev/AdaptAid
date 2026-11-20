"""The five recommendation signals and the outcome measure they learn from.

    need         1 - P(known)                                  knowledge-based
    style        length-scaled cosine (engine.style.similarity) content-based
    level        Gaussian fit of aid difficulty to the learner  content-based
    cf           collaborative filtering score                  collaborative
    helpfulness  smoothed mean residual gain of the aid         outcome statistic

need, style and level are already in [0, 1]. cf and helpfulness come on arbitrary
scales, so they are turned into percentile ranks within each candidate list.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from engine.bkt import BKTParams, predict_correct


def need(p_known: float) -> float:
    return max(0.0, min(1.0, 1.0 - p_known))


def target_difficulty(p_known: float) -> float:
    """On the 1–5 scale, aim slightly above the learner's current level."""
    return max(1.0, min(5.0, 1.0 + 4.0 * p_known + 0.5))


def level_fit(difficulty: float, p_known: float, sigma: float = 0.8) -> float:
    t = target_difficulty(p_known)
    return math.exp(-((difficulty - t) ** 2) / (2 * sigma**2))


def residual_gain(p_open: float, correct: Sequence[bool], params: BKTParams) -> float:
    """Outcome of using an aid: how much better the quick check went than BKT expected.

        gain = mean(correct) - P(correct | p_open)

    Using the mastery saved when the aid was *opened* (not the BKT estimate chained
    through the check) avoids two biases: BKT's learn step inflates every post-check
    estimate, and low-mastery learners would otherwise look like they gain the most.
    """
    if not correct:
        raise ValueError("a quick check needs at least one answer")
    observed = sum(1 for c in correct if c) / len(correct)
    return observed - predict_correct(p_open, params)


def smoothed_mean(total: float, n: int, prior_mean: float = 0.0, m: float = 5.0) -> float:
    """Bayesian average: (sum + m * prior) / (n + m). Few observations stay near the prior."""
    return (total + m * prior_mean) / (n + m)


def percentile_ranks(values: Sequence[float | None]) -> list[float | None]:
    """Rank-based scaling to [0, 1] among the non-missing values (ties share the average rank)."""
    present = [(v, i) for i, v in enumerate(values) if v is not None]
    out: list[float | None] = [None] * len(values)
    if not present:
        return out
    if len(present) == 1:
        out[present[0][1]] = 0.5
        return out
    ordered = sorted(present)
    j = 0
    while j < len(ordered):
        k = j
        while k + 1 < len(ordered) and ordered[k + 1][0] == ordered[j][0]:
            k += 1
        avg_rank = (j + k) / 2
        for idx in range(j, k + 1):
            out[ordered[idx][1]] = avg_rank / (len(ordered) - 1)
        j = k + 1
    return out
