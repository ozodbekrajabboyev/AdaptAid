"""Class-level teaching-aid suggestions for teachers (group recommendation).

For each concept where a meaningful share of the class is stuck (the concept is unlocked
for them but still below the target), aids are
scored for every student and combined with "average without misery" (Masthoff, 2011):
rank by the class average, but drop any aid that would suit more than a quarter of the
class poorly. Students who are better served by a different format are listed so the
teacher can hand them an alternative.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np

from engine.bkt import UNLOCK
from engine.signals import level_fit, percentile_ranks
from engine.style import dominant_pole, similarity
from engine.types import AidInfo, Catalogue


@dataclass
class StudentView:
    user_id: int
    name: str
    mastery: Mapping[int, float]
    style: tuple[float, float, float, float]


@dataclass
class AidSuggestion:
    aid: AidInfo
    class_score: float
    share_poor_fit: float
    mean_gain: float | None


@dataclass
class AltGroup:
    aid: AidInfo
    students: list[tuple[int, str]]


@dataclass
class ConceptSuggestion:
    concept_id: int
    concept_name: str
    share_below: float
    n_below: int
    n_students: int
    class_lean: str | None
    aids: list[AidSuggestion]
    alternatives: list[AltGroup] = field(default_factory=list)


def _student_score(s: StudentView, aid: AidInfo, concept: int, help_pct: float | None) -> float:
    p = s.mastery.get(concept, 0.0)
    base = 0.55 * similarity(s.style, aid.style) + 0.30 * level_fit(aid.difficulty, p)
    return base + 0.15 * (help_pct if help_pct is not None else 0.5)


def class_suggestions(
    students: Sequence[StudentView],
    catalogue: Catalogue,
    aid_gain: Mapping[int, float],
    *,
    below: float = 0.6,
    min_share: float = 0.2,
    poor_fit: float = 0.45,
    misery_share: float = 0.25,
    top_aids: int = 3,
    max_concepts: int = 4,
) -> list[ConceptSuggestion]:
    if not students:
        return []
    out: list[ConceptSuggestion] = []
    for concept in catalogue.syllabus:
        aids = catalogue.aids_by_concept.get(concept, [])
        if not aids:
            continue
        # "Stuck" = the concept is unlocked for the student (prerequisites at the unlock level)
        # but still below the target. Students who have not reached it yet are not stuck.
        prereqs = catalogue.prereqs.get(concept, set())
        struggling = [
            s for s in students
            if s.mastery.get(concept, 0.0) < below and all(s.mastery.get(p, 0.0) >= UNLOCK for p in prereqs)
        ]
        share = len(struggling) / len(students)
        if share < min_share or not struggling:
            continue
        help_pct = percentile_ranks([aid_gain.get(a.id) for a in aids])
        scores = np.array([[_student_score(s, a, concept, help_pct[j]) for j, a in enumerate(aids)] for s in struggling])
        every = []
        for j, a in enumerate(aids):
            col = scores[:, j]
            poor = float((col < poor_fit).mean())
            every.append(AidSuggestion(a, round(float(col.mean()), 4), round(poor, 3), aid_gain.get(a.id)))
        suggestions = [x for x in every if x.share_poor_fit <= misery_share]
        if not suggestions:
            # A divided class: no aid suits enough students. Fall back to the least-misery aids
            # and rely on the alternatives list below for the students they don't suit.
            least = min(x.share_poor_fit for x in every)
            suggestions = [x for x in every if x.share_poor_fit == least]
        suggestions.sort(key=lambda x: -x.class_score)
        suggestions = suggestions[:top_aids]

        alternatives: list[AltGroup] = []
        if suggestions:
            main = suggestions[0].aid
            main_j = aids.index(main)
            groups: dict[int, list[tuple[int, str]]] = {}
            for i, s in enumerate(struggling):
                best_j = int(np.argmax(scores[i]))
                if aids[best_j].aid_type != main.aid_type and scores[i, best_j] - scores[i, main_j] > 0.08:
                    groups.setdefault(best_j, []).append((s.user_id, s.name))
            alternatives = [AltGroup(aids[j], lst) for j, lst in sorted(groups.items(), key=lambda kv: -len(kv[1]))][:2]

        mean_style = tuple(np.mean([s.style for s in struggling], axis=0).tolist())
        lean = dominant_pole(mean_style, min_strength=0.15)
        out.append(
            ConceptSuggestion(
                concept_id=concept,
                concept_name=catalogue.names.get(concept, str(concept)),
                share_below=round(share, 3),
                n_below=len(struggling),
                n_students=len(students),
                class_lean=lean[1] if lean else None,
                aids=suggestions,
                alternatives=alternatives,
            )
        )
    out.sort(key=lambda c: -c.share_below)
    return out[:max_concepts]
