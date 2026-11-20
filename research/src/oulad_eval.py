"""OULAD evaluations: at-risk classifier, engagement personas, offline collaborative filtering.

At-risk classifier
  Features use only the first CUTOFF days of each presentation (clicks by activity type,
  active days, assessments submitted by then, prior attempts, credits). Students who had
  already withdrawn by the cutoff are excluded: there is nothing left to predict for them.
  Train on the 2013 presentations, test on 2014 (a later cohort), so the test set is
  genuinely in the future. Target: final result Withdrawn or Fail. Classes are imbalanced,
  so PR-AUC is reported next to ROC-AUC, F1 and recall.

Personas
  K-Means on standardised engagement shares (k = 3..6, chosen by silhouette), with stability
  across seeds (adjusted Rand index), on the 2014 presentations.

Offline collaborative filtering
  Learner x material clicks in the largest presentation. Per-student time split: the first
  80% of the materials a student opened are training data, the last 20% are what we try to
  predict; training items are removed from the candidates. Metrics at 5: precision,
  recall, NDCG, hit rate, and catalogue coverage.

Usage: backend/.venv/bin/python -m research.src.oulad_eval
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from engine import cf as cf_mod
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    adjusted_rand_score,
    average_precision_score,
    f1_score,
    recall_score,
    roc_auc_score,
    silhouette_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from research.src.datasets import oulad

OUT = Path(__file__).resolve().parents[1] / "outputs"
CUTOFF = 42  # days since presentation start (6 weeks)
GROUPS = {
    "resource": "content", "oucontent": "content", "page": "content", "subpage": "content",
    "url": "links", "dataplus": "links",
    "forumng": "forum", "oucollaborate": "forum", "ouelluminate": "forum", "ouwiki": "forum",
    "quiz": "quiz", "externalquiz": "quiz", "questionnaire": "quiz",
    "homepage": "homepage",
}
EDU = {"No Formal quals": 0, "Lower Than A Level": 1, "A Level or Equivalent": 2, "HE Qualification": 3,
       "Post Graduate Qualification": 4}


def load_clicks() -> pd.DataFrame:
    vle = oulad("vle", usecols=["id_site", "activity_type"])
    vle["group"] = vle["activity_type"].map(GROUPS).fillna("other")
    sv = oulad("studentVle", dtype={"id_student": "int32", "id_site": "int32", "date": "int16", "sum_click": "int32"})
    return sv.merge(vle[["id_site", "activity_type", "group"]], on="id_site", how="left")


# ----------------------------------------------------------------------------- risk


def risk_features(clicks: pd.DataFrame) -> pd.DataFrame:
    keys = ["code_module", "code_presentation", "id_student"]
    info = oulad("studentInfo")
    reg = oulad("studentRegistration")
    info = info.merge(reg, on=keys, how="left")
    info = info[~(info["date_unregistration"].notna() & (info["date_unregistration"] <= CUTOFF))]

    early = clicks[clicks["date"] <= CUTOFF]
    by_group = early.pivot_table(index=keys, columns="group", values="sum_click", aggfunc="sum", fill_value=0)
    by_group.columns = [f"clicks_{c}" for c in by_group.columns]
    activity = early.groupby(keys).agg(active_days=("date", "nunique"), clicks_total=("sum_click", "sum"))
    late = early[early["date"] > CUTOFF - 14].groupby(keys)["sum_click"].sum().rename("clicks_last2w")

    asm = oulad("assessments")
    sa = oulad("studentAssessment").merge(asm, on="id_assessment")
    sa = sa[(sa["date"] <= CUTOFF) & (sa["assessment_type"] != "Exam")]
    sa["late"] = (sa["date_submitted"] > sa["date"]).astype(int)
    a_feat = sa.groupby(keys).agg(n_submitted=("score", "size"), mean_score=("score", "mean"), n_late=("late", "sum"))
    due = asm[(asm["date"] <= CUTOFF) & (asm["assessment_type"] != "Exam")].groupby(["code_module", "code_presentation"]).size()

    X = info.set_index(keys).join([by_group, activity, late, a_feat], how="left")
    X = X.fillna({c: 0 for c in X.columns if c.startswith("clicks") or c in ("active_days", "n_submitted", "n_late")})
    X["mean_score"] = X["mean_score"].fillna(0)
    X["n_due"] = [due.get((m, p), 0) for m, p, _ in X.index]
    X["n_missing"] = (X["n_due"] - X["n_submitted"]).clip(lower=0)
    X["edu"] = X["highest_education"].map(EDU).fillna(1)
    X["target"] = X["final_result"].isin(["Withdrawn", "Fail"]).astype(int)
    X["year"] = X.index.get_level_values("code_presentation").str[:4]
    return X


def run_risk(clicks: pd.DataFrame) -> dict:
    X = risk_features(clicks)
    feats = [c for c in X.columns if c.startswith("clicks")] + [
        "active_days", "n_submitted", "mean_score", "n_late", "n_missing", "num_of_prev_attempts", "studied_credits", "edu"]
    train, test = X[X["year"] == "2013"], X[X["year"] == "2014"]
    models = {
        "Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")),
        "Random forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced", n_jobs=-1, random_state=0),
        "Gradient boosting": HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, class_weight="balanced", random_state=0),
    }
    table = []
    importances = {}
    for name, m in models.items():
        m.fit(train[feats], train["target"])
        p = m.predict_proba(test[feats])[:, 1]
        yhat = (p >= 0.5).astype(int)
        table.append({"model": name, "roc_auc": round(roc_auc_score(test["target"], p), 4),
                      "pr_auc": round(average_precision_score(test["target"], p), 4),
                      "f1": round(f1_score(test["target"], yhat), 4), "recall_at_risk": round(recall_score(test["target"], yhat), 4)})
        if name == "Random forest":
            importances = dict(sorted(zip(feats, m.feature_importances_.round(4).tolist(), strict=True), key=lambda kv: -kv[1])[:8])
    return {
        "note": (f"OULAD, features from the first {CUTOFF} days only; trained on 2013 presentations "
                 f"({len(train)} students), tested on 2014 ({len(test)} students). At-risk = Withdrawn or Fail "
                 f"({test['target'].mean():.0%} of the test set). Students who withdrew before day {CUTOFF} are excluded."),
        "table": table,
        "base_rate": round(float(test["target"].mean()), 4),
        "top_features_random_forest": importances,
    }


# ----------------------------------------------------------------------------- personas


def run_personas(clicks: pd.DataFrame) -> dict:
    keys = ["code_module", "code_presentation", "id_student"]
    c = clicks[clicks["code_presentation"].str.startswith("2014")]
    by_group = c.pivot_table(index=keys, columns="group", values="sum_click", aggfunc="sum", fill_value=0)
    total = by_group.sum(axis=1)
    keep = total >= 50
    shares = by_group[keep].div(total[keep], axis=0)
    shares.columns = [f"share_{x}" for x in shares.columns]
    act = c.groupby(keys).agg(active_days=("date", "nunique"))
    F = shares.join(act).assign(log_clicks=np.log1p(total[keep]))
    Z = StandardScaler().fit_transform(F)
    rng = np.random.default_rng(0)
    sample = rng.choice(len(Z), size=min(6000, len(Z)), replace=False)  # silhouette is O(n^2)
    rows = []
    best = None
    for k in (3, 4, 5, 6):
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Z)
        sil = silhouette_score(Z[sample], km.labels_[sample])
        aris = [adjusted_rand_score(km.labels_, KMeans(n_clusters=k, n_init=10, random_state=s).fit(Z).labels_) for s in (1, 2)]
        rows.append({"k": k, "silhouette": round(float(sil), 4), "stability_ari": round(float(np.mean(aris)), 4)})
        if best is None or sil > best[1]:
            best = (k, sil, km)
    k, _, km = best
    centroids = pd.DataFrame(km.cluster_centers_, columns=F.columns)
    sizes = np.bincount(km.labels_)
    profile = []
    for i in range(k):
        cz = centroids.iloc[i]
        top = cz.drop(["log_clicks", "active_days"]).idxmax().replace("share_", "")
        level = "high" if cz["log_clicks"] > 0.5 else "low" if cz["log_clicks"] < -0.5 else "medium"
        profile.append({"cluster": i, "students": int(sizes[i]), "activity": level, "leans_on": top,
                        "active_days_z": round(float(cz["active_days"]), 2)})
    return {"note": f"OULAD 2014 presentations, {len(F)} students with at least 50 clicks; K-Means on standardised click shares, active days and log clicks.",
            "table": rows, "chosen_k": k, "clusters": profile}


# ----------------------------------------------------------------------------- CF


def _metrics_at_k(recs: dict[int, list[int]], truth: dict[int, set[int]], k: int = 5) -> dict:
    p, r, ndcg, hit = [], [], [], []
    for u, items in recs.items():
        t = truth[u]
        top = items[:k]
        hits = [1 if i in t else 0 for i in top]
        p.append(sum(hits) / k)
        r.append(sum(hits) / len(t))
        dcg = sum(h / np.log2(j + 2) for j, h in enumerate(hits))
        idcg = sum(1 / np.log2(j + 2) for j in range(min(k, len(t))))
        ndcg.append(dcg / idcg)
        hit.append(1 if any(hits) else 0)
    return {"precision_at_5": round(float(np.mean(p)), 4), "recall_at_5": round(float(np.mean(r)), 4),
            "ndcg_at_5": round(float(np.mean(ndcg)), 4), "hit_rate_at_5": round(float(np.mean(hit)), 4)}


def run_cf(clicks: pd.DataFrame) -> dict:
    sizes = clicks.groupby(["code_module", "code_presentation"])["id_student"].nunique()
    mod, pres = sizes.idxmax()
    c = clicks[(clicks["code_module"] == mod) & (clicks["code_presentation"] == pres)]
    per = c.groupby(["id_student", "id_site"]).agg(first=("date", "min"), clicks=("sum_click", "sum")).reset_index()
    items = sorted(per["id_site"].unique())
    train_rows, truth = [], {}
    for u, g in per.groupby("id_student"):
        if len(g) < 10:
            continue
        g = g.sort_values(["first", "id_site"])
        cut = int(len(g) * 0.8)
        for _, row in g.iloc[:cut].iterrows():
            train_rows.append((int(u), int(row["id_site"]), float(np.log1p(row["clicks"]))))
        truth[int(u)] = set(g.iloc[cut:]["id_site"].astype(int))
    hist: dict[int, dict[int, float]] = {}
    for u, i, v in train_rows:
        hist.setdefault(u, {})[i] = v
    users = sorted(truth)
    idx = {a: j for j, a in enumerate(items)}
    rng = np.random.default_rng(0)
    pop = pd.Series([i for _, i, _ in train_rows]).value_counts()

    def rank(scores: np.ndarray, u: int) -> list[int]:
        s = scores.copy()
        for i in hist[u]:
            s[idx[i]] = -np.inf
        top = np.argpartition(-s, 5)[:5]
        return [items[j] for j in top[np.argsort(-s[top])]]

    results = {}
    results["Random"] = {u: rank(rng.random(len(items)), u) for u in users}
    pop_vec = np.array([pop.get(i, 0) for i in items], dtype=float)
    results["Most popular"] = {u: rank(pop_vec, u) for u in users}

    knn = cf_mod.train(train_rows, als_threshold=10**9)
    sim = np.zeros((len(items), len(items)))
    mi = [idx[i] for i in knn.item_ids]
    sim[np.ix_(mi, mi)] = knn.payload["sim"]
    results["Item-kNN (ours)"] = {}
    for u in users:
        h = np.zeros(len(items))
        for i, v in hist[u].items():
            h[idx[i]] = v
        results["Item-kNN (ours)"][u] = rank(sim @ h, u)

    als = cf_mod.train(train_rows, als_threshold=0, factors=32, iterations=20)
    Y = np.zeros((len(items), als.payload["item_factors"].shape[1]))
    Y[[idx[i] for i in als.item_ids]] = als.payload["item_factors"]
    results["ALS (ours, implicit)"] = {}
    for u in users:
        x = cf_mod._solve_user(als.payload["item_factors"], {als._index[i]: v for i, v in hist[u].items() if i in als._index},
                               als.payload["regularization"], als.payload["alpha"])
        results["ALS (ours, implicit)"][u] = rank(Y @ x, u)

    try:
        from lightfm import LightFM
        from lightfm.data import Dataset

        vle = oulad("vle", usecols=["id_site", "activity_type"]).set_index("id_site")["activity_type"]
        ds = Dataset()
        ds.fit(users=users, items=items, item_features=[f"type:{t}" for t in vle.reindex(items).fillna("other").unique()])
        inter, weights = ds.build_interactions([(u, i, v) for u, i, v in train_rows if u in truth])
        feats = ds.build_item_features([(i, [f"type:{vle.get(i, 'other')}"]) for i in items])
        model = LightFM(loss="warp", no_components=32, random_state=0)
        model.fit(inter, item_features=feats, sample_weight=weights, epochs=20, num_threads=4)
        uid, _, iid, _ = ds.mapping()
        item_order = np.array([iid[i] for i in items])
        results["LightFM hybrid (WARP + item type)"] = {
            u: rank(model.predict(uid[u], item_order, item_features=feats), u) for u in users}
    except Exception as e:  # LightFM is optional (no wheel on some platforms)
        print("LightFM skipped:", e)

    table = []
    for name, recs in results.items():
        cov = len({i for r in recs.values() for i in r}) / len(items)
        table.append({"model": name, **_metrics_at_k(recs, truth), "coverage": round(cov, 4)})
    return {"note": (f"OULAD {mod} {pres}: {len(users)} students, {len(items)} course materials. Per-student time split "
                     "(first 80% of materials opened = training, last 20% = target); training items excluded from "
                     "candidates. This validates the CF methods on implicit clicks; the app's CF learns from outcome gain instead."),
            "table": table}


def main() -> None:
    t0 = time.time()
    clicks = load_clicks()
    print(f"loaded {len(clicks):,} click rows ({time.time() - t0:.0f}s)")
    risk = run_risk(clicks)
    print("risk", json.dumps(risk["table"]))
    personas = run_personas(clicks)
    print("personas", json.dumps(personas["table"]))
    cf = run_cf(clicks)
    print("cf", json.dumps(cf["table"]))
    tripwires = {
        "risk_auc_below_0.95": all(r["roc_auc"] < 0.95 for r in risk["table"]),
        "risk_beats_chance": all(r["roc_auc"] > 0.6 for r in risk["table"]),
        "cf_beats_random": max(r["ndcg_at_5"] for r in cf["table"] if r["model"] != "Random")
        > next(r["ndcg_at_5"] for r in cf["table"] if r["model"] == "Random"),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name, payload in (("risk", risk), ("personas", personas), ("cf_offline", cf)):
        (OUT / f"{name}.json").write_text(json.dumps({**payload, "tripwires": tripwires}, indent=1))
    print("tripwires", tripwires, f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
