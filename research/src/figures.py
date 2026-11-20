"""Report figures for every offline evaluation (PNG, 160 dpi) in research/outputs/figures."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from research.src import sim_figures

OUT = Path(__file__).resolve().parents[1] / "outputs"
FIG = OUT / "figures"
INK, GOOD, WARN, BAD, MUTED, VIOLET = "#2747c9", "#1f8a5b", "#c98a12", "#c8463d", "#7a869e", "#7c4dbd"


def _load(name: str) -> dict | None:
    p = OUT / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _style(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.25)


def bars(name: str, rows: list[dict], label: str, value: str, xlabel: str, colors=None, xlim=None) -> None:
    fig, ax = plt.subplots(figsize=(7, 0.55 * len(rows) + 1.2))
    names = [r[label] for r in rows]
    vals = [r[value] for r in rows]
    ax.barh(names, vals, color=colors or [MUTED] * (len(rows) - 1) + [INK])
    for i, v in enumerate(vals):
        ax.text(v, i, f" {v:.3f}", va="center", fontsize=9)
    ax.invert_yaxis()
    if xlim:
        ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel)
    _style(ax)
    fig.tight_layout()
    fig.savefig(FIG / f"{name}.png", dpi=160)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    if (OUT / "simulation.json").exists():
        sim_figures.main("simulation.json")
    bkt = _load("bkt_eval")
    if bkt:
        bars("bkt_auc", bkt["table"], "model", "auc", "ROC-AUC, next-answer prediction (ASSISTments 2009, 5-fold by student)",
             colors=[MUTED, MUTED, INK, VIOLET][: len(bkt["table"])], xlim=(0.4, 0.8))
    risk = _load("risk")
    if risk:
        bars("risk_roc_auc", risk["table"], "model", "roc_auc", "ROC-AUC, at-risk after 6 weeks (OULAD, train 2013 / test 2014)",
             colors=[MUTED, INK, VIOLET], xlim=(0.5, 0.85))
    cf = _load("cf_offline")
    if cf:
        bars("cf_ndcg", cf["table"], "model", "ndcg_at_5", "NDCG@5, next course materials (OULAD, per-student time split)",
             colors=[MUTED, MUTED, INK, VIOLET, GOOD][: len(cf["table"])])
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
