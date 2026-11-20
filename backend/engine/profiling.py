"""Learner profiling: engagement personas (K-Means) and a rule-based risk score.

Personas are learned with K-Means on standardised engagement features. The number of
clusters is chosen by silhouette score, and stability across random seeds is reported
with the adjusted Rand index (ARI). Clusters are then named from their centroids.

The live risk score is rule-based on purpose: each flag comes with a reason a teacher
can act on. The OULAD-trained classifier is evaluated separately, offline.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

FEATURES = (
    "active_days",
    "aid_uses",
    "completion_rate",
    "check_accuracy",
    "mean_mastery",
    "mastery_slope",
    "days_since_active",
    "share_visual",
    "share_practice",
    "share_text",
)


@dataclass
class PersonaResult:
    labels: list[str]  # persona key per learner, same order as the input
    k: int
    silhouette: float
    stability_ari: float
    centroids: dict[str, dict[str, float]]  # persona key -> feature means (original units)
    names: dict[str, str]  # persona key -> human label


def _name(z: Mapping[str, float]) -> str:
    """Name a cluster from its standardised centroid."""
    if z["days_since_active"] > 0.8 or z["aid_uses"] < -0.9:
        return "Disengaged"
    if z["check_accuracy"] < -0.7 and z["mean_mastery"] < -0.5:
        return "Struggling"
    if z["share_practice"] > 0.6:
        return "Practice-first"
    if z["share_visual"] > 0.6:
        return "Visual explorer"
    if z["share_text"] > 0.6:
        return "Steady reader"
    if z["mean_mastery"] > 0.6:
        return "High achiever"
    return "Steady learner"


def personas(
    rows: Sequence[Mapping[str, float]],
    *,
    k_range: Sequence[int] = (2, 3, 4, 5, 6),
    seeds: Sequence[int] = (0, 1, 2, 3, 4),
) -> PersonaResult | None:
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score, silhouette_score
    from sklearn.preprocessing import StandardScaler

    if len(rows) < 8:
        return None
    X = np.array([[float(r.get(f, 0.0)) for f in FEATURES] for r in rows])
    scaler = StandardScaler().fit(X)
    Z = scaler.transform(X)

    best = None
    for k in k_range:
        if k >= len(rows):
            break
        km = KMeans(n_clusters=k, n_init=10, random_state=seeds[0]).fit(Z)
        if len(set(km.labels_)) < 2:
            continue
        sil = float(silhouette_score(Z, km.labels_))
        if best is None or sil > best[1]:
            best = (k, sil, km)
    if best is None:
        return None
    k, sil, km = best
    aris = []
    for s in seeds[1:]:
        other = KMeans(n_clusters=k, n_init=10, random_state=s).fit(Z)
        aris.append(adjusted_rand_score(km.labels_, other.labels_))
    stability = float(np.mean(aris)) if aris else 1.0

    names: dict[str, str] = {}
    centroids: dict[str, dict[str, float]] = {}
    used: dict[str, int] = {}
    keys = []
    for c in range(k):
        z = dict(zip(FEATURES, km.cluster_centers_[c], strict=True))
        label = _name(z)
        used[label] = used.get(label, 0) + 1
        key = label.lower().replace(" ", "_").replace("-", "_") + (f"_{used[label]}" if used[label] > 1 else "")
        names[key] = label if used[label] == 1 else f"{label} {used[label]}"
        orig = scaler.inverse_transform(km.cluster_centers_[c : c + 1])[0]
        centroids[key] = {f: round(float(v), 3) for f, v in zip(FEATURES, orig, strict=True)}
        keys.append(key)
    labels = [keys[int(c)] for c in km.labels_]
    return PersonaResult(labels, k, round(sil, 4), round(stability, 4), centroids, names)


@dataclass
class Risk:
    score: float
    level: str
    reasons: list[str]


def risk(f: Mapping[str, float]) -> Risk:
    """Transparent rule-based risk score in [0, 1] with the reasons that triggered it."""
    reasons: list[str] = []
    score = 0.0
    days = f.get("days_since_active", 0.0)
    if days >= 7:
        score += 0.4
        reasons.append(f"Inactive for {int(days)} days")
    elif days >= 4:
        score += 0.15
        reasons.append(f"No activity for {int(days)} days")
    if f.get("n_answers", 0) >= 6 and f.get("check_accuracy", 1.0) < 0.45:
        score += 0.3
        reasons.append(f"Quick-check accuracy {f.get('check_accuracy', 0):.0%}")
    if f.get("mastery_slope", 0.0) < -0.01:
        score += 0.2
        reasons.append("Mastery falling over the last two weeks")
    if f.get("opens", 0) >= 5 and f.get("completion_rate", 1.0) < 0.35:
        score += 0.15
        reasons.append(f"Finishes only {f.get('completion_rate', 0):.0%} of aids opened")
    if f.get("mean_mastery", 1.0) < 0.25 and f.get("active_days", 0) >= 3:
        score += 0.15
        reasons.append("Low mastery across concepts")
    score = min(1.0, score)
    level = "high" if score >= 0.5 else "medium" if score >= 0.25 else "low"
    return Risk(round(score, 3), level, reasons)
