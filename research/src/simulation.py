"""Simulation study: does the adaptive recommender help, and when?

Runs entirely on the engine package (the same code the app uses), with simulated learners
whose true knowledge and true format preferences are known.

Experiments
  1. Policy comparison: random, static course plan, single-signal rankers, hybrid without
     style, full hybrid; at three levels of how much format matching *really* matters
     (affinity_effect = 0, 0.3, 0.8).
  2. Retest effect: quick checks alone, with no aid, to measure what checking itself adds.
  3. Style recovery: does the learned preference vector approach the true one, starting
     from a noisy questionnaire, no questionnaire, or a deliberately wrong one?
  4. Weight tuning: random search over phase weights on *tuning* seeds. The best set is
     adopted only if, on separate *validation* seeds, it loses no more than 0.005 AUC at
     any affinity level (decision rule fixed in advance). Both are then reported on the
     *reporting* seeds.

Style-update settings and the exploration card position are tuned the same way, with
"do no harm" rules: learning from outcomes may not degrade a good questionnaire by more
than 0.03 cosine, and exploration may not cost more than 0.01 AUC.

Usage (from the repo root, backend venv):
    backend/.venv/bin/python -m research.src.simulation [--quick] [--catalogue demo|dsa]
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from engine.hybrid import DEFAULT_WEIGHTS, SIGNALS
from engine.policy import RandomPolicy, StaticPolicy, ablation
from engine.simulator import WorldConfig, demo_catalogue, run
from engine.style import UpdateConfig

OUT = Path(__file__).resolve().parents[1] / "outputs"
# Three disjoint seed sets: search on TUNE, decide on VALID, report on REPORT.
TUNE_SEEDS = [101, 102, 103, 104]
VALID_SEEDS = [201, 202, 203, 204]
REPORT_SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]
AFFINITY = {"none": 0.0, "small": 0.3, "large": 0.8}
STYLE_CFG = {"lr": UpdateConfig().lr, "prior_pull": UpdateConfig().prior_pull, "max_step": UpdateConfig().max_step}
POLICIES = ["random", "static", "need_only", "style_only", "level_only", "cf_only", "no_style", "hybrid"]


def load_catalogue(spec: str):
    if spec == "demo":
        return demo_catalogue(n_concepts=10, aids_per_concept=7, seed=0)
    if spec == "dsa":
        from research.src.catalogue import dsa_catalogue

        return dsa_catalogue()
    raise ValueError(spec)


def make_policy(name: str, weights: dict | None, seed: int, explore_position="default"):
    if name == "random":
        return RandomPolicy(seed=seed)
    if name == "static":
        return StaticPolicy()
    pol = ablation(name)
    if weights is not None and name in ("hybrid", "no_style"):
        pol.weights = copy.deepcopy(weights)
    if explore_position != "default":
        pol.explore_position = explore_position
    return pol


def job(spec: dict) -> dict:
    cat = load_catalogue(spec["catalogue"])
    cfg = WorldConfig(
        affinity_effect=spec["affinity"],
        prior_mode=spec.get("prior_mode", "noisy"),
        style_cfg=UpdateConfig(
            lr=spec.get("style_lr", STYLE_CFG["lr"]),
            prior_pull=spec.get("style_pull", STYLE_CFG["prior_pull"]),
            max_step=spec.get("style_step", STYLE_CFG["max_step"]),
        ),
    )
    res = run(
        lambda: make_policy(spec["policy"], spec.get("weights"), spec["seed"], spec.get("explore_position", "default")),
        cat,
        n_learners=spec["n"],
        steps=spec["steps"],
        cfg=cfg,
        seed=spec["seed"],
        check_only=spec.get("check_only", False),
    )
    return {
        **{k: v for k, v in spec.items() if k not in ("weights", "catalogue")},
        "final_known": res.final_known,
        "auc_known": float(np.mean(res.known_curve)),
        "steps_to_all": res.steps_to_all,
        "mean_gain": res.mean_gain,
        "final_style_cos": res.style_curve[-1] if res.style_curve else None,
        "start_style_cos": res.style_curve[0] if res.style_curve else None,
        "final_bkt_error": res.bkt_error_curve[-1] if res.bkt_error_curve else None,
        "known_curve": res.known_curve,
        "style_curve": res.style_curve,
        "by_type": res.by_type,
    }


def run_jobs(specs: list[dict], workers: int) -> list[dict]:
    if workers <= 1:
        return [job(s) for s in specs]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(job, specs, chunksize=2))


def mean_sd(xs):
    a = np.asarray(xs, dtype=float)
    return float(a.mean()), float(a.std(ddof=1)) if len(a) > 1 else 0.0


def random_weights(rng: np.random.Generator) -> dict:
    """Dirichlet samples per phase; cold phase never uses CF/help (no data yet)."""
    out = {}
    for phase in ("cold", "warm", "established"):
        if phase == "cold":
            w = rng.dirichlet([2, 2, 2])
            out[phase] = {"need": w[0], "style": w[1], "level": w[2], "cf": 0.0, "help": 0.0}
        else:
            w = rng.dirichlet([2, 1.5, 1.5, 1.5, 1.5])
            out[phase] = dict(zip(SIGNALS, w, strict=True))
        out[phase] = {k: round(float(v), 3) for k, v in out[phase].items()}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogue", default="demo", choices=["demo", "dsa"])
    ap.add_argument("--quick", action="store_true", help="fewer seeds and candidates (smoke test)")
    ap.add_argument("--learners", type=int, default=80)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--candidates", type=int, default=24, help="random weight sets to try")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()

    report_seeds = REPORT_SEEDS[:2] if args.quick else REPORT_SEEDS
    tune_seeds = TUNE_SEEDS[:1] if args.quick else TUNE_SEEDS
    valid_seeds = VALID_SEEDS[:1] if args.quick else VALID_SEEDS
    n_cand = 4 if args.quick else args.candidates
    base = {"catalogue": args.catalogue, "n": args.learners, "steps": args.steps}
    t0 = time.time()

    # 0. tune the style-update settings on the tuning seeds ------------------------------
    grid = [{"lr": lr, "prior_pull": pull, "max_step": step}
            for lr in ((0.6, 1.5) if args.quick else (0.3, 0.6, 1.0, 1.5, 2.5))
            for pull in ((0.0, 0.02) if args.quick else (0.0, 0.005, 0.02))
            for step in ((0.15,) if args.quick else (0.1, 0.2))]
    style_tune_specs = [
        {**base, "policy": "hybrid", "affinity_level": "large", "affinity": 0.8, "seed": s, "prior_mode": prior,
         "style_lr": g["lr"], "style_pull": g["prior_pull"], "style_step": g["max_step"], "grid": i}
        for i, g in enumerate(grid) for prior in ("noisy", "none", "wrong") for s in tune_seeds
    ]
    st_rows = run_jobs(style_tune_specs, args.workers)

    def style_stats(i):
        rows = [r for r in st_rows if r["grid"] == i]
        by = {m: [r for r in rows if r["prior_mode"] == m] for m in ("noisy", "none", "wrong")}
        return {
            "noisy_drift": float(np.mean([r["final_style_cos"] - r["start_style_cos"] for r in by["noisy"]])),
            "none_final": float(np.mean([r["final_style_cos"] for r in by["none"]])),
            "wrong_final": float(np.mean([r["final_style_cos"] for r in by["wrong"]])),
        }

    st_scores = []
    for i, g in enumerate(grid):
        st = style_stats(i)
        st_scores.append({"grid": i, **g, **{k: round(v, 4) for k, v in st.items()},
                          "admissible": st["noisy_drift"] >= -0.03,
                          "objective": round((st["none_final"] + st["wrong_final"]) / 2, 4)})
    st_scores.sort(key=lambda x: (not x["admissible"], -x["objective"]))
    STYLE_CFG.update({k: st_scores[0][k] for k in ("lr", "prior_pull", "max_step")})
    base["style_lr"], base["style_pull"], base["style_step"] = STYLE_CFG["lr"], STYLE_CFG["prior_pull"], STYLE_CFG["max_step"]

    # 0b. where should the exploration card go? (0-based rank; None = last) ------------------
    pos_specs = [
        {**base, "policy": "hybrid", "affinity_level": "large", "affinity": 0.8, "seed": s, "prior_mode": prior,
         "explore_position": pos, "pos_key": str(pos)}
        for pos in (1, 2, None) for prior in ("noisy", "wrong") for s in tune_seeds
    ]
    pos_rows = run_jobs(pos_specs, args.workers)
    explore_positions = []
    for pos in ("1", "2", "None"):
        rows = [r for r in pos_rows if r["pos_key"] == pos]
        explore_positions.append({
            "position": pos,
            "style_cos_wrong_prior": round(float(np.mean([r["final_style_cos"] for r in rows if r["prior_mode"] == "wrong"])), 4),
            "auc_known": round(float(np.mean([r["auc_known"] for r in rows])), 4),
        })
    last_auc = next(e["auc_known"] for e in explore_positions if e["position"] == "None")
    ok = [e for e in explore_positions if e["auc_known"] >= last_auc - 0.01]
    chosen_pos = max(ok, key=lambda e: e["style_cos_wrong_prior"])["position"]
    chosen_pos_value = None if chosen_pos == "None" else int(chosen_pos)
    base["explore_position"] = chosen_pos_value

    # 1. policy comparison --------------------------------------------------------------
    specs = [
        {**base, "policy": p, "affinity_level": lvl, "affinity": a, "seed": s}
        for lvl, a in AFFINITY.items()
        for p in POLICIES
        for s in report_seeds
    ]
    policy_rows = run_jobs(specs, args.workers)

    # 2. retest effect: checks only, concept chosen by the static plan --------------------
    retest_rows = run_jobs(
        [{**base, "policy": "static", "affinity_level": "large", "affinity": 0.8, "seed": s, "check_only": True}
         for s in report_seeds],
        args.workers,
    )

    # 3. style recovery ------------------------------------------------------------------
    style_specs = []
    for prior in ("noisy", "none", "wrong"):
        for lr_name, lr in (("with_update", STYLE_CFG["lr"]), ("prior_only", 0.0)):
            for s in report_seeds:
                style_specs.append({**base, "policy": "hybrid", "affinity_level": "large", "affinity": 0.8, "seed": s,
                                    "prior_mode": prior, "style_lr": lr, "style_case": f"{prior}/{lr_name}"})
    style_rows = run_jobs(style_specs, args.workers)

    # 4. weight tuning (tuning seeds only) -------------------------------------------------
    rng = np.random.default_rng(2026)
    candidates = [{k: dict(v) for k, v in DEFAULT_WEIGHTS.items()}] + [random_weights(rng) for _ in range(n_cand)]
    tune_specs = [
        {**base, "policy": "hybrid", "affinity_level": lvl, "affinity": AFFINITY[lvl], "seed": s, "weights": w, "cand": i}
        for i, w in enumerate(candidates)
        for lvl in ("none", "small", "large")
        for s in tune_seeds
    ]
    tune_rows = run_jobs(tune_specs, args.workers)
    cand_scores = []
    for i, w in enumerate(candidates):
        rows = [r for r in tune_rows if r["cand"] == i]
        cand_scores.append({"cand": i, "weights": w, "objective": float(np.mean([r["auc_known"] for r in rows]))})
    cand_scores.sort(key=lambda c: -c["objective"])
    best = cand_scores[0]["weights"]

    valid_rows = run_jobs(
        [{**base, "policy": "hybrid", "affinity_level": lvl, "affinity": a, "seed": s, "weights": w, "version": v}
         for v, w in (("v0", DEFAULT_WEIGHTS), ("tuned", best))
         for lvl, a in AFFINITY.items() for s in valid_seeds],
        args.workers,
    )
    valid = {}
    for lvl in AFFINITY:
        v0 = np.mean([r["auc_known"] for r in valid_rows if r["version"] == "v0" and r["affinity_level"] == lvl])
        tu = np.mean([r["auc_known"] for r in valid_rows if r["version"] == "tuned" and r["affinity_level"] == lvl])
        valid[lvl] = round(float(tu - v0), 4)
    # Decision rule: adopt tuned weights only for a meaningful validated gain (>= 0.005 mean AUC)
    # with no level losing more than 0.005. A first, looser rule (mean > 0) adopted weights
    # that the reporting seeds showed to be no better: the top candidates differ by less
    # than seed noise, so picking the maximum is a winner's curse. See docs for the write-up.
    adopt = all(d >= -0.005 for d in valid.values()) and float(np.mean(list(valid.values()))) >= 0.005
    chosen_weights = best if adopt else {k: dict(v) for k, v in DEFAULT_WEIGHTS.items()}

    # v0 (blueprint) vs v1 (tuned) on the reporting seeds
    compare_specs = [
        {**base, "policy": "hybrid", "affinity_level": lvl, "affinity": a, "seed": s, "weights": w, "version": v}
        for v, w in (("v0", DEFAULT_WEIGHTS), ("tuned", best))
        for lvl, a in AFFINITY.items()
        for s in report_seeds
    ]
    compare_rows = run_jobs(compare_specs, args.workers)

    # ---------------------------------------------------------------- summaries + checks
    def summary(rows, keys):
        groups: dict[tuple, list[dict]] = {}
        for r in rows:
            groups.setdefault(tuple(r[k] for k in keys), []).append(r)
        out = []
        for key, rs in groups.items():
            fk, fk_sd = mean_sd([r["final_known"] for r in rs])
            auc, auc_sd = mean_sd([r["auc_known"] for r in rs])
            out.append({
                **dict(zip(keys, key, strict=True)),
                "n_runs": len(rs),
                "final_known": round(fk, 4), "final_known_sd": round(fk_sd, 4),
                "auc_known": round(auc, 4), "auc_known_sd": round(auc_sd, 4),
                "steps_to_all": round(float(np.mean([r["steps_to_all"] for r in rs])), 2),
                "mean_gain": round(float(np.mean([r["mean_gain"] for r in rs])), 4),
                "final_style_cos": round(float(np.mean([r["final_style_cos"] for r in rs])), 4),
                "start_style_cos": round(float(np.mean([r["start_style_cos"] for r in rs])), 4),
                "curve": [round(float(x), 4) for x in np.mean([r["known_curve"] for r in rs], axis=0)],
                "style_curve_mean": [round(float(x), 4) for x in np.mean([r["style_curve"] for r in rs], axis=0)],
            })
        return out

    pol_sum = summary(policy_rows, ["affinity_level", "policy"])
    idx = {(r["affinity_level"], r["policy"]): r for r in pol_sum}
    style_sum = summary(style_rows, ["style_case"])
    style_idx = {r["style_case"]: r for r in style_sum}
    retest_sum = summary(retest_rows, ["policy"])[0]
    comp_sum = summary(compare_rows, ["version", "affinity_level"])

    def paired(policy_a, policy_b, lvl, metric="auc_known"):
        a = {r["seed"]: r[metric] for r in policy_rows if r["policy"] == policy_a and r["affinity_level"] == lvl}
        b = {r["seed"]: r[metric] for r in policy_rows if r["policy"] == policy_b and r["affinity_level"] == lvl}
        d = np.array([a[s] - b[s] for s in a if s in b])
        mean = float(d.mean())
        if len(d) > 1:
            from scipy import stats

            half = float(stats.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d)))
        else:
            half = 0.0
        return {"a": policy_a, "b": policy_b, "affinity_level": lvl, "metric": metric, "mean_diff": round(mean, 4),
                "ci95": [round(mean - half, 4), round(mean + half, 4)], "n_pairs": len(d)}

    paired_diffs = [paired(a, b, lvl) for lvl in AFFINITY
                    for a, b in (("hybrid", "static"), ("hybrid", "no_style"), ("hybrid", "random"))]

    tol = 0.01  # allowed shortfall at affinity "none" (simulation noise)
    checks = {
        "hybrid_ge_static_every_level": all(
            idx[(lvl, "hybrid")]["auc_known"] >= idx[(lvl, "static")]["auc_known"] - tol for lvl in AFFINITY
        ),
        "hybrid_gt_static_when_style_matters": all(
            idx[(lvl, "hybrid")]["auc_known"] > idx[(lvl, "static")]["auc_known"] for lvl in ("small", "large")
        ),
        "learned_style_beats_no_questionnaire": style_idx["none/with_update"]["final_style_cos"]
        > style_idx["none/prior_only"]["final_style_cos"],
        "learned_style_recovers_from_wrong_questionnaire": style_idx["wrong/with_update"]["final_style_cos"]
        > style_idx["wrong/prior_only"]["final_style_cos"],
        "aids_beat_checks_alone": idx[("large", "static")]["final_known"] > retest_sum["final_known"],
    }

    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "runtime_s": round(time.time() - t0, 1),
        "config": {**base, "report_seeds": report_seeds, "tune_seeds": tune_seeds, "valid_seeds": valid_seeds,
                   "affinity": AFFINITY,
                   "candidates": n_cand + 1},
        "policy_summary": [{k: v for k, v in r.items() if k != "style_curve_mean"} for r in pol_sum],
        "retest": {k: v for k, v in retest_sum.items() if k not in ("curve", "style_curve_mean")},
        "style_recovery": [{k: v for k, v in r.items() if k != "curve"} for r in style_sum],
        "style_tuning": {"best": dict(STYLE_CFG), "top": st_scores[:5]},
        "explore_position": {"candidates": explore_positions, "chosen": chosen_pos_value},
        "paired_differences": paired_diffs,
        "tuning": {"top": [{k: c[k] for k in ("cand", "objective", "weights")} for c in cand_scores[:5]],
                   "best_weights": best, "validation_diff_tuned_minus_v0": valid, "adopted": adopt,
                   "rule": "adopt if mean validation gain >= 0.005 AUC and no affinity level loses > 0.005",
                   "chosen_weights": chosen_weights, "v0_v1": [{k: v for k, v in r.items() if k not in ("curve", "style_curve_mean")}
                                                   for r in comp_sum]},
        "checks": checks,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    name = "simulation.json" if args.catalogue == "demo" else f"simulation_{args.catalogue}.json"
    (OUT / name).write_text(json.dumps(result, indent=1))
    print(json.dumps({"runtime_s": result["runtime_s"], "checks": checks}, indent=1))
    for lvl in AFFINITY:
        line = "  ".join(f"{p}={idx[(lvl, p)]['auc_known']:.3f}" for p in POLICIES)
        print(f"[{lvl}] {line}")
    for case, r in style_idx.items():
        print(f"style {case}: start {r['start_style_cos']:.3f} -> final {r['final_style_cos']:.3f}")
    print("style update:", json.dumps(STYLE_CFG))
    for e in explore_positions:
        print(f"explore card at {e['position']}: style cos (wrong prior) {e['style_cos_wrong_prior']:.3f}, auc {e['auc_known']:.4f}")
    print("explore position chosen:", chosen_pos_value)
    print("weights: validation diff", valid, "-> adopted" if adopt else "-> kept blueprint v0")
    for p in paired_diffs:
        print(f"{p['a']} - {p['b']} [{p['affinity_level']}]: {p['mean_diff']:+.4f}  95% CI {p['ci95']}")
    for r in comp_sum:
        print(f"{r['version']} {r['affinity_level']}: auc {r['auc_known']:.4f} final {r['final_known']:.4f}")


if __name__ == "__main__":
    main()
