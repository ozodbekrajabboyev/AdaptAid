"""Generate report material in docs/report-assets/ from the code, the content and the results.

    backend/.venv/bin/python -m research.src.report_assets

Writes: diagrams.md (mermaid), data_dictionary.md, er_diagram.md, content_summary.md,
results.md, appendices.md, openapi.json. Screenshots come from `make screenshots`.
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "report-assets"
RES = ROOT / "research" / "outputs"

DIAGRAMS = r'''# System diagrams

All diagrams are Mermaid; GitHub, VS Code and https://mermaid.live render them, and they can be exported as PNG/SVG for the report.

## 1. Architecture

```mermaid
flowchart TB
    subgraph Users
      S[Student] --- T[Teacher] --- A[Administrator]
    end
    subgraph Web["Web app (Next.js 16, React 19)"]
      UI[Student, teacher and admin pages]
      PX["/api/* same-origin proxy (route handler)"]
    end
    subgraph API["API (FastAPI)"]
      R[Routers: auth, onboarding, quiz, recommendations, events, content, teacher, admin, study]
      SV[Services: learner model, recommend, quiz, events, study, teacher, admin]
      J[Nightly jobs: personas, risk, aid stats, CF, BKT refit]
    end
    subgraph Engine["Engine (pure Python, unit-tested)"]
      BKT[Bayesian Knowledge Tracing]
      STY[Learning-preference model]
      HYB[Hybrid scorer + MMR re-rank + explanations]
      CF[Collaborative filtering: item-kNN / ALS]
      GRP[Group suggestions]
      PRF[Personas + risk]
      SIM[Learner simulator]
    end
    DB[(PostgreSQL)]
    RS[Research scripts: ASSISTments, OULAD, simulation]
    Users --> UI --> PX --> R --> SV --> Engine
    J --> Engine
    SV --> DB
    J --> DB
    RS --> Engine
    RS -->|import-research| DB
```

## 2. Data-flow diagram, level 0 (context)

```mermaid
flowchart LR
    S([Student]) -- "answers, aid usage, ratings, questionnaire" --> P((AdaptAid))
    P -- "recommended aids with reasons, mastery, learning path" --> S
    T([Teacher]) -- "teaching aids, questions, classes" --> P
    P -- "heatmap, risk flags, class aid suggestions, aid effectiveness" --> T
    A([Administrator]) -- "accounts, study settings, job triggers" --> P
    P -- "model report, pilot export" --> A
    D[(Public datasets: ASSISTments, OULAD)] -- "offline evaluation" --> P
```

## 3. Data-flow diagram, level 1

```mermaid
flowchart TB
    S([Student]) --> P1[1.0 Onboarding: questionnaire + diagnostic]
    P1 --> D2[(Style profiles)]
    P1 --> D3[(Responses + mastery)]
    S --> P2[2.0 Use a teaching aid]
    P2 --> D4[(Aid uses + interactions)]
    S --> P3[3.0 Quick check]
    P3 -->|BKT update| D3
    P3 -->|residual gain| D4
    P3 -->|style update| D2
    D1[(Content: concepts, aids, questions)] --> P4[4.0 Recommend]
    D2 --> P4
    D3 --> P4
    D5[(Aid stats + CF model)] --> P4
    P4 --> D6[(Recommendation lists + items)]
    D6 --> S
    D4 --> P5[5.0 Nightly jobs]
    D3 --> P5
    P5 --> D5
    P5 --> D7[(Personas + risk)]
    D3 --> P6[6.0 Teacher analytics]
    D7 --> P6
    D5 --> P6
    P6 --> T([Teacher])
```

## 4. Use cases

```mermaid
flowchart LR
    S([Student]) --- U1(Register / join class)
    S --- U2(Answer preference questionnaire)
    S --- U3(Take diagnostic)
    S --- U4(View recommendations with reasons)
    S --- U5(Use a teaching aid)
    S --- U6(Take a quick check)
    S --- U7(View learning path and progress)
    S --- U8(Pilot: consent, pre/post test, survey)
    T([Teacher]) --- U9(View class heatmap and risk)
    T --- U10(Get class teaching-aid suggestions)
    T --- U11(Manage aids and questions)
    T --- U12(Create class and share code)
    A([Administrator]) --- U13(Manage users)
    A --- U14(Run jobs / view model report)
    A --- U15(Configure and export pilot study)
```

## 5. Sequence: one turn of the adaptive loop

```mermaid
sequenceDiagram
    actor S as Student
    participant W as Web app
    participant API as FastAPI
    participant E as Engine
    participant DB as PostgreSQL
    S->>W: open recommended aid
    W->>API: POST /api/events {open, item}
    API->>DB: aid_use(p_open = current mastery)
    S->>W: finish aid, rate it
    W->>API: POST /api/events {complete, rate}
    S->>W: take quick check
    W->>API: POST /api/quiz/start {check, use_id}
    API->>DB: 3 unseen check questions
    loop each answer
      W->>API: POST /answer
      API->>E: bkt.update(p, correct)
      API->>DB: response(p_before, p_after), mastery
    end
    W->>API: POST /finish
    API->>E: residual_gain(p_open, answers)
    API->>E: style.update(profile, aid style, gain)
    API->>E: policy.recommend(learner view, catalogue)
    E-->>API: ranked aids + signal parts
    API->>E: explain(item, contributions)
    API->>DB: new recommendation list (policy, arm, phase, versions)
    API-->>W: mastery before/after, gain, new list id
    W-->>S: mastery change, "see what's next"
```

## 6. Deployment

```mermaid
flowchart LR
    B[Browser] -- HTTPS 443 --> C[Caddy: TLS, compression]
    C --> W[web: Next.js standalone :3000]
    W -- "/api/* (server side)" --> API[api: FastAPI + scheduler :8000]
    API --> PG[(db: PostgreSQL 17, volume pgdata)]
```
'''


def er_and_dictionary() -> tuple[str, str]:
    import app.models  # noqa: F401
    from app.core.db import Base

    lines = ["# Entity-relationship diagram", "", "Generated from the SQLAlchemy models.", "", "```mermaid", "erDiagram"]
    rels = set()
    for t in Base.metadata.sorted_tables:
        lines.append(f"    {t.name} {{")
        for c in t.columns:
            typ = type(c.type).__name__.lower().replace("varchar", "string")
            key = "PK" if c.primary_key else ("FK" if c.foreign_keys else "")
            lines.append(f"        {typ} {c.name}{(' ' + key) if key else ''}")
        lines.append("    }")
        for fk in t.foreign_keys:
            rels.add((fk.column.table.name, t.name, fk.parent.name))
    for parent, child, col in sorted(rels):
        lines.append(f'    {parent} ||--o{{ {child} : "{col}"')
    lines.append("```")

    dd = ["# Data dictionary", "", "Every table and column, generated from the models.", ""]
    for t in Base.metadata.sorted_tables:
        dd.append(f"## `{t.name}`")
        doc = (t.info or {}).get("doc", "")
        if doc:
            dd.append(doc)
        dd += ["", "| Column | Type | Null | Key |", "|---|---|---|---|"]
        for c in t.columns:
            key = "PK" if c.primary_key else (", ".join(f"FK → {fk.column.table.name}.{fk.column.name}" for fk in c.foreign_keys))
            dd.append(f"| `{c.name}` | {c.type} | {'yes' if c.nullable else 'no'} | {key} |")
        dd.append("")
    return "\n".join(lines) + "\n", "\n".join(dd)


def content_summary() -> str:
    from app.content_pack import DEFAULT_PACK, load_pack

    p = load_pack(DEFAULT_PACK)
    types = sorted({a.type for a in p.aids})
    counts = Counter((a.concept, a.type) for a in p.aids)
    names = {c.slug: c.name for c in p.concepts}
    out = ["# Content summary", "", f"{len(p.concepts)} concepts, {len(p.aids)} teaching aids, {len(p.questions)} questions.", "",
           "## Aids by concept and format", "", "| Concept | " + " | ".join(types) + " | Total |",
           "|---|" + "---|" * (len(types) + 1)]
    for c in p.concepts:
        row = [str(counts.get((c.slug, t), 0) or "") for t in types]
        out.append(f"| {names[c.slug]} | " + " | ".join(row) + f" | {sum(counts.get((c.slug, t), 0) for t in types)} |")
    pools = Counter(q.pool for q in p.questions)
    out += ["", "## Questions by pool", "", "| Pool | Count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(pools.items())]
    out += ["", "## Prerequisites", "", "| Concept | Requires |", "|---|---|"]
    out += [f"| {c.name} | {', '.join(names[x] for x in c.prerequisites) or '–'} |" for c in p.concepts]
    sources = Counter(a.source for a in p.aids if a.delivery == "external_url")
    out += ["", "## External sources", ""] + [f"- {s}: {n}" for s, n in sources.most_common()]
    return "\n".join(out) + "\n"


def _table(rows: list[dict], cols: list[str] | None = None) -> list[str]:
    if not rows:
        return ["_no data_"]
    cols = cols or list(rows[0])
    out = ["| " + " | ".join(c.replace("_", " ") for c in cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return out


def results() -> str:
    out = ["# Results", "", "Generated from research/outputs/*.json (run `make research` to regenerate).", ""]
    for name, title in (("simulation", "Simulation study (synthetic course)"), ("simulation_dsa", "Simulation study (real DSA course)")):
        p = RES / f"{name}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        out += [f"## {title}", "", f"Seeds: report {d['config']['report_seeds']}, {d['config']['n']} learners x {d['config']['steps']} sessions.", "",
                "### Paired differences in area under the learning curve", ""]
        out += _table([{"comparison": f"{x['a']} − {x['b']}", "format effect": x["affinity_level"], "difference": x["mean_diff"],
                        "95% CI": f"[{x['ci95'][0]}, {x['ci95'][1]}]"} for x in d["paired_differences"]])
        out += ["", "### Policies (mean over reporting seeds)", ""]
        out += _table([{k: r[k] for k in ("affinity_level", "policy", "auc_known", "auc_known_sd", "final_known", "steps_to_all")}
                       for r in d["policy_summary"]])
        out += ["", "### Learning-preference recovery", ""]
        out += _table([{k: r[k] for k in ("style_case", "start_style_cos", "final_style_cos")} for r in d["style_recovery"]])
        t = d["tuning"]
        out += ["", f"Weights: {'tuned set adopted' if t['adopted'] else 'blueprint weights kept'} (rule: {t.get('rule', '')}); "
                f"validation difference {t['validation_diff_tuned_minus_v0']}.", "",
                "Checks: " + ", ".join(f"{k} = {v}" for k, v in d["checks"].items()), ""]
    for name, title in (("bkt_eval", "Knowledge tracing on ASSISTments 2009"), ("risk", "At-risk classifier on OULAD"),
                        ("cf_offline", "Collaborative filtering on OULAD"), ("personas", "Personas on OULAD")):
        p = RES / f"{name}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        out += [f"## {title}", "", d.get("note", ""), ""] + _table(d.get("table", [])) + [""]
        if name == "bkt_eval":
            out += [f"Median fitted parameters: {d['median_params']}. Cleaning: {d['cleaning']}.", ""]
        if name == "risk":
            out += [f"Top random-forest features: {d.get('top_features_random_forest')}.", ""]
        if name == "personas":
            out += _table(d.get("clusters", [])) + [""]
    return "\n".join(out) + "\n"


def appendices() -> str:
    from app.content_pack import DEFAULT_PACK, load_pack
    from app.services.settings import DEFAULTS, STUDY

    p = load_pack(DEFAULT_PACK)
    q = p.questionnaire
    out = ["# Appendices", "", "## A. Learning-preference questionnaire", "", q.get("intro", ""), "", f"_{q.get('note', '')}_", "",
           "| # | Dimension | Prompt | Option a | Option b | a points to |", "|---|---|---|---|---|---|"]
    poles = {"ar": ("active", "reflective"), "si": ("sensing", "intuitive"), "vv": ("visual", "verbal"), "sg": ("sequential", "global")}
    for i, it in enumerate(q.get("items", []), 1):
        pole = poles[it["dim"]][0 if it["a_pole"] > 0 else 1]
        out.append(f"| {i} | {it['dim']} | {it['prompt']} | {it['a']} | {it['b']} | {pole} |")
    out += ["", "Scoring: each answer is a vote of +1 or −1 for one pole; a dimension's score is the mean of its five votes (−1 to +1).", "",
            "## B. Pilot consent text (default; edit in Admin → Pilot study)", "", DEFAULTS[STUDY]["consent_text"], "",
            "## C. System Usability Scale and satisfaction items", ""]
    s = p.sus
    out += [f"{i}. {item}" for i, item in enumerate(s.get("items", []), 1)]
    out += ["", f"Scale: {', '.join(s.get('scale', []))}. {s.get('scoring', '')}", ""]
    out += [f"{i}. {item}" for i, item in enumerate(s.get("satisfaction", {}).get("items", []), 11)]
    return "\n".join(out) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diagrams.md").write_text(DIAGRAMS)
    er, dd = er_and_dictionary()
    (OUT / "er_diagram.md").write_text(er)
    (OUT / "data_dictionary.md").write_text(dd)
    (OUT / "content_summary.md").write_text(content_summary())
    (OUT / "results.md").write_text(results())
    (OUT / "appendices.md").write_text(appendices())
    shutil.copy(ROOT / "backend" / "openapi.json", OUT / "openapi.json")
    figs = RES / "figures"
    if figs.exists():
        (OUT / "figures").mkdir(exist_ok=True)
        for f in figs.glob("*.png"):
            shutil.copy(f, OUT / "figures" / f.name)
    print("report assets written to", OUT)


if __name__ == "__main__":
    main()
