"""Figures for the simulation study (reads research/outputs/simulation.json)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "outputs"
FIG = OUT / "figures"
INK, GOOD, WARN, BAD, MUTED, VIOLET = "#2747c9", "#1f8a5b", "#c98a12", "#c8463d", "#7a869e", "#7c4dbd"
COLORS = {"hybrid": INK, "static": BAD, "random": MUTED, "no_style": VIOLET, "need_only": GOOD, "level_only": WARN}
LABELS = {"none": "Format has no effect", "small": "Small format effect", "large": "Large format effect"}


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)


def main(name: str = "simulation.json") -> None:
    data = json.loads((OUT / name).read_text())
    FIG.mkdir(parents=True, exist_ok=True)
    rows = data["policy_summary"]

    # 1. learning curves per affinity level
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
    for ax, lvl in zip(axes, ("none", "small", "large"), strict=True):
        for pol in ("hybrid", "no_style", "random", "static"):
            r = next(x for x in rows if x["affinity_level"] == lvl and x["policy"] == pol)
            ax.plot(range(1, len(r["curve"]) + 1), r["curve"], label=pol.replace("_", " "), color=COLORS[pol], lw=2)
        ax.set_title(LABELS[lvl], fontsize=11)
        ax.set_xlabel("Session")
        _style(ax)
    axes[0].set_ylabel("Share of concepts truly known")
    axes[0].legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "sim_learning_curves.png", dpi=160)
    plt.close(fig)

    # 2. paired differences with 95% CI
    diffs = data["paired_differences"]
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    labels = [f"{d['a']} − {d['b']}\n({d['affinity_level']})" for d in diffs]
    for i, d in enumerate(diffs):
        lo, hi = d["ci95"]
        color = GOOD if lo > 0 else MUTED
        ax.errorbar(d["mean_diff"], i, xerr=[[d["mean_diff"] - lo], [hi - d["mean_diff"]]], fmt="o", color=color, capsize=3)
    ax.axvline(0, color="#999", lw=1)
    ax.set_yticks(range(len(diffs)), labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Difference in mean share of concepts known (AUC), 95% CI over paired seeds")
    _style(ax)
    fig.tight_layout()
    fig.savefig(FIG / "sim_paired_differences.png", dpi=160)
    plt.close(fig)

    # 3. style recovery
    st = {r["style_case"]: r for r in data["style_recovery"]}
    fig, ax = plt.subplots(figsize=(7, 3.6))
    cases = ["noisy", "none", "wrong"]
    x = range(len(cases))
    ax.bar([i - 0.2 for i in x], [st[f"{c}/prior_only"]["final_style_cos"] for c in cases], 0.38, color=MUTED,
           label="questionnaire only")
    ax.bar([i + 0.2 for i in x], [st[f"{c}/with_update"]["final_style_cos"] for c in cases], 0.38, color=INK,
           label="questionnaire + learning from outcomes")
    ax.set_xticks(list(x), ["Noisy questionnaire", "No questionnaire", "Wrong questionnaire"])
    ax.axhline(0, color="#999", lw=1)
    ax.set_ylabel("cos(learned, true preference)")
    ax.legend(frameon=False, fontsize=9)
    _style(ax)
    fig.tight_layout()
    fig.savefig(FIG / "sim_style_recovery.png", dpi=160)
    plt.close(fig)
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
