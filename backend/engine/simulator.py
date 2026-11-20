"""Simulated learners for testing the adaptive loop before (and alongside) real users.

Each synthetic learner has hidden ground truth the platform never sees:
  - which concepts it really knows,
  - a true format preference vector,
  - how fast it learns, how often it shows up, and its guess/slip behaviour.

The platform side runs the real engine: BKT mastery updates from quick-check answers,
residual gain, the style update, aid statistics, collaborative filtering and the
policies. So a simulation exercises the same code the app runs.

`affinity_effect` controls how much a matched format actually helps a learner learn.
With affinity_effect = 0, style matching *cannot* help; the evaluation reports every
setting so the claim is only "no harm when style does not matter, gain when it does".
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np

from engine import cf as cf_mod
from engine.bkt import MASTERED, BKTParams, update
from engine.graph import layers
from engine.signals import residual_gain, smoothed_mean
from engine.style import StyleState, UpdateConfig, cosine
from engine.style import update as style_update
from engine.types import AidInfo, Catalogue, LearnerView

LEARNER_TYPES: dict[str, dict] = {
    "visual_explorer": {"pref": (0.3, 0.1, 0.85, 0.2), "learn_mult": 1.0, "engagement": 0.9, "ability": 0.1},
    "practice_first": {"pref": (0.85, 0.6, 0.0, 0.3), "learn_mult": 1.0, "engagement": 0.85, "ability": 0.1},
    "steady": {"pref": (-0.5, 0.2, -0.6, 0.7), "learn_mult": 1.0, "engagement": 0.85, "ability": 0.0},
    "struggling": {"pref": (0.2, 0.7, 0.5, 0.6), "learn_mult": 0.55, "engagement": 0.7, "ability": -0.4},
    "dropout": {"pref": (0.0, -0.3, 0.4, -0.4), "learn_mult": 0.9, "engagement": 0.8, "ability": 0.0, "decay": 0.06},
}
DEFAULT_MIX = {"visual_explorer": 0.25, "practice_first": 0.25, "steady": 0.25, "struggling": 0.15, "dropout": 0.10}


@dataclass
class WorldConfig:
    affinity_effect: float = 0.6
    base_learn: float = 0.14
    prereq_penalty: float = 0.3
    check_learn: float = 0.02  # practice/retest effect of answering a check
    guess: float = 0.2
    slip: float = 0.1
    questionnaire_noise: float = 0.3
    prior_mode: str = "noisy"  # "noisy" | "none" | "wrong"
    check_size: int = 3
    position_bias: tuple[float, ...] = (0.45, 0.25, 0.15, 0.1, 0.05)
    cooldown: int = 4  # an aid is not recommended again within this many uses
    cf_every: int = 5  # retrain CF every n steps
    style_cfg: UpdateConfig = field(default_factory=UpdateConfig)


@dataclass
class SimLearner:
    uid: int
    kind: str
    pref: np.ndarray
    learn_mult: float
    engagement: float
    ability: float
    decay: float
    known: dict[int, bool]
    # platform-side state
    mastery: dict[int, float]
    style: StyleState
    n_uses: int = 0
    format_counts: dict[str, int] = field(default_factory=dict)
    recent: deque = field(default_factory=lambda: deque(maxlen=4))
    passed: set[int] = field(default_factory=set)
    per_concept: dict[int, int] = field(default_factory=dict)
    history: dict[int, float] = field(default_factory=dict)
    gains_by_aid: dict[int, float] = field(default_factory=dict)
    steps_active: int = 0


def make_learners(
    n: int, cat: Catalogue, cfg: WorldConfig, rng: np.random.Generator, mix: dict[str, float] | None = None
) -> list[SimLearner]:
    mix = mix or DEFAULT_MIX
    kinds = list(mix)
    probs = np.array([mix[k] for k in kinds]) / sum(mix.values())
    depth = layers(cat.syllabus, [(c, p) for c, ps in cat.prereqs.items() for p in ps])
    learners = []
    for uid in range(n):
        kind = kinds[int(rng.choice(len(kinds), p=probs))]
        t = LEARNER_TYPES[kind]
        pref = np.clip(np.array(t["pref"]) + rng.normal(0, 0.12, 4), -1, 1)
        base_known = 0.35 + 0.15 * t["ability"]
        known = {c: bool(rng.random() < max(0.02, base_known * (0.45 ** depth[c]))) for c in cat.syllabus}
        if cfg.prior_mode == "none":
            reported = np.zeros(4)
        elif cfg.prior_mode == "wrong":
            reported = -0.8 * pref
        else:
            reported = np.clip(pref + rng.normal(0, cfg.questionnaire_noise, 4), -1, 1)
        prior = tuple(round(float(x), 4) for x in reported)
        learners.append(
            SimLearner(
                uid=uid,
                kind=kind,
                pref=pref,
                learn_mult=t["learn_mult"],
                engagement=t["engagement"],
                ability=t["ability"],
                decay=t.get("decay", 0.0),
                known=known,
                mastery={c: cat.bkt(c).prior for c in cat.syllabus},
                style=StyleState(vector=prior, prior=prior),  # type: ignore[arg-type]
                recent=deque(maxlen=cfg.cooldown),
            )
        )
    return learners


def diagnose(learner: SimLearner, cat: Catalogue, cfg: WorldConfig, rng: np.random.Generator) -> None:
    """One diagnostic question per concept seeds BKT, as the onboarding quiz does."""
    for c in cat.syllabus:
        correct = _answer(learner, c, cfg, rng)
        learner.mastery[c] = update(learner.mastery[c], correct, cat.bkt(c))


def _answer(learner: SimLearner, concept: int, cfg: WorldConfig, rng: np.random.Generator) -> bool:
    p = 1 - cfg.slip if learner.known[concept] else cfg.guess
    return bool(rng.random() < p)


def p_learn(learner: SimLearner, aid: AidInfo, cat: Catalogue, cfg: WorldConfig) -> float:
    """Hidden truth: chance this aid teaches this learner the concept."""
    match = cosine(aid.style, learner.pref)  # -1..1
    base = cfg.base_learn * learner.learn_mult * (1 + cfg.affinity_effect * match)
    target = 2.5 + 1.5 * learner.ability
    base *= float(np.exp(-((aid.difficulty - target) ** 2) / (2 * 1.6**2)))
    if not all(learner.known[p] for p in cat.prereqs.get(aid.concept_id, set())):
        base *= cfg.prereq_penalty
    return float(np.clip(base, 0.005, 0.9))


def view_of(
    learner: SimLearner, cf_scores: dict[int, float], help_scores: dict[int, float], cat: Catalogue | None = None
) -> LearnerView:
    best_gain: dict[int, int] = {}
    if cat is not None:
        best_val: dict[int, float] = {}
        for aid_id, value in learner.history.items():
            c = cat.aids[aid_id].concept_id
            if value > best_val.get(c, -1.0):
                best_val[c], best_gain[c] = value, aid_id
    return LearnerView(
        mastery=dict(learner.mastery),
        style=learner.style.vector,
        n_uses=learner.n_uses,
        format_counts=dict(learner.format_counts),
        recent_aids=set(learner.recent),
        used_aids=set(learner.history),
        passed_check=set(learner.passed),
        aids_used_per_concept=dict(learner.per_concept),
        cf_scores=cf_scores,
        help_scores=help_scores,
        best_gain_aid=best_gain,
    )


@dataclass
class SimResult:
    policy: str
    known_curve: list[float]  # mean share of concepts truly known, per step
    style_curve: list[float]  # mean cos(learned style, true preference), per step
    bkt_error_curve: list[float]  # mean |P(L) - truth|, per step
    final_known: float
    steps_to_all: float  # mean steps until every concept is truly known (capped)
    mean_gain: float
    by_type: dict[str, float]


PolicyLike = object


def run(
    policy_factory: Callable[[], PolicyLike],
    cat: Catalogue,
    *,
    n_learners: int = 60,
    steps: int = 40,
    cfg: WorldConfig | None = None,
    seed: int = 0,
    check_only: bool = False,
    mix: dict[str, float] | None = None,
) -> SimResult:
    """Simulate `steps` sessions for a cohort under one policy.

    check_only=True replaces the aid with nothing, to measure the retest effect of the
    quick check alone.
    """
    cfg = cfg or WorldConfig()
    rng = np.random.default_rng(seed)
    learners = make_learners(n_learners, cat, cfg, rng, mix)
    for ln in learners:
        diagnose(ln, cat, cfg, rng)
    policy = policy_factory()

    aid_sum: dict[int, float] = {}
    aid_n: dict[int, int] = {}
    model = None
    known_curve, style_curve, err_curve, all_gains = [], [], [], []
    done_at = {ln.uid: None for ln in learners}

    for t in range(steps):
        if t % cfg.cf_every == 0:
            rows = [(ln.uid, a, v) for ln in learners for a, v in ln.history.items()]
            model = cf_mod.train(rows, als_threshold=10_000)  # item-kNN is enough at this scale
        help_scores = {a: smoothed_mean(aid_sum[a], aid_n[a]) for a in aid_sum}
        for ln in learners:
            engagement = ln.engagement * (1 - ln.decay) ** t
            if rng.random() > engagement:
                continue
            ln.steps_active += 1
            cands = [a.id for a in cat.aids.values()]
            cf_scores = model.score(ln.history, cands) if model else {}
            view = view_of(ln, cf_scores, help_scores, cat)
            rec = policy.recommend(view, cat, k=5)  # type: ignore[attr-defined]
            if not rec.items:
                continue
            bias = np.array(cfg.position_bias[: len(rec.items)])
            pick = rec.items[int(rng.choice(len(rec.items), p=bias / bias.sum()))]
            aid, concept = pick.aid, pick.concept_id
            params = cat.bkt(concept)
            p_open = ln.mastery[concept]

            if not check_only and not ln.known[concept] and rng.random() < p_learn(ln, aid, cat, cfg):
                ln.known[concept] = True
            answers = []
            for _ in range(cfg.check_size):
                ans = _answer(ln, concept, cfg, rng)
                answers.append(ans)
                ln.mastery[concept] = update(ln.mastery[concept], ans, params)
                if not ln.known[concept] and rng.random() < cfg.check_learn:
                    ln.known[concept] = True
            gain = residual_gain(p_open, answers, params)
            all_gains.append(gain)
            if not check_only:
                ln.style = style_update(ln.style, aid.style, gain, cfg.style_cfg)
                ln.history[aid.id] = max(ln.history.get(aid.id, 0.0), max(gain, 0.0))
                aid_sum[aid.id] = aid_sum.get(aid.id, 0.0) + gain
                aid_n[aid.id] = aid_n.get(aid.id, 0) + 1
                ln.n_uses += 1
                ln.format_counts[aid.aid_type] = ln.format_counts.get(aid.aid_type, 0) + 1
                ln.recent.append(aid.id)
                ln.per_concept[concept] = ln.per_concept.get(concept, 0) + 1
            if sum(answers) >= 2:
                ln.passed.add(concept)
            if done_at[ln.uid] is None and all(ln.known.values()):
                done_at[ln.uid] = t + 1

        known_curve.append(float(np.mean([np.mean(list(ln.known.values())) for ln in learners])))
        style_curve.append(float(np.mean([cosine(ln.style.vector, ln.pref) for ln in learners])))
        err_curve.append(
            float(np.mean([np.mean([abs(ln.mastery[c] - ln.known[c]) for c in cat.syllabus]) for ln in learners]))
        )

    by_type: dict[str, list[float]] = {}
    for ln in learners:
        by_type.setdefault(ln.kind, []).append(float(np.mean(list(ln.known.values()))))
    return SimResult(
        policy=getattr(policy, "name", "policy") + ("+check_only" if check_only else ""),
        known_curve=known_curve,
        style_curve=style_curve,
        bkt_error_curve=err_curve,
        final_known=known_curve[-1] if known_curve else 0.0,
        steps_to_all=float(np.mean([d if d is not None else steps + 1 for d in done_at.values()])),
        mean_gain=float(np.mean(all_gains)) if all_gains else 0.0,
        by_type={k: float(np.mean(v)) for k, v in by_type.items()},
    )


def demo_catalogue(n_concepts: int = 8, aids_per_concept: int = 6, seed: int = 0) -> Catalogue:
    """A small synthetic course for tests and quick experiments."""
    rng = np.random.default_rng(seed)
    formats = {
        "animation": (0.3, 0.1, 0.9, 0.4),
        "video": (-0.2, 0.0, 0.5, 0.4),
        "notes": (-0.5, 0.0, -0.8, 0.6),
        "worked_example": (0.1, 0.8, 0.0, 0.8),
        "practice": (0.9, 0.6, -0.1, 0.3),
        "concept_map": (-0.1, -0.5, 0.7, -0.8),
        "article": (-0.4, -0.3, -0.7, 0.2),
    }
    concepts = list(range(1, n_concepts + 1))
    prereqs = {c: ({c - 1} if c > 1 else set()) for c in concepts}
    if n_concepts >= 4:
        prereqs[4] = {2}
        prereqs[3] = {1}
    aids: dict[int, AidInfo] = {}
    aid_id = 1
    names = list(formats)
    for c in concepts:
        for j in range(aids_per_concept):
            fmt = names[j % len(names)]
            style = tuple(float(np.clip(x + rng.normal(0, 0.1), -1, 1)) for x in formats[fmt])
            aids[aid_id] = AidInfo(aid_id, c, fmt, style, int(rng.integers(1, 6)), default_order=j)  # type: ignore[arg-type]
            aid_id += 1
    return Catalogue(
        syllabus=concepts,
        prereqs=prereqs,
        aids=aids,
        names={c: f"Concept {c}" for c in concepts},
        params={c: BKTParams() for c in concepts},
    )


def summarise(results: Sequence[SimResult]) -> list[dict]:
    return [
        {
            "policy": r.policy,
            "final_known": round(r.final_known, 4),
            "steps_to_all": round(r.steps_to_all, 2),
            "mean_gain": round(r.mean_gain, 4),
            "final_style_cos": round(r.style_curve[-1], 4) if r.style_curve else None,
        }
        for r in results
    ]


__all__ = ["MASTERED", "WorldConfig", "SimLearner", "SimResult", "run", "demo_catalogue", "make_learners", "summarise"]
