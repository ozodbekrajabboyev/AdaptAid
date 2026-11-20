"""Quizzes: diagnostic, quick checks after an aid, drills inside practice aids, pre/post tests.

Every answer runs one Bayesian Knowledge Tracing update. Finishing a quick check turns
the answers into the aid's residual gain, updates the learner's preference profile and
regenerates the recommendation list.
"""

from __future__ import annotations

import random

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    AidUse,
    Attempt,
    Concept,
    Enrollment,
    Mastery,
    Question,
    RecommendationItem,
    Response,
    StyleProfile,
    StyleUpdate,
    TeachingAid,
    User,
)
from app.models.base import AttemptKind, CheckStatus, QuestionPool
from app.schemas.learning import AnswerOut, AttemptOut, ConceptChange, FinishOut, QuizQuestion
from app.services import learner as learner_svc
from app.services import recommend as rec_svc
from app.services import settings as settings_svc
from engine import clock
from engine.bkt import MASTERED, BKTParams
from engine.bkt import update as bkt_update
from engine.signals import residual_gain
from engine.style import StyleState
from engine.style import update as style_update

CHECK_SIZE = 3


def _params(c: Concept) -> BKTParams:
    return BKTParams(c.bkt_prior, c.bkt_learn, c.bkt_guess, c.bkt_slip)


def _seen_questions(db: Session, user_id: int) -> dict[int, object]:
    rows = db.execute(
        select(Response.question_id, func.max(Response.created_at)).where(Response.user_id == user_id)
        .group_by(Response.question_id)
    ).all()
    return {qid: ts for qid, ts in rows}


def _pick_check_questions(db: Session, user: User, concept_id: int) -> list[Question]:
    pool = list(db.scalars(select(Question).where(Question.concept_id == concept_id, Question.pool == QuestionPool.check,
                                                  Question.is_active)))
    seen = _seen_questions(db, user.id)
    rng = random.Random(f"{user.id}-{concept_id}-{len(seen)}")
    unseen = [q for q in pool if q.id not in seen]
    rng.shuffle(unseen)
    # Repeats only when the pool runs out, least recently seen first.
    repeats = sorted((q for q in pool if q.id in seen), key=lambda q: seen[q.id])  # type: ignore[arg-type, return-value]
    return (unseen + repeats)[:CHECK_SIZE]


def _attempt_out(db: Session, attempt: Attempt) -> AttemptOut:
    qs = {q.id: q for q in db.scalars(select(Question).where(Question.id.in_(attempt.question_ids or [0])))}
    names = {c.id: c.name for c in db.scalars(select(Concept).where(Concept.id.in_({q.concept_id for q in qs.values()} or {0})))}
    answered = {r.question_id: r.chosen_index for r in db.scalars(select(Response).where(Response.attempt_id == attempt.id))}
    return AttemptOut(
        id=attempt.id, kind=attempt.kind, concept_id=attempt.concept_id,
        questions=[QuizQuestion(id=q.id, concept_id=q.concept_id, concept_name=names.get(q.concept_id, ""),
                                stem=q.stem, options=list(q.options))
                   for qid in attempt.question_ids if (q := qs.get(qid))],
        answered=answered,
    )


def start(db: Session, user: User, kind: AttemptKind, concept_id: int | None = None, use_id: int | None = None,
          aid_id: int | None = None) -> AttemptOut:
    course = learner_svc.course_for(db, user)
    concepts = sorted(db.scalars(select(Concept).where(Concept.course_id == course.id)), key=lambda c: c.order_index)
    use = None
    form = None
    if kind == AttemptKind.diagnostic:
        questions = []
        for c in concepts:
            q = db.scalars(select(Question).where(Question.concept_id == c.id, Question.pool == QuestionPool.diagnostic,
                                                  Question.is_active).order_by(Question.key)).first()
            if q:
                questions.append(q)
    elif kind == AttemptKind.check:
        if use_id is not None:
            use = db.get(AidUse, use_id)
            if use is None or use.user_id != user.id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "That aid session was not found.")
            if use.check_status == CheckStatus.done:
                raise HTTPException(status.HTTP_409_CONFLICT, "You already took the quick check for this aid.")
            concept_id = use.concept_id
        if concept_id is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "A quick check needs a concept.")
        questions = _pick_check_questions(db, user, concept_id)
    elif kind == AttemptKind.drill:
        aid = db.get(TeachingAid, aid_id) if aid_id else None
        if aid is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "That practice aid was not found.")
        questions = list(db.scalars(select(Question).where(Question.aid_id == aid.id, Question.pool == QuestionPool.drill,
                                                           Question.is_active).order_by(Question.key)))
        concept_id = questions[0].concept_id if questions else None
    else:  # pre/post test
        enrollment = learner_svc.enrollment_for(db, user)
        order = (enrollment.form_order if enrollment and enrollment.form_order else "AB")
        form = order[0] if kind == AttemptKind.pretest else order[1]
        study_ids = [c.id for c in concepts if c.is_study]
        questions = list(db.scalars(select(Question).where(Question.concept_id.in_(study_ids or [0]),
                                                           Question.pool == QuestionPool.study, Question.form == form,
                                                           Question.is_active).order_by(Question.key)))
    if not questions:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "There are no questions for this yet.")
    attempt = Attempt(user_id=user.id, kind=kind, concept_id=concept_id, aid_id=use.aid_id if use else aid_id,
                      rec_item_id=use.rec_item_id if use else None, use_id=use.id if use else None,
                      question_ids=[q.id for q in questions], form=form, started_at=clock.now(),
                      n_total=len(questions))
    db.add(attempt)
    db.flush()
    return _attempt_out(db, attempt)


def get_attempt(db: Session, user: User, attempt_id: int) -> Attempt:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That quiz was not found.")
    return attempt


def attempt_out(db: Session, user: User, attempt_id: int) -> AttemptOut:
    return _attempt_out(db, get_attempt(db, user, attempt_id))


def _answer_out(r: Response, q: Question) -> AnswerOut:
    return AnswerOut(question_id=q.id, correct=r.correct, correct_index=q.correct_index, explanation=q.explanation,
                     concept_id=q.concept_id, p_before=round(r.p_before, 4), p_after=round(r.p_after, 4),
                     is_repeat=r.is_repeat)


def answer(db: Session, user: User, attempt_id: int, question_id: int, chosen: int, time_ms: int | None) -> AnswerOut:
    attempt = get_attempt(db, user, attempt_id)
    if question_id not in attempt.question_ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "That question is not part of this quiz.")
    q = db.get(Question, question_id)
    assert q is not None
    existing = db.scalar(select(Response).where(Response.attempt_id == attempt.id, Response.question_id == question_id))
    if existing:  # idempotent: a double click returns the stored result
        return _answer_out(existing, q)
    if attempt.finished_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This quiz is already finished.")

    concept = db.get(Concept, q.concept_id)
    assert concept is not None
    mastery = db.scalars(select(Mastery).where(Mastery.user_id == user.id, Mastery.concept_id == concept.id)
                         .with_for_update()).first()
    now = clock.now()
    if mastery is None:
        mastery = Mastery(user_id=user.id, concept_id=concept.id, p_known=concept.bkt_prior, n_answers=0, updated_at=now)
        db.add(mastery)
        db.flush()
    is_repeat = db.scalar(select(func.count()).select_from(Response).where(
        Response.user_id == user.id, Response.question_id == question_id)) > 0
    correct = chosen == q.correct_index
    p_before = mastery.p_known
    p_after = bkt_update(p_before, correct, _params(concept))
    r = Response(attempt_id=attempt.id, question_id=q.id, user_id=user.id, concept_id=concept.id, chosen_index=chosen,
                 correct=correct, is_repeat=is_repeat, time_ms=time_ms, p_before=p_before, p_after=p_after,
                 created_at=now)
    try:
        with db.begin_nested():
            db.add(r)
            db.flush()
    except IntegrityError:  # a concurrent duplicate submit won the race
        existing = db.scalar(select(Response).where(Response.attempt_id == attempt.id, Response.question_id == question_id))
        assert existing is not None
        return _answer_out(existing, q)
    mastery.p_known = p_after
    mastery.n_answers += 1
    mastery.updated_at = now
    if p_after >= MASTERED and mastery.mastered_at is None:
        mastery.mastered_at = now
    user.last_active_at = now
    db.flush()
    return _answer_out(r, q)


def finish(db: Session, user: User, attempt_id: int) -> FinishOut:
    attempt = get_attempt(db, user, attempt_id)
    responses = list(db.scalars(select(Response).where(Response.attempt_id == attempt.id).order_by(Response.id)))
    if attempt.finished_at is None:
        attempt.finished_at = clock.now()
        attempt.n_correct = sum(r.correct for r in responses)
        attempt.n_total = len(attempt.question_ids)
    names = {c.id: c.name for c in db.scalars(select(Concept).where(Concept.id.in_({r.concept_id for r in responses} or {0})))}
    first: dict[int, float] = {}
    last: dict[int, float] = {}
    for r in responses:
        first.setdefault(r.concept_id, r.p_before)
        last[r.concept_id] = r.p_after
    changes = [ConceptChange(concept_id=c, name=names.get(c, ""), before=round(first[c], 4), after=round(last[c], 4))
               for c in first]

    gain = None
    passed = None
    if attempt.kind == AttemptKind.check:
        passed = bool(responses) and attempt.n_correct / max(1, attempt.n_total) >= 2 / 3
        use = db.get(AidUse, attempt.use_id) if attempt.use_id else None
        if use is not None and use.check_status != CheckStatus.done:
            fresh = [r.correct for r in responses if not r.is_repeat]
            concept = db.get(Concept, use.concept_id)
            assert concept is not None
            if fresh:
                gain = round(residual_gain(use.p_open, fresh, _params(concept)), 4)
            use.check_status = CheckStatus.done
            use.checked_at = clock.now()
            use.gain = gain
            if use.rec_item_id:
                item = db.get(RecommendationItem, use.rec_item_id)
                if item:
                    item.checked_at, item.gain, item.check_status = use.checked_at, gain, CheckStatus.done
            if gain is not None:
                _update_style(db, user, use, gain)
    db.flush()

    next_list_id = None
    if attempt.kind in (AttemptKind.check, AttemptKind.diagnostic, AttemptKind.pretest):
        if attempt.kind == AttemptKind.pretest:
            from app.services import study as study_svc

            study_svc.assign_arm_after_pretest(db, user, attempt)
        next_list_id = rec_svc.generate(db, user, reason=attempt.kind.value).id
    return FinishOut(attempt_id=attempt.id, kind=attempt.kind, n_correct=attempt.n_correct, n_total=attempt.n_total,
                     changes=changes, gain=gain, passed=passed, next_list_id=next_list_id)


def _update_style(db: Session, user: User, use: AidUse, gain: float) -> None:
    profile = db.get(StyleProfile, user.id)
    if profile is None:
        profile = StyleProfile(user_id=user.id, updated_at=clock.now())
        db.add(profile)
        db.flush()
    aid = db.get(TeachingAid, use.aid_id)
    assert aid is not None
    state = StyleState(
        vector=(profile.ar, profile.si, profile.vv, profile.sg),
        prior=(profile.prior_ar, profile.prior_si, profile.prior_vv, profile.prior_sg),
        n_updates=profile.n_updates, ema_gain=profile.ema_gain,
    )
    new = style_update(state, (aid.style_ar, aid.style_si, aid.style_vv, aid.style_sg), gain,
                       settings_svc.style_config(db))
    db.add(StyleUpdate(user_id=user.id, aid_id=aid.id, item_id=use.rec_item_id, gain=gain, baseline=state.ema_gain,
                       before=list(state.vector), after=list(new.vector), created_at=clock.now()))
    profile.ar, profile.si, profile.vv, profile.sg = new.vector
    profile.n_updates, profile.ema_gain, profile.updated_at = new.n_updates, new.ema_gain, clock.now()


def enrollment_or_none(db: Session, user: User) -> Enrollment | None:
    return learner_svc.enrollment_for(db, user)
