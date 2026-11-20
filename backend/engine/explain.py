"""Human-readable reasons for each recommendation.

The reason names what makes *this* card different from the others in the list: each
signal's contribution is measured relative to the list average, w_k * (x_k - mean_k),
so cards in the same list get different reasons.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from engine.hybrid import SIGNALS
from engine.types import Scored

FORMAT_LABEL = {
    "video": "video",
    "animation": "animation",
    "interactive": "interactive visual",
    "notes": "notes",
    "worked_example": "worked example",
    "cheat_sheet": "cheat sheet",
    "concept_map": "concept map",
    "practice": "practice drill",
    "article": "article",
}

CONTROL_REASON = "Next in the course plan."


@dataclass
class PeerStat:
    n_checked: int
    n_improved: int


@dataclass
class ExplainContext:
    concept_names: Mapping[int, str]
    mastery: Mapping[int, float]
    dominant_pole: str | None = None  # e.g. "visual"
    peers: Mapping[int, PeerStat] | None = None  # aid id -> stats for learners like this one
    min_peer_n: int = 5


def contributions(items: Sequence[Scored], weights: Mapping[str, float]) -> list[dict[str, float]]:
    means: dict[str, float] = {}
    for k in SIGNALS:
        vals = [s.parts[k] for s in items if s.parts.get(k) is not None]
        means[k] = sum(vals) / len(vals) if vals else 0.0
    out = []
    for s in items:
        out.append(
            {
                k: weights.get(k, 0.0) * (s.parts[k] - means[k])  # type: ignore[operator]
                for k in SIGNALS
                if s.parts.get(k) is not None and weights.get(k, 0.0) > 0
            }
        )
    return out


def _phrase(signal: str, item: Scored, ctx: ExplainContext) -> str:
    concept = ctx.concept_names.get(item.concept_id, "this topic")
    p = ctx.mastery.get(item.concept_id, 0.0)
    if signal == "need":
        return f"{concept} needs the most work right now."
    if signal == "style":
        if ctx.dominant_pole:
            return f"It matches how you learn best: {ctx.dominant_pole} material."
        return "Its format suits your learning profile."
    if signal == "level":
        return "It is pitched just above your current level." if p > 0.2 else "It starts from the basics."
    if signal == "cf":
        return "Students with a profile like yours learned well from it."
    if signal == "help":
        return f"It has one of the best track records for {concept}."
    return ""


def explain(item: Scored, contrib: Mapping[str, float], ctx: ExplainContext) -> str:
    concept = ctx.concept_names.get(item.concept_id, "this topic")
    p = ctx.mastery.get(item.concept_id, 0.0)
    fmt = FORMAT_LABEL.get(item.aid.aid_type, item.aid.aid_type)

    if item.is_explore:
        return (
            f"You haven't used many {fmt}s yet. One card in your list tries a different format "
            "so AdaptAid can learn what works for you."
        )
    if item.reoffer:
        return f"You've used every aid for {concept}. This one helped you most, so it's worth another look."

    lead = f"You're at {p:.0%} on {concept}."
    ranked = sorted((v, k) for k, v in contrib.items() if v > 0)
    ranked.reverse()
    reasons = [_phrase(k, item, ctx) for _, k in ranked if k != "need"][:1]
    if not reasons and ranked:
        reasons = [_phrase(ranked[0][1], item, ctx)]
    text = " ".join([lead, *reasons]).strip()

    if ctx.peers and item.aid.id in ctx.peers:
        stat = ctx.peers[item.aid.id]
        if stat.n_checked >= ctx.min_peer_n:
            text += f" {stat.n_improved} of {stat.n_checked} similar students improved after it."
    return text
