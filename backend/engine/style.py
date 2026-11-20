"""Learning-preference model on the Felder–Silverman dimensions.

A learner's preference is a vector in [-1, 1]^4:
    ar: +1 active      / -1 reflective
    si: +1 sensing     / -1 intuitive
    vv: +1 visual      / -1 verbal
    sg: +1 sequential  / -1 global

The questionnaire gives a *prior*. After each aid and its quick check the vector is
nudged along the aid's style direction: forward if the learner gained more than their
usual, backward if less. This is one step of online least squares for the model
"gain ~ s . s_aid", so a bad outcome on an aid that *matches* the current profile
weakens that preference (a difference-based rule, s_aid - s, would not move at all in
that case and could never correct a wrong questionnaire). A decaying learning rate, a
per-step cap and a gentle pull back to the prior keep noisy checks from swinging it.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

DIMS = ("ar", "si", "vv", "sg")
POLES = {
    "ar": ("active", "reflective"),
    "si": ("sensing", "intuitive"),
    "vv": ("visual", "verbal"),
    "sg": ("sequential", "global"),
}


def _vec(v: Sequence[float]) -> np.ndarray:
    a = np.asarray(v, dtype=float)
    if a.shape != (4,):
        raise ValueError("style vectors have 4 components")
    return a


# ----------------------------------------------------------------- questionnaire


@dataclass(frozen=True)
class Item:
    """A forced-choice item. `a_pole` says which pole option "a" points to (+1 or -1)."""

    key: str
    dim: str
    a_pole: int


def score_questionnaire(answers: Mapping[str, str], items: Sequence[Item]) -> list[float]:
    """Average of +/-1 votes per dimension. Unanswered items are ignored."""
    sums = dict.fromkeys(DIMS, 0.0)
    counts = dict.fromkeys(DIMS, 0)
    for it in items:
        choice = answers.get(it.key)
        if choice not in ("a", "b"):
            continue
        vote = it.a_pole if choice == "a" else -it.a_pole
        sums[it.dim] += vote
        counts[it.dim] += 1
    return [round(sums[d] / counts[d], 4) if counts[d] else 0.0 for d in DIMS]


def from_ils_scores(scores: Mapping[str, tuple[int, str]]) -> list[float]:
    """Convert official ILS results, e.g. {"vv": (7, "visual")}, to the [-1, 1] vector.

    ILS reports each dimension as an odd number 1–11 toward one pole.
    """
    out = []
    for d in DIMS:
        value, pole = scores.get(d, (1, POLES[d][0]))
        if value not in (1, 3, 5, 7, 9, 11):
            raise ValueError(f"ILS score for {d} must be an odd number from 1 to 11")
        if pole not in POLES[d]:
            raise ValueError(f"pole for {d} must be one of {POLES[d]}")
        sign = 1 if pole == POLES[d][0] else -1
        out.append(round(sign * value / 11, 4))
    return out


# ----------------------------------------------------------------- similarity


def similarity(learner: Sequence[float], aid: Sequence[float], tau: float = 0.35) -> float:
    """Match between a learner and an aid in [0, 1]; 0.5 means "no information".

    Plain cosine is unstable for balanced learners whose vector is near zero (tiny
    noise flips it to +/-1), so its effect is scaled by the learner vector's length:
        0.5 + 0.5 * cos(s_u, s_a) * min(1, |s_u| / tau)
    """
    u, a = _vec(learner), _vec(aid)
    nu, na = float(np.linalg.norm(u)), float(np.linalg.norm(a))
    if nu < 1e-9 or na < 1e-9:
        return 0.5
    cos = float(u @ a / (nu * na))
    return 0.5 + 0.5 * cos * min(1.0, nu / tau)


def cosine(u: Sequence[float], v: Sequence[float]) -> float:
    a, b = _vec(u), _vec(v)
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(a @ b / (na * nb))


# ----------------------------------------------------------------- update rule


@dataclass(frozen=True)
class StyleState:
    vector: tuple[float, float, float, float]
    prior: tuple[float, float, float, float]
    n_updates: int = 0
    ema_gain: float = 0.0


@dataclass(frozen=True)
class UpdateConfig:
    # Tuned in research/src/simulation.py under a "do no harm" rule: learning from outcomes
    # may not degrade an accurate questionnaire by more than 0.03 cosine.
    lr: float = 1.0
    max_step: float = 0.2
    prior_pull: float = 0.02
    ema_alpha: float = 0.2


def update(state: StyleState, aid_style: Sequence[float], gain: float, cfg: UpdateConfig | None = None) -> StyleState:
    """Move the preference vector after one aid + quick check.

    s <- clip(s + lr_n * (gain - EMA_gain) * s_aid + pull * (prior - s), -1, 1)
    with lr_n = lr / sqrt(1 + n) and each component's step capped at max_step.
    """
    cfg = cfg or UpdateConfig()
    s = _vec(state.vector)
    prior = _vec(state.prior)
    a = _vec(aid_style)
    lr_n = cfg.lr / math.sqrt(1 + state.n_updates)
    step = lr_n * (gain - state.ema_gain) * a
    step = np.clip(step, -cfg.max_step, cfg.max_step)
    new = np.clip(s + step + cfg.prior_pull * (prior - s), -1.0, 1.0)
    ema = (1 - cfg.ema_alpha) * state.ema_gain + cfg.ema_alpha * gain
    return StyleState(
        vector=tuple(round(float(x), 4) for x in new),  # type: ignore[arg-type]
        prior=state.prior,
        n_updates=state.n_updates + 1,
        ema_gain=round(float(ema), 4),
    )


def dominant_pole(vector: Sequence[float], min_strength: float = 0.25) -> tuple[str, str] | None:
    """The strongest pole, e.g. ("vv", "visual"), or None for a balanced learner."""
    v = _vec(vector)
    i = int(np.argmax(np.abs(v)))
    if abs(v[i]) < min_strength:
        return None
    d = DIMS[i]
    return d, POLES[d][0] if v[i] > 0 else POLES[d][1]
