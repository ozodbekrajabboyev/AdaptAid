"""Outcome-aware collaborative filtering.

The learner × aid matrix holds how much each aid *helped* each learner (positive
residual gain from the quick check, with completion and rating as weaker fallbacks; the
service builds those values). Two models:

- ItemKNN (cosine item–item similarity): works with very little data and is easy to
  explain. Used until there are `als_threshold` interactions.
- ALS (implicit library, Hu, Koren & Volinsky 2008): latent factors for larger data.
  New or unseen learners get a factor vector solved on the fly from their history
  (the same closed-form step ALS uses), so nobody waits for the nightly retrain.
"""

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np


@dataclass
class CFModel:
    kind: str  # "itemknn" or "als"
    item_ids: list[int]
    payload: dict[str, Any]
    n_interactions: int
    n_users: int

    def __post_init__(self) -> None:
        self._index = {aid: i for i, aid in enumerate(self.item_ids)}

    def score(self, history: Mapping[int, float], candidates: Sequence[int]) -> dict[int, float]:
        """Raw scores for candidate aids given one learner's history {aid: value}."""
        hist = {self._index[a]: v for a, v in history.items() if a in self._index and v > 0}
        cand = [(a, self._index[a]) for a in candidates if a in self._index]
        if not hist or not cand:
            return {}
        if self.kind == "itemknn":
            sim: np.ndarray = self.payload["sim"]
            h_idx = np.array(list(hist))
            h_val = np.array(list(hist.values()))
            out = {}
            for aid, j in cand:
                s = sim[j, h_idx]
                denom = np.abs(s).sum()
                out[aid] = float(s @ h_val / denom) if denom > 1e-9 else 0.0
            return out
        Y: np.ndarray = self.payload["item_factors"]
        reg: float = self.payload["regularization"]
        alpha: float = self.payload["alpha"]
        x_u = _solve_user(Y, hist, reg, alpha)
        return {aid: float(Y[j] @ x_u) for aid, j in cand}


def _solve_user(Y: np.ndarray, hist: Mapping[int, float], reg: float, alpha: float) -> np.ndarray:
    """Implicit-ALS user step: x = (Y'Y + Y'(C-I)Y + reg I)^-1 Y'C p, with c = 1 + alpha * r."""
    f = Y.shape[1]
    A = Y.T @ Y + reg * np.eye(f)
    b = np.zeros(f)
    for j, r in hist.items():
        c = 1.0 + alpha * r
        A += (c - 1.0) * np.outer(Y[j], Y[j])
        b += c * Y[j]
    return np.linalg.solve(A, b)


def _matrix(rows: Sequence[tuple[int, int, float]]):
    from scipy.sparse import csr_matrix

    users = sorted({u for u, _, v in rows if v > 0})
    items = sorted({i for _, i, v in rows if v > 0})
    ui = {u: k for k, u in enumerate(users)}
    ii = {i: k for k, i in enumerate(items)}
    agg: dict[tuple[int, int], float] = {}
    for u, i, v in rows:
        if v > 0:
            agg[(ui[u], ii[i])] = max(agg.get((ui[u], ii[i]), 0.0), v)
    r, c = zip(*agg.keys(), strict=True) if agg else ((), ())
    m = csr_matrix((list(agg.values()), (r, c)), shape=(len(users), len(items)), dtype=np.float32)
    return m, users, items


def train(
    rows: Sequence[tuple[int, int, float]],
    *,
    als_threshold: int = 300,
    factors: int = 16,
    regularization: float = 0.1,
    alpha: float = 10.0,
    iterations: int = 25,
    seed: int = 7,
) -> CFModel | None:
    """rows: (learner id, aid id, helped value). Returns None when there is nothing to learn from."""
    m, users, items = _matrix(rows)
    n = int(m.nnz)
    if n == 0 or len(items) < 2 or len(users) < 2:
        return None
    if n < als_threshold:
        dense = m.toarray()
        norms = np.linalg.norm(dense, axis=0)
        norms[norms == 0] = 1.0
        sim = (dense.T @ dense) / np.outer(norms, norms)
        np.fill_diagonal(sim, 0.0)
        return CFModel("itemknn", items, {"sim": sim.astype(np.float32)}, n, len(users))

    from implicit.als import AlternatingLeastSquares

    model = AlternatingLeastSquares(
        factors=factors, regularization=regularization, iterations=iterations, random_state=seed,
        calculate_training_loss=False,
    )
    model.fit((m * alpha).tocsr(), show_progress=False)
    item_factors = np.asarray(model.item_factors, dtype=np.float64)
    return CFModel(
        "als",
        items,
        {"item_factors": item_factors, "regularization": regularization, "alpha": alpha},
        n,
        len(users),
    )


def dumps(model: CFModel) -> bytes:
    buf = io.BytesIO()
    joblib.dump(
        {"kind": model.kind, "item_ids": model.item_ids, "payload": model.payload,
         "n_interactions": model.n_interactions, "n_users": model.n_users},
        buf,
    )
    return buf.getvalue()


def loads(data: bytes) -> CFModel:
    d = joblib.load(io.BytesIO(data))
    return CFModel(d["kind"], d["item_ids"], d["payload"], d["n_interactions"], d["n_users"])
