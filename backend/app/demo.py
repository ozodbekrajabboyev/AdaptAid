"""Demo data: a simulated four-week semester driven through the real services.

`adaptaid seed-demo` creates a demo class of synthetic students (users.is_synthetic = true)
and replays four weeks of activity on an injected clock: onboarding, the diagnostic,
recommendations, opening aids, ratings and quick checks all go through the same service
code the API uses, and the background jobs run once a simulated week. Hidden learner
truth (what each student really knows and which formats really help them) comes from
engine/simulator.py.

It also creates three demo accounts for the viva:
    admin@adaptaid.demo, teacher@adaptaid.demo, student@adaptaid.demo ("hero" student)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import AidStats, Concept, Enrollment, ModelRun, Question, SchoolClass, User
from app.models.base import AttemptKind, EventSource, EventType, Role
from app.schemas.learning import EventIn
from app.services import content as content_svc
from app.services import events as events_svc
from app.services import learner as learner_svc
from app.services import onboarding as onboarding_svc
from app.services import quiz as quiz_svc
from app.services import recommend as rec_svc
from app.services import settings as settings_svc
from engine import clock
from engine.simulator import LEARNER_TYPES, SimLearner, WorldConfig, make_learners, p_learn

log = logging.getLogger("adaptaid.demo")
DOMAIN = "adaptaid.demo"
CLASS_CODE = "DEMO26"
FIRST = ["Aarav", "Diya", "Ishaan", "Meera", "Rohan", "Sana", "Tanvi", "Vivek", "Ananya", "Kabir", "Priya", "Arjun",
         "Neha", "Rahul", "Zoya", "Aditya", "Kavya", "Nikhil", "Ira", "Siddharth", "Riya", "Varun", "Aisha", "Dev",
         "Pooja", "Yash", "Nandini", "Karan", "Shreya", "Farhan", "Tara", "Manav", "Leela", "Omar", "Anika", "Rehan",
         "Simran", "Aryan", "Maya", "Kunal"]
LAST = ["Sharma", "Kapoor", "Patel", "Reddy", "Mehta", "Ansari", "Gupta", "Nair", "Iyer", "Singh", "Das", "Khan",
        "Joshi", "Bose", "Menon", "Verma", "Malhotra", "Chopra", "Rao", "Saxena"]


class DemoExists(RuntimeError):
    pass


def _user(db: Session, email: str, name: str, role: Role, password: str, synthetic: bool = False) -> User:
    u = User(email=email, full_name=name, role=role, password_hash=hash_password(password), is_synthetic=synthetic,
             created_at=clock.now(), last_active_at=None)
    db.add(u)
    db.flush()
    return u


def _answers_for(pref: np.ndarray, items: list[dict], rng: np.random.Generator) -> dict[str, str]:
    dims = {"ar": 0, "si": 1, "vv": 2, "sg": 3}
    out = {}
    for it in items:
        lean = pref[dims[it["dim"]]] * int(it["a_pole"]) + rng.normal(0, 0.45)
        out[it["key"]] = "a" if lean > 0 else "b"
    return out


class Session_:
    """One synthetic learner's behaviour inside the real platform."""

    def __init__(self, db: Session, sim: SimLearner, user: User, cfg: WorldConfig, rng: np.random.Generator,
                 question_concept: dict[int, int], catalogue_fn: Callable, hard: set[int] | None = None):
        self.db, self.sim, self.user, self.cfg, self.rng = db, sim, user, cfg, rng
        self.qc = question_concept
        self.catalogue_fn = catalogue_fn
        self.hard = hard or set()  # concepts this learner keeps getting wrong (the hero's recursion)

    def answer_question(self, qid: int, correct_index: int) -> int:
        concept = self.qc[qid]
        knows = self.sim.known.get(concept, False)
        p = 1 - self.cfg.slip if knows else self.cfg.guess
        if concept in self.hard:
            p = 0.12
        if self.rng.random() < p:
            return correct_index
        return int((correct_index + 1 + self.rng.integers(0, 3)) % 4)

    def run_quiz(self, attempt) -> None:
        for q in attempt.questions:
            ci = self.db.get(Question, q.id).correct_index
            quiz_svc.answer(self.db, self.user, attempt.id, q.id, self.answer_question(q.id, ci),
                            int(self.rng.integers(6000, 40000)))
            c = self.qc[q.id]
            if not self.sim.known.get(c, False) and self.rng.random() < self.cfg.check_learn:
                self.sim.known[c] = True
        quiz_svc.finish(self.db, self.user, attempt.id)

    def onboard(self, items: list[dict]) -> None:
        onboarding_svc.submit_questionnaire(self.db, self.user, _answers_for(self.sim.pref, items, self.rng))
        self.run_quiz(quiz_svc.start(self.db, self.user, AttemptKind.diagnostic))

    def study_session(self, blocked: set[int] | None = None) -> bool:
        db, user, rng = self.db, self.user, self.rng
        lst = rec_svc.current(db, user)
        out = rec_svc.to_out(db, user, lst)
        if not out.items:
            return False
        rec_svc.mark_impression(db, user, lst.id)
        bias = np.array(self.cfg.position_bias[: len(out.items)])
        item = out.items[int(rng.choice(len(out.items), p=bias / bias.sum()))]
        ev = events_svc.record(db, user, EventIn(aid_id=item.aid.id, event=EventType.open, item_id=item.id,
                                                 source=EventSource.rec))
        cat = self.catalogue_fn()
        aid = cat.aids.get(item.aid.id)
        concept = item.concept_id
        learnable = aid is not None and not self.sim.known.get(concept, False) and concept not in (blocked or set())
        if learnable and rng.random() < p_learn(self.sim, aid, cat, self.cfg):
            self.sim.known[concept] = True
        seconds = int(item.aid.duration_min * 60 * rng.uniform(0.3, 1.2))
        events_svc.record(db, user, EventIn(aid_id=item.aid.id, event=EventType.heartbeat, use_id=ev.use_id,
                                            seconds=min(seconds, 3600)))
        if rng.random() < 0.8:
            events_svc.record(db, user, EventIn(aid_id=item.aid.id, event=EventType.complete, use_id=ev.use_id))
        if rng.random() < 0.6 and aid is not None:
            match = float(np.dot(aid.style, self.sim.pref) / (np.linalg.norm(aid.style) * np.linalg.norm(self.sim.pref) + 1e-9))
            rating = int(np.clip(round(3 + 1.5 * match + rng.normal(0, 0.7)), 1, 5))
            events_svc.record(db, user, EventIn(aid_id=item.aid.id, event=EventType.rate, use_id=ev.use_id, rating=rating))
        if rng.random() < 0.85:
            self.run_quiz(quiz_svc.start(db, user, AttemptKind.check, use_id=ev.use_id))
        return True


def demo_exists(db: Session) -> bool:
    return db.scalar(select(User.id).where(User.email == f"teacher@{DOMAIN}")) is not None


def reset_demo(db: Session) -> int:
    """Delete demo accounts, synthetic students, the demo class, model runs and aid statistics."""
    users = list(db.scalars(select(User).where((User.email.like(f"%@{DOMAIN}")) | User.is_synthetic)))
    for u in users:
        db.delete(u)
    db.execute(delete(ModelRun))
    db.execute(delete(AidStats))
    db.commit()
    return len(users)


def seed_demo(n_students: int = 60, days: int = 28, seed: int = 2026, password: str = "demo-pass-2026",
              progress: Callable[[str], None] = print) -> dict:
    from app.jobs.runner import run_all

    rng = np.random.default_rng(seed)
    real_now = clock.now()
    start = (real_now - timedelta(days=days)).replace(hour=3, minute=30, second=0, microsecond=0)
    sim_clock = clock.ManualClock(start)

    with clock.use_clock(sim_clock), SessionLocal() as db:
        if demo_exists(db):
            raise DemoExists("Demo data already exists. Run `adaptaid reset-demo` first.")
        course = content_svc.default_course(db)
        settings_svc.ensure_defaults(db)
        cat = learner_svc.load_catalogue(db, course.id)
        qc = {q.id: q.concept_id for q in db.scalars(select(Question))}
        items = settings_svc.get(db, settings_svc.QUESTIONNAIRE)[0]["items"]

        admin = _user(db, f"admin@{DOMAIN}", "Asha Admin", Role.admin, password)
        teacher = _user(db, f"teacher@{DOMAIN}", "Prof. Meenakshi Rao", Role.teacher, password)
        klass = SchoolClass(course_id=course.id, teacher_id=teacher.id, name="Demo CSE-3A", join_code=CLASS_CODE,
                            created_at=clock.now())
        db.add(klass)
        db.flush()

        cfg = WorldConfig(affinity_effect=0.6)
        sims = make_learners(n_students, cat, cfg, rng)
        actors: list[Session_] = []
        used_names: set[str] = set()
        for i, sim in enumerate(sims):
            while True:
                name = f"{FIRST[int(rng.integers(len(FIRST)))]} {LAST[int(rng.integers(len(LAST)))]}"
                if name not in used_names:
                    used_names.add(name)
                    break
            u = _user(db, f"student{i + 1:02d}@{DOMAIN}", name, Role.student, password, synthetic=True)
            db.add(Enrollment(class_id=klass.id, user_id=u.id, joined_at=clock.now()))
            actors.append(Session_(db, sim, u, cfg, rng, qc, lambda: learner_svc.load_catalogue(db, course.id)))

        # The hero: a visual learner who has nearly finished the linear structures and is stuck on recursion.
        hero_sim = make_learners(1, cat, cfg, np.random.default_rng(seed + 1), mix={"visual_explorer": 1.0})[0]
        hero_sim.engagement, hero_sim.decay = 1.0, 0.0
        slugs = {c.id: c.slug for c in db.scalars(select(Concept).where(Concept.course_id == course.id))}
        recursion = next((cid for cid, s in slugs.items() if s == "recursion"), None)
        for cid, s in slugs.items():
            hero_sim.known[cid] = s in ("complexity", "arrays", "linked-lists", "stacks")
        hero = _user(db, f"student@{DOMAIN}", "Diya Kapoor", Role.student, password)
        db.add(Enrollment(class_id=klass.id, user_id=hero.id, joined_at=clock.now()))
        hero_actor = Session_(db, hero_sim, hero, cfg, rng, qc, lambda: learner_svc.load_catalogue(db, course.id),
                              hard={recursion} if recursion else None)
        db.commit()

        everyone = [*actors, hero_actor]
        onboard_day = {id(a): int(rng.integers(0, 3)) for a in actors}
        onboard_day[id(hero_actor)] = 0
        onboarded: set[int] = set()
        sessions = 0
        for day in range(days):
            order = list(everyone)
            rng.shuffle(order)
            for actor in order:
                at = start + timedelta(days=day, hours=float(rng.uniform(5.5, 17.5)))  # 09:00-23:00 IST
                sim_clock.set(at)
                if id(actor) not in onboarded:
                    if day >= onboard_day[id(actor)]:
                        actor.onboard(items)
                        onboarded.add(id(actor))
                        db.commit()
                    continue
                engagement = actor.sim.engagement * (1 - actor.sim.decay) ** day
                if actor is not hero_actor and LEARNER_TYPES[actor.sim.kind].get("decay") and day > 18:
                    engagement *= 0.15  # dropouts go quiet in the last ten days
                if rng.random() > engagement:
                    continue
                n = 2 if actor is hero_actor else int(rng.integers(1, 4))
                for s in range(n):
                    sim_clock.set(at + timedelta(minutes=25 * s))
                    blocked = {recursion} if actor is hero_actor and recursion else None
                    if actor.study_session(blocked=blocked):
                        sessions += 1
                db.commit()
            if day % 7 == 6 or day == days - 1:
                sim_clock.set(start + timedelta(days=day, hours=20, minutes=30))  # 02:00 IST next night
                db.commit()
                run_all(triggered_by="demo", force=True)
                learner_svc._catalogue_cache.clear()
                progress(f"  day {day + 1}/{days}: {sessions} sessions so far, jobs run")

        # Steer the hero's recursion mastery into the 30-60% band with real quick-check answers.
        sim_clock.set(real_now - timedelta(hours=2))
        if recursion is not None:
            _steer(db, hero, recursion, low=0.30, high=0.60)
        rec_svc.generate(db, hero, "demo")
        db.commit()

    with SessionLocal() as db:
        n_syn = len(db.scalars(select(User.id).where(User.is_synthetic)).all())
    return {"students": n_syn, "sessions": sessions, "class_code": CLASS_CODE, "password": password,
            "accounts": [f"admin@{DOMAIN}", f"teacher@{DOMAIN}", f"student@{DOMAIN}"], "admin_id": admin.id}


def _steer(db: Session, user: User, concept_id: int, low: float, high: float) -> None:
    from app.models import Mastery

    for _ in range(6):
        m = db.scalar(select(Mastery).where(Mastery.user_id == user.id, Mastery.concept_id == concept_id))
        p = m.p_known if m else 0.0
        if low <= p <= high:
            return
        attempt = quiz_svc.start(db, user, AttemptKind.check, concept_id=concept_id)
        q = attempt.questions[0]
        ci = db.get(Question, q.id).correct_index
        quiz_svc.answer(db, user, attempt.id, q.id, ci if p < low else (ci + 1) % 4, 15000)
        quiz_svc.finish(db, user, attempt.id)
        db.commit()
