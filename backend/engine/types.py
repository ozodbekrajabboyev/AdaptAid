"""Plain data structures shared by the engine, the API services and the simulator."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from engine.bkt import BKTParams

Style = tuple[float, float, float, float]


@dataclass(frozen=True)
class AidInfo:
    id: int
    concept_id: int  # primary concept the aid teaches
    aid_type: str
    style: Style
    difficulty: int
    default_order: int = 0
    title: str = ""


@dataclass
class Catalogue:
    syllabus: list[int]  # concept ids in course (syllabus) order
    prereqs: dict[int, set[int]]
    aids: dict[int, AidInfo]
    names: dict[int, str] = field(default_factory=dict)
    params: dict[int, BKTParams] = field(default_factory=dict)

    def __post_init__(self) -> None:
        from engine.graph import downstream_counts

        edges = [(c, p) for c, ps in self.prereqs.items() for p in ps]
        self.downstream = downstream_counts(self.syllabus, edges)
        self.order_index = {c: i for i, c in enumerate(self.syllabus)}
        by_concept: dict[int, list[AidInfo]] = defaultdict(list)
        for a in self.aids.values():
            by_concept[a.concept_id].append(a)
        for lst in by_concept.values():
            lst.sort(key=lambda a: (a.default_order, a.id))
        self.aids_by_concept = dict(by_concept)

    def bkt(self, concept_id: int) -> BKTParams:
        return self.params.get(concept_id, BKTParams())


@dataclass
class LearnerView:
    """Everything a policy needs to know about one learner at decision time."""

    mastery: dict[int, float]
    style: Style = (0.0, 0.0, 0.0, 0.0)
    n_uses: int = 0
    format_counts: dict[str, int] = field(default_factory=dict)
    recent_aids: set[int] = field(default_factory=set)  # cooldown: not recommended again yet
    used_aids: set[int] = field(default_factory=set)
    passed_check: set[int] = field(default_factory=set)  # concepts with a passed quick check
    aids_used_per_concept: dict[int, int] = field(default_factory=dict)
    cf_scores: dict[int, float] = field(default_factory=dict)  # raw CF score per aid
    help_scores: dict[int, float] = field(default_factory=dict)  # smoothed gain per aid
    best_gain_aid: dict[int, int] = field(default_factory=dict)  # concept -> aid that helped most


@dataclass
class Scored:
    aid: AidInfo
    concept_id: int
    parts: dict[str, float | None]
    score: float
    is_explore: bool = False
    reoffer: bool = False


@dataclass
class RecList:
    policy: str
    phase: str
    focus_concept: int | None
    items: list[Scored]
    weights: dict[str, float] = field(default_factory=dict)
