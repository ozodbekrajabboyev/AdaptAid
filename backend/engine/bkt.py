"""Bayesian Knowledge Tracing (Corbett & Anderson, 1994).

Each concept is a two-state hidden Markov model: the learner either knows it (L) or not.
Four parameters per concept:
    prior  P(L0)  probability the concept is known before any practice
    learn  P(T)   probability of moving from unknown to known after an opportunity
    guess  P(G)   probability of a correct answer while not knowing
    slip   P(S)   probability of a wrong answer while knowing

After each answer the posterior P(L | answer) is computed with Bayes' rule, then the
learn step adds the chance the learner acquired the concept during this opportunity.
A concept counts as mastered at P(L) >= 0.95, the conventional BKT threshold.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

MASTERED = 0.95
UNLOCK = 0.70
_EPS = 1e-6


@dataclass(frozen=True)
class BKTParams:
    prior: float = 0.2
    learn: float = 0.15
    guess: float = 0.2
    slip: float = 0.1

    def as_dict(self) -> dict[str, float]:
        return {"prior": self.prior, "learn": self.learn, "guess": self.guess, "slip": self.slip}


def predict_correct(p_known: float, params: BKTParams) -> float:
    """P(next answer correct) = P(L)(1 - S) + (1 - P(L)) G."""
    return p_known * (1.0 - params.slip) + (1.0 - p_known) * params.guess


def posterior(p_known: float, correct: bool, params: BKTParams) -> float:
    """P(L | observed answer) by Bayes' rule, before the learn step."""
    if correct:
        num = p_known * (1.0 - params.slip)
        den = num + (1.0 - p_known) * params.guess
    else:
        num = p_known * params.slip
        den = num + (1.0 - p_known) * (1.0 - params.guess)
    return num / den if den > 0 else p_known


def update(p_known: float, correct: bool, params: BKTParams) -> float:
    """One BKT step: Bayesian evidence update, then the learning transition."""
    post = posterior(p_known, correct, params)
    return post + (1.0 - post) * params.learn


def trace(answers: Sequence[bool], params: BKTParams, p0: float | None = None) -> tuple[list[float], float]:
    """Run BKT over a sequence.

    Returns the one-step-ahead predictions P(correct) made *before* seeing each answer
    (what you score with AUC) and the final P(L).
    """
    p = params.prior if p0 is None else p0
    preds: list[float] = []
    for a in answers:
        preds.append(predict_correct(p, params))
        p = update(p, bool(a), params)
    return preds, p


# --------------------------------------------------------------------------- fitting


def _pad(sequences: Sequence[Sequence[int]], max_len: int | None) -> tuple[np.ndarray, np.ndarray]:
    seqs = [list(s)[:max_len] if max_len else list(s) for s in sequences if len(s) > 0]
    if not seqs:
        raise ValueError("No sequences to fit")
    length = max(len(s) for s in seqs)
    obs = np.zeros((len(seqs), length), dtype=np.float64)
    mask = np.zeros((len(seqs), length), dtype=bool)
    for i, s in enumerate(seqs):
        obs[i, : len(s)] = s
        mask[i, : len(s)] = True
    return obs, mask


def _grid_loglik(obs: np.ndarray, mask: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Log-likelihood of all sequences for every parameter combination at once.

    obs, mask: (N students, T steps). grid: (G, 4) columns prior, learn, guess, slip.
    Returns (G,) total log-likelihoods. Vectorised over grid points and students.
    """
    prior, learn, guess, slip = (grid[:, i : i + 1] for i in range(4))  # each (G, 1)
    p = np.broadcast_to(prior, (grid.shape[0], obs.shape[0])).copy()  # (G, N)
    ll = np.zeros(grid.shape[0])
    for t in range(obs.shape[1]):
        o = obs[:, t][None, :]
        m = mask[:, t][None, :]
        pred = np.clip(p * (1 - slip) + (1 - p) * guess, _EPS, 1 - _EPS)
        ll += np.where(m, o * np.log(pred) + (1 - o) * np.log(1 - pred), 0.0).sum(axis=1)
        num_c = p * (1 - slip)
        num_w = p * slip
        post = np.where(o == 1, num_c / pred, num_w / (1 - pred))
        nxt = post + (1 - post) * learn
        p = np.where(m, nxt, p)
    return ll


def _grid(prior, learn, guess, slip) -> np.ndarray:
    mesh = np.meshgrid(prior, learn, guess, slip, indexing="ij")
    return np.stack([m.ravel() for m in mesh], axis=1)


@dataclass(frozen=True)
class FitResult:
    params: BKTParams
    loglik: float
    n_sequences: int
    n_answers: int


def fit_brute_force(
    sequences: Sequence[Sequence[int]],
    *,
    max_guess: float = 0.3,
    max_slip: float = 0.3,
    max_len: int | None = 200,
    chunk: int = 4000,
) -> FitResult:
    """Bounded brute-force BKT fit (Baker et al.), coarse grid then a finer local grid.

    Guess and slip are capped at 0.3 to avoid degenerate solutions where "knowing"
    a concept would mean answering worse than chance.
    """
    obs, mask = _pad(sequences, max_len)

    def best_of(grid: np.ndarray) -> tuple[np.ndarray, float]:
        best_ll, best_row = -np.inf, grid[0]
        for start in range(0, len(grid), chunk):
            part = grid[start : start + chunk]
            ll = _grid_loglik(obs, mask, part)
            i = int(np.argmax(ll))
            if ll[i] > best_ll:
                best_ll, best_row = float(ll[i]), part[i]
        return best_row, best_ll

    coarse = _grid(
        np.linspace(0.05, 0.95, 10),
        np.linspace(0.02, 0.5, 9),
        np.linspace(0.02, max_guess, 7),
        np.linspace(0.02, max_slip, 7),
    )
    row, _ = best_of(coarse)

    def around(center: float, step: float, lo: float, hi: float) -> np.ndarray:
        return np.clip(np.linspace(center - step, center + step, 7), lo, hi)

    fine = _grid(
        around(row[0], 0.05, 0.01, 0.99),
        around(row[1], 0.03, 0.005, 0.6),
        around(row[2], 0.025, 0.005, max_guess),
        around(row[3], 0.025, 0.005, max_slip),
    )
    row, ll = best_of(np.unique(fine, axis=0))
    return FitResult(
        params=BKTParams(*(round(float(x), 4) for x in row)),
        loglik=ll,
        n_sequences=int(obs.shape[0]),
        n_answers=int(mask.sum()),
    )
