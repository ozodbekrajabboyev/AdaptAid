"""Recommendation policies.

AdaptivePolicy  the hybrid recommender used by AdaptAid (and its ablations via `enabled`).
StaticPolicy    the "course plan": syllabus order and the teacher's default aid order.
                This is the pilot's control arm and the "static instruction" baseline.
RandomPolicy    random aids from the frontier (sanity baseline).

All policies return the same RecList shape, so the UI and the logs treat both pilot
arms identically. Only the concept choice and the aid ranking differ.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from engine.bkt import MASTERED
from engine.graph import frontier, next_concept_adaptive, next_concept_static
from engine.hybrid import DEFAULT_WEIGHTS, PHASE_THRESHOLDS, SIGNALS, phase_for, score_candidates
from engine.rerank import mmr, with_explore_slot
from engine.types import AidInfo, Catalogue, LearnerView, RecList, Scored


def _candidates(learner: LearnerView, cat: Catalogue, concepts: list[int]) -> list[tuple[AidInfo, int, bool]]:
    """Fresh aids for each concept; if a concept has none left, re-offer its best-gain aid."""
    out: list[tuple[AidInfo, int, bool]] = []
    for c in concepts:
        aids = cat.aids_by_concept.get(c, [])
        fresh = [a for a in aids if a.id not in learner.recent_aids]
        if fresh:
            out.extend((a, c, False) for a in fresh)
        elif aids and learner.mastery.get(c, 0.0) < MASTERED:
            best_id = learner.best_gain_aid.get(c)
            best = cat.aids.get(best_id) if best_id is not None else None
            out.append((best or aids[0], c, True))
    return out


@dataclass
class AdaptivePolicy:
    name: str = "adaptive"
    weights: dict[str, dict[str, float]] = field(default_factory=lambda: {k: dict(v) for k, v in DEFAULT_WEIGHTS.items()})
    enabled: tuple[str, ...] = SIGNALS
    thresholds: tuple[int, int] = PHASE_THRESHOLDS
    explore: bool = True
    lam: float = 0.7

    def focus(self, learner: LearnerView, cat: Catalogue) -> int | None:
        fr = frontier(cat.syllabus, learner.mastery, cat.prereqs)
        return next_concept_adaptive(fr, learner.mastery, cat.downstream, cat.order_index)

    def recommend(self, learner: LearnerView, cat: Catalogue, k: int = 5, concept: int | None = None) -> RecList:
        phase = phase_for(learner.n_uses, self.thresholds)
        weights = self.weights[phase]
        concepts = [concept] if concept is not None else frontier(cat.syllabus, learner.mastery, cat.prereqs)
        focus = concept if concept is not None else self.focus(learner, cat)
        cands = _candidates(learner, cat, concepts)
        if not cands:
            return RecList(self.name, phase, focus, [], weights)
        scored = score_candidates([(a, c) for a, c, _ in cands], learner, weights, self.enabled)
        reoffer = {(a.id, c) for a, c, r in cands if r}
        for s in scored:
            s.reoffer = (s.aid.id, s.concept_id) in reoffer
        picked = mmr(scored, k, self.lam)
        if self.explore:
            picked = with_explore_slot(picked, scored, learner.format_counts, k)
        return RecList(self.name, phase, focus, picked, weights)


@dataclass
class StaticPolicy:
    name: str = "static"
    aids_to_advance: int = 3

    def focus(self, learner: LearnerView, cat: Catalogue) -> int | None:
        return next_concept_static(
            cat.syllabus, learner.mastery, learner.passed_check, learner.aids_used_per_concept, self.aids_to_advance
        )

    def recommend(self, learner: LearnerView, cat: Catalogue, k: int = 5, concept: int | None = None) -> RecList:
        c = concept if concept is not None else self.focus(learner, cat)
        if c is None:
            return RecList(self.name, "static", None, [])
        aids = cat.aids_by_concept.get(c, [])
        fresh = [a for a in aids if a.id not in learner.recent_aids]
        ordered = fresh + [a for a in aids if a not in fresh]
        items = [
            Scored(aid=a, concept_id=c, parts={}, score=round(1 - i / max(1, len(ordered)), 4))
            for i, a in enumerate(ordered[:k])
        ]
        return RecList(self.name, "static", c, items)


@dataclass
class RandomPolicy:
    name: str = "random"
    seed: int = 0

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def focus(self, learner: LearnerView, cat: Catalogue) -> int | None:
        fr = frontier(cat.syllabus, learner.mastery, cat.prereqs)
        return self._rng.choice(fr) if fr else None

    def recommend(self, learner: LearnerView, cat: Catalogue, k: int = 5, concept: int | None = None) -> RecList:
        concepts = [concept] if concept is not None else frontier(cat.syllabus, learner.mastery, cat.prereqs)
        cands = _candidates(learner, cat, concepts)
        picks = self._rng.sample(cands, min(k, len(cands)))
        items = [Scored(aid=a, concept_id=c, parts={}, score=0.0, reoffer=r) for a, c, r in picks]
        return RecList(self.name, "random", concept, items)


def ablation(name: str, **kw) -> AdaptivePolicy:
    """Variants used in the evaluation: need_only, style_only, level_only, cf_only, no_style."""
    presets = {
        "need_only": ("need",),
        "style_only": ("style",),
        "level_only": ("level",),
        "cf_only": ("cf",),
        "no_style": ("need", "level", "cf", "help"),
        "hybrid": SIGNALS,
    }
    enabled = presets[name]
    pol = AdaptivePolicy(name=name, enabled=enabled, **kw)
    if name in ("style_only", "level_only", "cf_only", "need_only"):
        # A single-signal ranker should use that signal in every phase.
        for ph in pol.weights:
            pol.weights[ph] = {s: (1.0 if s in enabled else 0.0) for s in SIGNALS}
    return pol
