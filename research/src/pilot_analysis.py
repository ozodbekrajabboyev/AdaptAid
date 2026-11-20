"""Pilot study analysis, exactly as pre-specified in docs/STUDY_PROTOCOL.md.

Input: the CSV from Admin -> Pilot study -> Download CSV (one row per participant).

Primary analysis
  ANCOVA: post_score ~ pre_score + arm. The arm coefficient is the adjusted difference in
  post-test score (adaptive minus control), reported with its 95% CI and p-value.
Secondary
  Hake's normalized gain g = (post - pre) / (1 - pre) by arm: mean difference with a
  bootstrap 95% CI, Mann-Whitney U, Cohen's d. SUS and satisfaction by arm. Engagement.

Usage:
    backend/.venv/bin/python -m research.src.pilot_analysis pilot_study.csv
    backend/.venv/bin/python -m research.src.pilot_analysis --self-test
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "outputs"


def analyse(df: pd.DataFrame, n_boot: int = 4000, seed: int = 0) -> dict:
    import statsmodels.formula.api as smf
    from scipy import stats

    d = df.dropna(subset=["pre_score", "post_score", "arm"]).copy()
    d = d[d["arm"].isin(["adaptive", "control"])]
    d["adaptive"] = (d["arm"] == "adaptive").astype(int)
    n = d["arm"].value_counts().to_dict()
    if min(n.get("adaptive", 0), n.get("control", 0)) < 3:
        return {"error": "need at least 3 participants with pre- and post-test scores in each arm", "n": n}

    model = smf.ols("post_score ~ pre_score + adaptive", data=d).fit()
    lo, hi = model.conf_int().loc["adaptive"].tolist()
    primary = {"effect": round(float(model.params["adaptive"]), 4), "ci95": [round(lo, 4), round(hi, 4)],
               "p_value": round(float(model.pvalues["adaptive"]), 4), "r2": round(float(model.rsquared), 4)}

    d = d[d["pre_score"] < 1].copy()
    d["g"] = (d["post_score"] - d["pre_score"]) / (1 - d["pre_score"])
    ga = d.loc[d["adaptive"] == 1, "g"].to_numpy()
    gc = d.loc[d["adaptive"] == 0, "g"].to_numpy()
    rng = np.random.default_rng(seed)
    boot = [rng.choice(ga, len(ga)).mean() - rng.choice(gc, len(gc)).mean() for _ in range(n_boot)]
    pooled = np.sqrt(((len(ga) - 1) * ga.var(ddof=1) + (len(gc) - 1) * gc.var(ddof=1)) / (len(ga) + len(gc) - 2))
    u = stats.mannwhitneyu(ga, gc, alternative="two-sided")
    secondary = {
        "mean_g": {"adaptive": round(float(ga.mean()), 4), "control": round(float(gc.mean()), 4)},
        "diff_g": round(float(ga.mean() - gc.mean()), 4),
        "diff_g_bootstrap_ci95": [round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4)],
        "cohens_d": round(float((ga.mean() - gc.mean()) / pooled), 4) if pooled > 0 else None,
        "mann_whitney_u": round(float(u.statistic), 2), "mann_whitney_p": round(float(u.pvalue), 4),
    }
    by_arm = {}
    for arm, g in df.groupby("arm"):
        by_arm[arm] = {c: (round(float(pd.to_numeric(g[c], errors="coerce").mean()), 3) if c in g else None)
                       for c in ("sus", "satisfaction", "aid_uses", "checked_uses", "active_days", "completion_rate")}
    return {"n": n, "primary_ancova": primary, "secondary": secondary, "by_arm": by_arm,
            "significant_at_0.05": primary["p_value"] < 0.05}


def simulate_pilot(n_per_arm: int = 20, effect: float = 0.0, seed: int = 0, items: int = 20) -> pd.DataFrame:
    """Synthetic pilot data for checking the analysis (planted effect on post-test score)."""
    rng = np.random.default_rng(seed)
    rows = []
    for arm in ("adaptive", "control"):
        for i in range(n_per_arm):
            skill = rng.beta(2.5, 3)
            pre = rng.binomial(items, 0.15 + 0.7 * skill) / items
            learn = 0.25 + (effect if arm == "adaptive" else 0.0) + rng.normal(0, 0.08)
            p_post = np.clip(0.15 + 0.7 * skill + learn * (1 - (0.15 + 0.7 * skill)), 0.01, 0.99)
            post = rng.binomial(items, p_post) / items
            rows.append({"participant": f"{arm[0]}{i}", "arm": arm, "pre_score": pre, "post_score": post,
                         "sus": rng.normal(72, 10), "satisfaction": rng.normal(3.8, 0.5)})
    return pd.DataFrame(rows)


def self_test() -> dict:
    planted = analyse(simulate_pilot(n_per_arm=20, effect=0.25, seed=1))
    null = analyse(simulate_pilot(n_per_arm=20, effect=0.0, seed=2))
    ok = planted["significant_at_0.05"] and not null["significant_at_0.05"]
    return {"planted_effect_detected": planted["significant_at_0.05"], "planted": planted["primary_ancova"],
            "null_not_detected": not null["significant_at_0.05"], "null": null["primary_ancova"], "ok": bool(ok)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        res = self_test()
        print(json.dumps(res, indent=1))
        sys.exit(0 if res["ok"] else 1)
    if not args.csv:
        ap.error("give the exported CSV, or --self-test")
    res = analyse(pd.read_csv(args.csv))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pilot.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
