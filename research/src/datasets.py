"""Public datasets: download (once) and load with the documented cleaning steps.

- ASSISTments 2009-2010 skill builder (Feng, Heffernan & Koedinger, 2009), via the copy
  used by pyBKT's examples. Cleaning: drop scaffolding rows (original == 0), drop rows
  without a skill, keep one row per order_id (multi-skill problems are duplicated in the
  raw export, which inflates knowledge-tracing AUC).
- OULAD, Open University Learning Analytics Dataset (Kuzilek, Hlosta & Zdrahal, 2017),
  CC BY 4.0, via the UCI Machine Learning Repository mirror.

Raw files live in research/data/ (git-ignored). They are parsed as data only.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
ASSIST_URL = "https://raw.githubusercontent.com/CAHLR/pyBKT-examples/master/data/as.csv"
OULAD_URL = "https://archive.ics.uci.edu/static/public/349/open+university+learning+analytics+dataset.zip"


def _download(url: str, dest: Path) -> Path:
    import httpx

    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    tmp.rename(dest)
    return dest


def assistments_path() -> Path:
    return _download(ASSIST_URL, DATA / "assistments" / "skill_builder_2009.csv")


def assistments() -> pd.DataFrame:
    raw = pd.read_csv(assistments_path(), encoding="latin-1", low_memory=False,
                      usecols=["order_id", "user_id", "skill_id", "skill_name", "correct", "original"])
    n0 = len(raw)
    df = raw[raw["original"] == 1]
    df = df.dropna(subset=["skill_name"])
    df = df.drop_duplicates(subset="order_id", keep="first")
    df = df.sort_values(["user_id", "order_id"])
    df["correct"] = df["correct"].astype(int).clip(0, 1)
    df.attrs["cleaning"] = {"raw_rows": n0, "after_original": int((raw["original"] == 1).sum()), "final_rows": len(df)}
    return df[["order_id", "user_id", "skill_name", "correct"]].reset_index(drop=True)


def oulad_dir() -> Path:
    target = DATA / "oulad"
    if (target / "studentInfo.csv").exists():
        return target
    z = _download(OULAD_URL, DATA / "oulad_download" / "oulad.zip")
    with zipfile.ZipFile(z) as outer:
        names = outer.namelist()
        inner = [n for n in names if n.endswith(".zip")]
        target.mkdir(parents=True, exist_ok=True)
        if inner:  # the UCI archive wraps the original zip
            outer.extract(inner[0], DATA / "oulad_download")
            with zipfile.ZipFile(DATA / "oulad_download" / inner[0]) as z2:
                _safe_extract(z2, target)
        else:
            _safe_extract(outer, target)
    nested = list(target.rglob("studentInfo.csv"))
    if nested and nested[0].parent != target:
        for f in nested[0].parent.iterdir():
            f.rename(target / f.name)
    return target


def _safe_extract(z: zipfile.ZipFile, dest: Path) -> None:
    for member in z.namelist():
        p = (dest / member).resolve()
        if not str(p).startswith(str(dest.resolve())):
            raise ValueError(f"unsafe path in archive: {member}")
    z.extractall(dest)


def oulad(table: str, **kw) -> pd.DataFrame:
    # OULAD marks missing values (dates, scores, imd_band) with "?".
    return pd.read_csv(oulad_dir() / f"{table}.csv", na_values=["?"], **kw)


if __name__ == "__main__":
    a = assistments()
    print("ASSISTments", a.attrs["cleaning"], "skills", a["skill_name"].nunique(), "students", a["user_id"].nunique())
    d = oulad_dir()
    print("OULAD files:", sorted(p.name for p in d.glob("*.csv")))
