"""Regenerate every number and figure in the report, then check the tripwires.

    backend/.venv/bin/python -m research.src.run_all [--quick]

Steps: simulation study (synthetic catalogue and the real DSA catalogue), knowledge tracing
on ASSISTments (pyBKT predictions from research/outputs/pybkt_predictions.csv, made on Colab,
or a local pyBKT venv if that file is missing), OULAD risk/personas/CF, figures, summary.
Exits non-zero if any tripwire fails (an implausible result usually means leakage or a bug).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "outputs"
PY = sys.executable


def step(name: str, args: list[str]) -> None:
    t = time.time()
    print(f"==> {name}")
    subprocess.run([PY, "-m", *args], cwd=ROOT, check=True)
    print(f"    {name} done in {time.time() - t:.0f}s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller runs for a smoke test")
    ap.add_argument("--skip-bkt", action="store_true", help="keep the existing bkt_eval.json (slow step)")
    ap.add_argument("--skip-sim", action="store_true", help="keep the existing simulation outputs")
    args = ap.parse_args()
    q = ["--quick"] if args.quick else []
    if not args.skip_sim:
        step("simulation (synthetic catalogue)", ["research.src.simulation", *q])
        step("simulation (DSA catalogue)", ["research.src.simulation", "--catalogue", "dsa", *q])
    if not args.skip_bkt:
        pybkt_csv = OUT / "pybkt_predictions.csv"
        step("knowledge tracing (ASSISTments)", ["research.src.bkt_eval", *(["--skills", "5"] if args.quick else []),
                                                 *(["--pybkt-csv", str(pybkt_csv)] if pybkt_csv.exists() else [])])
    step("OULAD: risk, personas, CF", ["research.src.oulad_eval"])
    step("figures", ["research.src.figures"])

    summary: dict[str, dict] = {}
    failed = []
    for f in sorted(OUT.glob("*.json")):
        if f.name == "summary.json":
            continue
        data = json.loads(f.read_text())
        checks = data.get("tripwires") or data.get("checks") or {}
        summary[f.stem] = checks
        failed += [f"{f.stem}: {k}" for k, ok in checks.items() if not ok]
    (OUT / "summary.json").write_text(json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                                  "checks": summary, "failed": failed}, indent=1))
    if failed:
        print("TRIPWIRES FAILED:\n  " + "\n  ".join(failed))
        sys.exit(1)
    print("All checks passed. Results in research/outputs/.")


if __name__ == "__main__":
    main()
