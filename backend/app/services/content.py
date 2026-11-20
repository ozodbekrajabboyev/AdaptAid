"""Content queries, CRUD and CSV import/export."""

from __future__ import annotations

import csv
import io
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AidConcept, Concept, ConceptPrerequisite, Course, Question, TeachingAid
from app.models.base import AidType, Delivery, Interactivity, QuestionPool
from app.schemas.content import (
    AidDetail,
    AidIn,
    AidSummary,
    ConceptOut,
    ImportResult,
    QuestionIn,
    QuestionOut,
)

AID_CSV_FIELDS = [
    "slug", "concept_slug", "title", "description", "type", "delivery", "url", "component", "source",
    "difficulty", "duration", "order", "style_ar", "style_si", "style_vv", "style_sg", "interactivity", "body_md",
]
QUESTION_CSV_FIELDS = [
    "key", "concept_slug", "pool", "form", "aid_slug", "stem", "option_a", "option_b", "option_c", "option_d",
    "answer", "explanation", "difficulty",
]


def concept_map(db: Session, course_id: int) -> dict[int, Concept]:
    return {c.id: c for c in db.scalars(select(Concept).where(Concept.course_id == course_id))}


def primary_concepts(db: Session, aid_ids: list[int] | None = None) -> dict[int, int]:
    stmt = select(AidConcept.aid_id, AidConcept.concept_id).order_by(AidConcept.weight.desc())
    if aid_ids is not None:
        stmt = stmt.where(AidConcept.aid_id.in_(aid_ids))
    out: dict[int, int] = {}
    for aid_id, concept_id in db.execute(stmt):
        out.setdefault(aid_id, concept_id)
    return out


def list_concepts(db: Session, course_id: int) -> list[ConceptOut]:
    concepts = sorted(concept_map(db, course_id).values(), key=lambda c: c.order_index)
    prereqs: dict[int, list[int]] = defaultdict(list)
    for row in db.scalars(select(ConceptPrerequisite).where(ConceptPrerequisite.concept_id.in_([c.id for c in concepts]))):
        prereqs[row.concept_id].append(row.prereq_id)
    counts = dict(
        db.execute(
            select(AidConcept.concept_id, func.count())
            .join(TeachingAid, TeachingAid.id == AidConcept.aid_id)
            .where(TeachingAid.is_active)
            .group_by(AidConcept.concept_id)
        ).all()
    )
    return [
        ConceptOut(
            id=c.id, slug=c.slug, name=c.name, description=c.description, order_index=c.order_index,
            is_study=c.is_study, prerequisites=sorted(prereqs[c.id]),
            bkt={"prior": c.bkt_prior, "learn": c.bkt_learn, "guess": c.bkt_guess, "slip": c.bkt_slip},
            params_source=c.params_source, n_aids=counts.get(c.id, 0),
        )
        for c in concepts
    ]


def _summary(a: TeachingAid, concept: Concept | None) -> dict:
    return {
        "id": a.id, "slug": a.slug, "title": a.title, "description": a.description, "aid_type": a.aid_type,
        "delivery": a.delivery, "source": a.source, "difficulty": a.difficulty, "duration_min": a.duration_min,
        "concept_id": concept.id if concept else 0, "concept_name": concept.name if concept else "",
        "style": [a.style_ar, a.style_si, a.style_vv, a.style_sg], "interactivity": a.interactivity,
        "default_order": a.default_order, "is_active": a.is_active,
    }


def list_aids(
    db: Session, course_id: int | None = None, concept_id: int | None = None, aid_type: str | None = None,
    q: str | None = None, include_inactive: bool = False,
) -> list[AidSummary]:
    stmt = select(TeachingAid)
    if course_id:
        stmt = stmt.where(TeachingAid.course_id == course_id)
    if not include_inactive:
        stmt = stmt.where(TeachingAid.is_active)
    if aid_type:
        stmt = stmt.where(TeachingAid.aid_type == aid_type)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(TeachingAid.title).like(like) | func.lower(TeachingAid.description).like(like))
    aids = list(db.scalars(stmt))
    primary = primary_concepts(db, [a.id for a in aids])
    if concept_id:
        aids = [a for a in aids if primary.get(a.id) == concept_id]
    concepts = {c.id: c for c in db.scalars(select(Concept).where(Concept.id.in_(set(primary.values()) or {0})))}
    out = [AidSummary(**_summary(a, concepts.get(primary.get(a.id, 0)))) for a in aids]
    out.sort(key=lambda s: (concepts[s.concept_id].order_index if s.concept_id in concepts else 999, s.default_order, s.id))
    return out


def aid_detail(db: Session, aid_id: int) -> AidDetail:
    a = db.get(TeachingAid, aid_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That teaching aid does not exist.")
    cid = primary_concepts(db, [a.id]).get(a.id)
    concept = db.get(Concept, cid) if cid else None
    n_drill = db.scalar(select(func.count()).select_from(Question).where(Question.aid_id == a.id, Question.is_active)) or 0
    return AidDetail(**_summary(a, concept), url=a.url, body_md=a.body_md, component_key=a.component_key,
                     n_drill_questions=n_drill)


def save_aid(db: Session, body: AidIn, user_id: int, aid_id: int | None = None) -> TeachingAid:
    problem = body.check_delivery()
    if problem:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, problem)
    concept = db.get(Concept, body.concept_id)
    if concept is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That concept does not exist.")
    if aid_id is None:
        clash = db.scalar(select(TeachingAid.id).where(TeachingAid.course_id == concept.course_id, TeachingAid.slug == body.slug))
        if clash:
            raise HTTPException(status.HTTP_409_CONFLICT, "Another aid already uses that slug.")
        a = TeachingAid(course_id=concept.course_id, slug=body.slug, created_by=user_id)
        db.add(a)
    else:
        a = db.get(TeachingAid, aid_id)
        if a is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That teaching aid does not exist.")
    data = body.model_dump(exclude={"concept_id"})
    for k, v in data.items():
        setattr(a, k, v)
    a.is_active = True
    db.flush()
    existing = db.scalars(select(AidConcept).where(AidConcept.aid_id == a.id)).all()
    for link in existing:
        db.delete(link)
    db.flush()
    db.add(AidConcept(aid_id=a.id, concept_id=concept.id, weight=1.0))
    db.flush()
    return a


def question_out(q: Question) -> QuestionOut:
    return QuestionOut(
        id=q.id, key=q.key, concept_id=q.concept_id, stem=q.stem, options=list(q.options),
        correct_index=q.correct_index, explanation=q.explanation, difficulty=q.difficulty, pool=q.pool,
        form=q.form, aid_id=q.aid_id, is_active=q.is_active,
    )


def save_question(db: Session, body: QuestionIn, question_id: int | None = None) -> Question:
    concept = db.get(Concept, body.concept_id)
    if concept is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That concept does not exist.")
    if body.pool == QuestionPool.study and body.form is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Study questions need form A or B.")
    if question_id is None:
        if db.scalar(select(Question.id).where(Question.course_id == concept.course_id, Question.key == body.key)):
            raise HTTPException(status.HTTP_409_CONFLICT, "Another question already uses that key.")
        q = Question(course_id=concept.course_id, key=body.key)
        db.add(q)
    else:
        q = db.get(Question, question_id)
        if q is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That question does not exist.")
    for k, v in body.model_dump().items():
        setattr(q, k, v)
    q.is_active = True
    db.flush()
    return q


# ------------------------------------------------------------------ CSV


def export_aids_csv(db: Session, course_id: int) -> str:
    concepts = concept_map(db, course_id)
    aids = list(db.scalars(select(TeachingAid).where(TeachingAid.course_id == course_id, TeachingAid.is_active)))
    primary = primary_concepts(db, [a.id for a in aids])
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=AID_CSV_FIELDS)
    w.writeheader()
    for a in sorted(aids, key=lambda a: (concepts[primary[a.id]].order_index if a.id in primary else 999, a.default_order)):
        c = concepts.get(primary.get(a.id, 0))
        w.writerow({
            "slug": a.slug, "concept_slug": c.slug if c else "", "title": a.title, "description": a.description,
            "type": a.aid_type.value, "delivery": a.delivery.value, "url": a.url or "", "component": a.component_key or "",
            "source": a.source, "difficulty": a.difficulty, "duration": a.duration_min, "order": a.default_order,
            "style_ar": a.style_ar, "style_si": a.style_si, "style_vv": a.style_vv, "style_sg": a.style_sg,
            "interactivity": a.interactivity.value, "body_md": a.body_md or "",
        })
    return buf.getvalue()


def export_questions_csv(db: Session, course_id: int) -> str:
    concepts = concept_map(db, course_id)
    aids = {a.id: a.slug for a in db.scalars(select(TeachingAid).where(TeachingAid.course_id == course_id))}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=QUESTION_CSV_FIELDS)
    w.writeheader()
    for q in db.scalars(select(Question).where(Question.course_id == course_id, Question.is_active).order_by(Question.key)):
        opts = list(q.options) + [""] * (4 - len(q.options))
        w.writerow({
            "key": q.key, "concept_slug": concepts[q.concept_id].slug, "pool": q.pool.value, "form": q.form or "",
            "aid_slug": aids.get(q.aid_id, "") if q.aid_id else "", "stem": q.stem,
            "option_a": opts[0], "option_b": opts[1], "option_c": opts[2], "option_d": opts[3],
            "answer": "ABCD"[q.correct_index], "explanation": q.explanation, "difficulty": q.difficulty,
        })
    return buf.getvalue()


def _read_csv(data: bytes) -> list[dict[str, str]]:
    text = data.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def import_aids_csv(db: Session, course_id: int, data: bytes, user_id: int) -> ImportResult:
    concepts = {c.slug: c for c in concept_map(db, course_id).values()}
    created = updated = 0
    errors: list[str] = []
    for i, row in enumerate(_read_csv(data), start=2):
        try:
            concept = concepts.get(row.get("concept_slug", ""))
            if concept is None:
                raise ValueError(f"unknown concept '{row.get('concept_slug', '')}'")
            body = AidIn(
                slug=row["slug"], title=row["title"], description=row.get("description") or row["title"],
                concept_id=concept.id, aid_type=AidType(row["type"]), delivery=Delivery(row["delivery"]),
                url=row.get("url") or None, body_md=row.get("body_md") or None,
                component_key=row.get("component") or None, source=row.get("source") or "AdaptAid",
                difficulty=int(row.get("difficulty") or 2), duration_min=int(row.get("duration") or 10),
                style_ar=float(row.get("style_ar") or 0), style_si=float(row.get("style_si") or 0),
                style_vv=float(row.get("style_vv") or 0), style_sg=float(row.get("style_sg") or 0),
                interactivity=Interactivity(row.get("interactivity") or "expositive"),
                default_order=int(row.get("order") or 0),
            )
            existing = db.scalar(select(TeachingAid).where(TeachingAid.course_id == course_id, TeachingAid.slug == body.slug))
            with db.begin_nested():
                save_aid(db, body, user_id, existing.id if existing else None)
            if existing:
                updated += 1
            else:
                created += 1
        except HTTPException as e:
            errors.append(f"row {i}: {e.detail}")
        except (KeyError, ValueError) as e:
            errors.append(f"row {i}: {e}")
    return ImportResult(created=created, updated=updated, errors=errors)


def import_questions_csv(db: Session, course_id: int, data: bytes) -> ImportResult:
    concepts = {c.slug: c for c in concept_map(db, course_id).values()}
    aids = {a.slug: a.id for a in db.scalars(select(TeachingAid).where(TeachingAid.course_id == course_id))}
    created = updated = 0
    errors: list[str] = []
    for i, row in enumerate(_read_csv(data), start=2):
        try:
            concept = concepts.get(row.get("concept_slug", ""))
            if concept is None:
                raise ValueError(f"unknown concept '{row.get('concept_slug', '')}'")
            answer = (row.get("answer") or "").strip().upper()
            if answer not in ("A", "B", "C", "D"):
                raise ValueError("answer must be A, B, C or D")
            body = QuestionIn(
                key=row["key"], concept_id=concept.id, stem=row["stem"],
                options=[row["option_a"], row["option_b"], row["option_c"], row["option_d"]],
                correct_index="ABCD".index(answer), explanation=row["explanation"],
                difficulty=int(row.get("difficulty") or 2), pool=QuestionPool(row.get("pool") or "check"),
                form=(row.get("form") or None), aid_id=aids.get(row.get("aid_slug") or "") if row.get("aid_slug") else None,
            )
            existing = db.scalar(select(Question).where(Question.course_id == course_id, Question.key == body.key))
            with db.begin_nested():
                save_question(db, body, existing.id if existing else None)
            if existing:
                updated += 1
            else:
                created += 1
        except HTTPException as e:
            errors.append(f"row {i}: {e.detail}")
        except (KeyError, ValueError) as e:
            errors.append(f"row {i}: {e}")
    return ImportResult(created=created, updated=updated, errors=errors)


def default_course(db: Session) -> Course:
    course = db.scalar(select(Course).order_by(Course.id))
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No course has been loaded yet. Run `adaptaid seed`.")
    return course
