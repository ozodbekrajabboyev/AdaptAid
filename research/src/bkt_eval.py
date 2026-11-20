"""Knowledge tracing on ASSISTments 2009: how well does BKT predict the next answer?

Protocol (guards against the usual leakage):
- 5-fold cross-validation split by *student*: no student is in both train and test.
- Parameters are fitted on the training folds only, separately per skill.
- Predictions are one step ahead: P(correct) for an answer is computed before seeing it.
- Metrics pooled over every test prediction: ROC-AUC and RMSE.

Models: global mean, per-skill mean, our bounded brute-force BKT (engine/bkt.py, the code
the app runs), and pyBKT's EM fit (Badrinath et al., 2021) run in its own pinned venv.

Usage: backend/.venv/bin/python -m research.src.bkt_eval [--skills 40] [--no-pybkt]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from engine.bkt import fit_brute_force, trace
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold

from research.src.datasets import assistments

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "outputs"
PYBKT_PY = ROOT / "research" / ".venv-pybkt" / "bin" / "python"
FOLDS = 5
MAX_FIT_LEN = 50  # sequences are truncated to 50 answers for fitting speed (prediction uses all)


def _fit_and_predict(args: tuple) -> dict:
    skill, train_seqs, test_seqs = args
    fit = fit_brute_force(train_seqs, max_len=MAX_FIT_LEN)
    preds: list[float] = []
    for s in test_seqs:
        p, _ = trace(s, fit.params)
        preds.extend(p)
    return {"skill": skill, "params": fit.params.as_dict(), "preds": preds}


def rmse(y, p) -> float:
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills", type=int, default=40, help="evaluate the N skills with the most students")
    ap.add_argument("--no-pybkt", action="store_true")
    ap.add_argument("--pybkt-skills", type=int, default=10,
                    help="run the pyBKT comparison on the N largest skills (its EM is slow)")
    ap.add_argument("--pybkt-csv", type=Path, default=None,
                    help="merge pyBKT predictions computed elsewhere (research/notebooks/pybkt_colab.ipynb) "
                         "instead of running pyBKT locally; columns fold, order_id, pybkt")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()
    t0 = time.time()

    df = assistments()
    cleaning = df.attrs["cleaning"]
    counts = df.groupby("skill_name")["user_id"].nunique()
    # Deterministic order (ties broken by name) so the Colab notebook selects identical skills.
    skills = sorted(counts.index, key=lambda s: (-int(counts[s]), s))[: args.skills]
    df = df[df["skill_name"].isin(skills)].copy()
    users = np.array(sorted(df["user_id"].unique()))
    kf = KFold(n_splits=FOLDS, shuffle=True, random_state=42)

    rows: list[dict] = []  # one per test prediction
    params_all: list[dict] = []
    use_pybkt = not args.no_pybkt and args.pybkt_csv is None and PYBKT_PY.exists()

    for fold, (tr_idx, te_idx) in enumerate(kf.split(users)):
        tr_users, te_users = set(users[tr_idx]), set(users[te_idx])
        train = df[df["user_id"].isin(tr_users)]
        test = df[df["user_id"].isin(te_users)]
        global_mean = train["correct"].mean()
        skill_mean = train.groupby("skill_name")["correct"].mean()

        jobs = []
        test_keys: dict[str, list[pd.DataFrame]] = {}
        for skill in skills:
            tr = train[train["skill_name"] == skill]
            te = test[test["skill_name"] == skill]
            if tr.empty or te.empty:
                continue
            tr_seqs = [g["correct"].tolist() for _, g in tr.groupby("user_id", sort=False)]
            te_groups = [g for _, g in te.groupby("user_id", sort=False)]
            test_keys[skill] = te_groups
            jobs.append((skill, tr_seqs, [g["correct"].tolist() for g in te_groups]))
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            results = list(ex.map(_fit_and_predict, jobs))

        for res in results:
            params_all.append({"fold": fold, "skill": res["skill"], **res["params"]})
            te = pd.concat(test_keys[res["skill"]])
            for (oid, y), p in zip(te[["order_id", "correct"]].itertuples(index=False), res["preds"], strict=True):
                rows.append({"fold": fold, "order_id": oid, "skill": res["skill"], "y": y, "bkt": p,
                             "global": global_mean, "skill_mean": skill_mean.get(res["skill"], global_mean)})

        if use_pybkt:
            sub = set(skills[: args.pybkt_skills])
            with tempfile.TemporaryDirectory() as tmp:
                trp, tep, outp = Path(tmp) / "train.csv", Path(tmp) / "test.csv", Path(tmp) / "pred.csv"
                train[train["skill_name"].isin(sub)].to_csv(trp, index=False)
                test[test["skill_name"].isin(sub)].to_csv(tep, index=False)
                subprocess.run([str(PYBKT_PY), "-I", str(ROOT / "research" / "pybkt" / "fit_predict.py"),
                                str(trp), str(tep), str(outp)], check=True)
                pred = pd.read_csv(outp).set_index("order_id")["correct_predictions"]
                for r in rows:
                    if r["fold"] == fold:
                        r["pybkt"] = float(pred.get(r["order_id"], np.nan))
        print(f"fold {fold + 1}/{FOLDS} done ({time.time() - t0:.0f}s)", flush=True)

    res = pd.DataFrame(rows)
    pybkt_scope = f"{args.pybkt_skills} largest skills"
    if args.pybkt_csv is not None:
        ext = pd.read_csv(args.pybkt_csv)
        lookup = {(int(f), int(o)): float(p) for f, o, p in ext[["fold", "order_id", "pybkt"]].itertuples(index=False)}
        res["pybkt"] = [lookup.get((int(f), int(o)), np.nan) for f, o in zip(res["fold"], res["order_id"], strict=True)]
        pybkt_scope = f"{ext['skill_name'].nunique()} largest skills"
        missing = res.loc[res["skill"].isin(set(ext["skill_name"])), "pybkt"].isna().sum()
        print(f"merged {res['pybkt'].notna().sum()} pyBKT predictions from {args.pybkt_csv.name} ({missing} unmatched)")
        use_pybkt = True

    def score(name: str, col: str, frame: pd.DataFrame, scope: str) -> dict:
        sub = frame.dropna(subset=[col])
        auc = roc_auc_score(sub["y"], sub[col]) if sub["y"].nunique() > 1 and sub[col].nunique() > 1 else 0.5
        return {"model": name, "scope": scope, "auc": round(float(auc), 4), "rmse": round(rmse(sub["y"], sub[col]), 4),
                "predictions": len(sub)}

    scope_all = f"{len(skills)} skills"
    table = [score("Global mean", "global", res, scope_all), score("Per-skill mean", "skill_mean", res, scope_all),
             score("BKT, brute force (ours)", "bkt", res, scope_all)]
    if use_pybkt and "pybkt" in res:
        head = res.dropna(subset=["pybkt"])
        scope_sub = pybkt_scope
        table += [score("BKT, brute force (ours)", "bkt", head, scope_sub), score("BKT, EM (pyBKT)", "pybkt", head, scope_sub)]

    per_skill = []
    for skill, g in res.groupby("skill"):
        if g["y"].nunique() > 1:
            per_skill.append({"skill": skill, "students": int(counts[skill]), "answers": len(g),
                              "auc_bkt": round(float(roc_auc_score(g["y"], g["bkt"])), 4),
                              **({"auc_pybkt": round(float(roc_auc_score(g["y"], g["pybkt"])), 4)}
                                 if "pybkt" in g and g["pybkt"].notna().all() else {})})
    per_skill.sort(key=lambda r: -r["students"])
    params = pd.DataFrame(params_all)
    median = {k: round(float(params[k].median()), 4) for k in ("prior", "learn", "guess", "slip")}

    bkt_auc = table[2]["auc"]
    tripwires = {
        "bkt_auc_in_plausible_range_0.6_0.8": 0.6 <= bkt_auc <= 0.8,
        "no_model_above_0.9": all(r["auc"] <= 0.9 for r in table),
        "bkt_beats_per_skill_mean": bkt_auc > table[1]["auc"],
    }
    out = {
        "note": (f"ASSISTments 2009 skill builder, {len(skills)} skills with the most students, "
                 f"{res['order_id'].nunique()} answers. 5-fold cross-validation by student; parameters fitted on "
                 "training folds only; one-step-ahead predictions. pyBKT is compared head to head on the largest skills "
                 "(its EM is slow), with our BKT scored on exactly the same predictions."),
        "table": table,
        "per_skill": per_skill,
        "median_params": median,
        "cleaning": cleaning,
        "config": {"skills": len(skills), "folds": FOLDS, "max_fit_len": MAX_FIT_LEN, "pybkt": use_pybkt,
                   "pybkt_scope": pybkt_scope if use_pybkt else None,
                   "pybkt_source": ("Colab (Linux, C++ extension)" if args.pybkt_csv is not None
                                    else "local" if use_pybkt else None)},
        "tripwires": tripwires,
        "runtime_s": round(time.time() - t0, 1),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "bkt_eval.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"table": table, "median_params": median, "tripwires": tripwires}, indent=1))


if __name__ == "__main__":
    main()
