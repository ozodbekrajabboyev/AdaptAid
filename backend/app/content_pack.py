"""Load and validate a content pack (content/<course>/). Pure Python: no database access.

Used by `adaptaid seed`, `adaptaid validate-content`, `adaptaid check-links` and the research
scripts (which build an engine Catalogue from the same files).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from engine.graph import CycleError, topological_order

REPO = Path(__file__).resolve().parents[2]
DEFAULT_PACK = REPO / "content" / "dsa"

AID_TYPES = {"video", "animation", "interactive", "notes", "worked_example", "cheat_sheet", "concept_map", "practice", "article"}
DELIVERIES = {"native_md", "external_url", "interactive_component"}
COMPONENTS = {"sorting-stepper", "recursion-stack", "bst-builder"}
POOLS = {"diagnostic", "check", "drill", "study"}

# RUBRIC.md defaults: (ar, si, vv, sg), interactivity
DEFAULT_STYLE: dict[str, tuple[tuple[float, float, float, float], str]] = {
    "video": ((-0.3, 0.0, 0.6, 0.5), "expositive"),
    "animation": ((0.3, 0.2, 0.9, 0.6), "mixed"),
    "interactive": ((0.9, 0.5, 0.8, 0.4), "active"),
    "notes": ((-0.5, 0.0, -0.8, 0.6), "expositive"),
    "worked_example": ((0.1, 0.8, -0.2, 0.8), "expositive"),
    "cheat_sheet": ((0.0, 0.2, -0.4, -0.8), "expositive"),
    "concept_map": ((-0.2, -0.5, 0.8, -0.8), "expositive"),
    "practice": ((0.9, 0.6, -0.3, 0.3), "active"),
    "article": ((-0.4, -0.4, -0.7, 0.3), "expositive"),
}

MIN_POOL = {"diagnostic": 1, "check": 10, "drill": 5}
MIN_STUDY_PER_FORM = 5


@dataclass
class AidSpec:
    slug: str
    concept: str
    title: str
    type: str
    delivery: str
    description: str
    difficulty: int
    duration: int
    order: int
    style: tuple[float, float, float, float]
    interactivity: str
    source: str = "AdaptAid"
    url: str | None = None
    body: str | None = None  # markdown text (loaded from aids/*.md)
    body_file: str | None = None
    component: str | None = None


@dataclass
class QuestionSpec:
    key: str
    concept: str
    pool: str
    stem: str
    options: list[str]
    answer: int
    explanation: str
    difficulty: int
    aid: str | None = None
    form: str | None = None


@dataclass
class ConceptSpec:
    slug: str
    name: str
    description: str
    prerequisites: list[str]
    order: int
    is_study: bool


@dataclass
class Pack:
    root: Path
    code: str
    title: str
    description: str
    concepts: list[ConceptSpec]
    aids: list[AidSpec]
    questions: list[QuestionSpec]
    questionnaire: dict
    sus: dict
    load_errors: list[str] = field(default_factory=list)


def _read_json(path: Path, errors: list[str]) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{path.name}: file is missing")
    except json.JSONDecodeError as e:
        errors.append(f"{path.name}: invalid JSON ({e})")
    return {}


def load_pack(root: Path | str = DEFAULT_PACK) -> Pack:
    root = Path(root)
    errors: list[str] = []
    course = _read_json(root / "course.json", errors)
    syllabus: list[str] = course.get("concepts_in_syllabus_order", [])
    study = set(course.get("study_concepts", []))
    concepts: list[ConceptSpec] = []
    aids: list[AidSpec] = []
    questions: list[QuestionSpec] = []

    for order, slug in enumerate(syllabus):
        path = root / "concepts" / f"{slug}.json"
        if not path.exists():
            errors.append(f"concepts/{slug}.json: missing (listed in course.json)")
            continue
        data = _read_json(path, errors)
        if not data:
            continue
        if data.get("slug") != slug:
            errors.append(f"concepts/{slug}.json: slug field is {data.get('slug')!r}, expected {slug!r}")
        concepts.append(
            ConceptSpec(
                slug=slug,
                name=data.get("name", slug),
                description=data.get("description", ""),
                prerequisites=list(data.get("prerequisites", [])),
                order=order,
                is_study=slug in study,
            )
        )
        for a in data.get("aids", []):
            t = a.get("type", "")
            default_style, default_inter = DEFAULT_STYLE.get(t, ((0.0, 0.0, 0.0, 0.0), "expositive"))
            body = None
            if a.get("delivery") == "native_md" and a.get("body"):
                body_path = root / "aids" / a["body"]
                body = body_path.read_text(encoding="utf-8") if body_path.exists() else None
            aids.append(
                AidSpec(
                    slug=a.get("slug", ""),
                    concept=slug,
                    title=a.get("title", ""),
                    type=t,
                    delivery=a.get("delivery", ""),
                    description=a.get("description", ""),
                    difficulty=int(a.get("difficulty", 2)),
                    duration=int(a.get("duration", 10)),
                    order=int(a.get("order", 0)),
                    style=tuple(a.get("style", default_style)),  # type: ignore[arg-type]
                    interactivity=a.get("interactivity", default_inter),
                    source=a.get("source", "AdaptAid"),
                    url=a.get("url"),
                    body=body,
                    body_file=a.get("body"),
                    component=a.get("component"),
                )
            )
        for q in data.get("questions", []):
            questions.append(
                QuestionSpec(
                    key=q.get("key", ""),
                    concept=slug,
                    pool=q.get("pool", ""),
                    stem=q.get("stem", ""),
                    options=list(q.get("options", [])),
                    answer=int(q.get("answer", -1)),
                    explanation=q.get("explanation", ""),
                    difficulty=int(q.get("difficulty", 2)),
                    aid=q.get("aid"),
                    form=q.get("form"),
                )
            )
    questionnaire = _read_json(root / "questionnaire.json", errors)
    sus = _read_json(root / "sus.json", errors)
    return Pack(root, course.get("code", "COURSE"), course.get("title", ""), course.get("description", ""),
                concepts, aids, questions, questionnaire, sus, errors)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", "", text)).strip().lower()


def validate(pack: Pack, only: set[str] | None = None) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). `only` limits per-concept checks to some concept slugs."""
    errors = list(pack.load_errors)
    warnings: list[str] = []
    slugs = [c.slug for c in pack.concepts]
    known = set(slugs)

    edges = []
    for c in pack.concepts:
        for p in c.prerequisites:
            if p not in known:
                errors.append(f"{c.slug}: prerequisite {p!r} is not a concept in this course")
            else:
                edges.append((c.slug, p))
    try:
        topological_order(slugs, edges)
    except CycleError as e:
        errors.append(f"prerequisite graph: {e}")

    aid_slugs: dict[str, AidSpec] = {}
    for a in pack.aids:
        if a.slug in aid_slugs:
            errors.append(f"aid {a.slug}: duplicate slug")
        aid_slugs[a.slug] = a

    qkeys: set[str] = set()
    for q in pack.questions:
        if q.key in qkeys:
            errors.append(f"question {q.key}: duplicate key")
        qkeys.add(q.key)

    for c in pack.concepts:
        if only and c.slug not in only:
            continue
        caids = [a for a in pack.aids if a.concept == c.slug]
        for a in caids:
            where = f"{c.slug}/{a.slug}"
            if a.type not in AID_TYPES:
                errors.append(f"{where}: unknown type {a.type!r}")
            if a.delivery not in DELIVERIES:
                errors.append(f"{where}: unknown delivery {a.delivery!r}")
            if not a.title or not a.description:
                errors.append(f"{where}: title and description are required")
            if not 1 <= a.difficulty <= 5:
                errors.append(f"{where}: difficulty must be 1-5")
            if len(a.style) != 4 or any(not -1 <= x <= 1 for x in a.style):
                errors.append(f"{where}: style must be 4 numbers in [-1, 1]")
            if a.delivery == "native_md":
                if not a.body or len(a.body.strip()) < 80:
                    errors.append(f"{where}: body file aids/{a.body_file} is missing or too short")
                if a.body and "<" in a.body and re.search(r"<\s*(script|iframe|div|span|img)\b", a.body, re.I):
                    errors.append(f"{where}: raw HTML is not allowed in markdown aids")
            if a.delivery == "external_url" and not (a.url or "").startswith("https://"):
                errors.append(f"{where}: external aids need an https:// url")
            if a.delivery == "interactive_component" and a.component not in COMPONENTS:
                errors.append(f"{where}: component must be one of {sorted(COMPONENTS)}")
            if not a.slug.startswith(f"{c.slug}-"):
                warnings.append(f"{where}: slug should start with '{c.slug}-'")

        types = {a.type for a in caids}
        if len(types) < 4:
            errors.append(f"{c.slug}: needs at least 4 aid types (has {sorted(types)})")
        if not any(a.style[2] > 0.3 for a in caids) or not any(a.style[2] < -0.3 for a in caids):
            errors.append(f"{c.slug}: needs aids on both sides of visual/verbal")
        if not any(a.style[0] > 0.3 for a in caids) or not any(a.style[0] < -0.3 for a in caids):
            errors.append(f"{c.slug}: needs aids on both sides of active/reflective")
        if not any(a.type == "practice" for a in caids):
            errors.append(f"{c.slug}: needs a practice aid")

        cq = [q for q in pack.questions if q.concept == c.slug]
        for q in cq:
            where = f"{c.slug}/{q.key}"
            if q.pool not in POOLS:
                errors.append(f"{where}: unknown pool {q.pool!r}")
            if len(q.options) != 4 or len({_norm(o) for o in q.options}) != 4:
                errors.append(f"{where}: needs exactly 4 different options")
            if not 0 <= q.answer < len(q.options):
                errors.append(f"{where}: answer index out of range")
            if not q.stem.strip() or not q.explanation.strip():
                errors.append(f"{where}: stem and explanation are required")
            if not 1 <= q.difficulty <= 3:
                errors.append(f"{where}: difficulty must be 1-3")
            if q.pool == "drill":
                aid = aid_slugs.get(q.aid or "")
                if aid is None or aid.type != "practice" or aid.concept != c.slug:
                    errors.append(f"{where}: drill items must name this concept's practice aid")
            if q.pool == "study" and q.form not in ("A", "B"):
                errors.append(f"{where}: study items need form A or B")
            if any("all of the above" in _norm(o) or "none of the above" in _norm(o) for o in q.options):
                warnings.append(f"{where}: avoid 'all/none of the above'")
        for pool, n in MIN_POOL.items():
            have = sum(1 for q in cq if q.pool == pool)
            if have < n:
                errors.append(f"{c.slug}: pool {pool} has {have} items, needs {n}")
        if c.is_study:
            for form in ("A", "B"):
                have = sum(1 for q in cq if q.pool == "study" and q.form == form)
                if have < MIN_STUDY_PER_FORM:
                    errors.append(f"{c.slug}: study form {form} has {have} items, needs {MIN_STUDY_PER_FORM}")
        answers = [q.answer for q in cq]
        if answers and max(answers.count(i) for i in range(4)) > 0.6 * len(answers):
            warnings.append(f"{c.slug}: correct answers are mostly in one position; vary them")

    # Study items must not leak into practice material.
    study_stems = {_norm(q.stem) for q in pack.questions if q.pool == "study"}
    other_stems = {_norm(q.stem) for q in pack.questions if q.pool != "study"}
    for s in study_stems & other_stems:
        errors.append(f"study item text also appears in another pool: {s[:60]}...")
    bodies = " ".join(_norm(a.body or "") for a in pack.aids)
    for s in study_stems:
        if len(s) > 30 and s in bodies:
            errors.append(f"study item text appears inside an aid body: {s[:60]}...")

    if pack.questionnaire and len(pack.questionnaire.get("items", [])) != 20:
        errors.append("questionnaire.json: expected 20 items")
    return errors, warnings


# ------------------------------------------------------------------ link checking


def check_url(url: str, timeout: float = 15.0) -> tuple[bool, str]:
    import httpx

    headers = {"User-Agent": "Mozilla/5.0 (compatible; AdaptAid link checker)"}
    try:
        if "youtube.com/watch" in url or "youtu.be/" in url:
            r = httpx.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"},
                          headers=headers, timeout=timeout, follow_redirects=True)
            if r.status_code == 200:
                d = r.json()
                return True, f"{d.get('title', '')} ({d.get('author_name', '')})"
            return False, f"oEmbed HTTP {r.status_code}"
        r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        return (200 <= r.status_code < 400), f"HTTP {r.status_code}"
    except httpx.HTTPError as e:
        return False, type(e).__name__
