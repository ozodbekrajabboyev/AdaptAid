"""Load a content pack into the database (idempotent upsert).

Re-running the seed updates titles, bodies and questions in place, keeps fitted BKT
parameters, and deactivates aids/questions that were removed from the pack, so history
(recommendations, responses) still points at valid rows.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.content_pack import Pack
from app.models import AidConcept, Concept, ConceptPrerequisite, Course, Question, TeachingAid
from app.models.base import AidType, Delivery, Interactivity, QuestionPool
from app.services import settings as settings_svc


@dataclass
class SeedResult:
    course_id: int
    concepts: int
    aids: int
    questions: int
    deactivated_aids: int
    deactivated_questions: int


def seed_pack(db: Session, pack: Pack) -> SeedResult:
    course = db.scalar(select(Course).where(Course.code == pack.code))
    if course is None:
        course = Course(code=pack.code, title=pack.title, description=pack.description)
        db.add(course)
        db.flush()
    else:
        course.title, course.description = pack.title, pack.description

    concepts: dict[str, Concept] = {
        c.slug: c for c in db.scalars(select(Concept).where(Concept.course_id == course.id))
    }
    for spec in pack.concepts:
        c = concepts.get(spec.slug)
        if c is None:
            c = Concept(course_id=course.id, slug=spec.slug)
            db.add(c)
            concepts[spec.slug] = c
        c.name, c.description, c.order_index, c.is_study = spec.name, spec.description, spec.order, spec.is_study
    db.flush()

    ids = [c.id for c in concepts.values()]
    db.execute(delete(ConceptPrerequisite).where(ConceptPrerequisite.concept_id.in_(ids)))
    for spec in pack.concepts:
        for p in spec.prerequisites:
            if p in concepts:
                db.add(ConceptPrerequisite(concept_id=concepts[spec.slug].id, prereq_id=concepts[p].id))

    aids: dict[str, TeachingAid] = {
        a.slug: a for a in db.scalars(select(TeachingAid).where(TeachingAid.course_id == course.id))
    }
    seen_aids: set[str] = set()
    for spec in pack.aids:
        a = aids.get(spec.slug)
        if a is None:
            a = TeachingAid(course_id=course.id, slug=spec.slug)
            db.add(a)
            aids[spec.slug] = a
        a.title, a.description = spec.title, spec.description
        a.aid_type, a.delivery = AidType(spec.type), Delivery(spec.delivery)
        a.url, a.body_md, a.component_key = spec.url, spec.body, spec.component
        a.source, a.difficulty, a.duration_min, a.default_order = spec.source, spec.difficulty, spec.duration, spec.order
        a.style_ar, a.style_si, a.style_vv, a.style_sg = spec.style
        a.interactivity = Interactivity(spec.interactivity)
        a.is_active = True
        seen_aids.add(spec.slug)
    db.flush()
    for spec in pack.aids:
        a = aids[spec.slug]
        db.execute(delete(AidConcept).where(AidConcept.aid_id == a.id))
        db.add(AidConcept(aid_id=a.id, concept_id=concepts[spec.concept].id, weight=1.0))
    deactivated_aids = 0
    for slug, a in aids.items():
        if slug not in seen_aids and a.is_active:
            a.is_active = False
            deactivated_aids += 1

    questions: dict[str, Question] = {
        q.key: q for q in db.scalars(select(Question).where(Question.course_id == course.id))
    }
    seen_q: set[str] = set()
    for spec in pack.questions:
        q = questions.get(spec.key)
        if q is None:
            q = Question(course_id=course.id, key=spec.key)
            db.add(q)
            questions[spec.key] = q
        q.concept_id = concepts[spec.concept].id
        q.stem, q.options, q.correct_index, q.explanation = spec.stem, spec.options, spec.answer, spec.explanation
        q.difficulty, q.pool, q.form = spec.difficulty, QuestionPool(spec.pool), spec.form
        q.aid_id = aids[spec.aid].id if spec.aid and spec.aid in aids else None
        q.is_active = True
        seen_q.add(spec.key)
    deactivated_q = 0
    for key, q in questions.items():
        if key not in seen_q and q.is_active:
            q.is_active = False
            deactivated_q += 1

    settings_svc.ensure_defaults(db)
    if pack.questionnaire:
        settings_svc.put(db, settings_svc.QUESTIONNAIRE, pack.questionnaire)
    if pack.sus:
        settings_svc.put(db, settings_svc.SUS, pack.sus)
    db.flush()
    return SeedResult(course.id, len(pack.concepts), len(pack.aids), len(pack.questions), deactivated_aids, deactivated_q)
