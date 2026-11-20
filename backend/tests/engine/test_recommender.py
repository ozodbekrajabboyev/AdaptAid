import numpy as np
import pytest

from engine import cf
from engine.explain import CONTROL_REASON, ExplainContext, PeerStat, contributions, explain
from engine.group import StudentView, class_suggestions
from engine.hybrid import DEFAULT_WEIGHTS, phase_for, score_candidates
from engine.policy import AdaptivePolicy, RandomPolicy, StaticPolicy, ablation
from engine.profiling import personas, risk
from engine.rerank import mmr, with_explore_slot
from engine.simulator import WorldConfig, demo_catalogue, run
from engine.types import AidInfo, Catalogue, LearnerView, Scored

VISUAL = (0.2, 0.0, 0.9, 0.3)
VERBAL = (-0.4, 0.0, -0.8, 0.5)
PRACTICE = (0.9, 0.6, 0.0, 0.3)


def aid(i, t="video", style=VISUAL, d=2, c=1, order=0):
    return AidInfo(i, c, t, style, d, default_order=order, title=f"aid {i}")


# ------------------------------------------------------------------ hybrid


def test_phase_thresholds():
    assert [phase_for(n) for n in (0, 4, 5, 29, 30)] == ["cold", "cold", "warm", "warm", "established"]


def test_missing_cf_is_not_penalised():
    a, b = aid(1), aid(2)
    learner = LearnerView(mastery={1: 0.3}, style=VISUAL, cf_scores={2: 0.01, 3: 5.0}, help_scores={})
    w = {"need": 0.3, "style": 0.3, "level": 0.2, "cf": 0.2, "help": 0.0}
    out = score_candidates([(a, 1), (b, 1), (aid(3), 1)], learner, w)
    by_id = {s.aid.id: s for s in out}
    assert by_id[1].parts["cf"] is None
    # b has the lowest CF percentile (0), a has no CF: a must not score below b.
    assert by_id[1].score > by_id[2].score


def test_cf_scale_does_not_matter():
    cands = [(aid(i), 1) for i in range(1, 5)]
    raw = {1: 0.1, 2: 0.4, 3: 0.2, 4: 0.3}
    w = DEFAULT_WEIGHTS["established"]
    a = score_candidates(cands, LearnerView({1: 0.4}, VISUAL, cf_scores=raw), w)
    b = score_candidates(cands, LearnerView({1: 0.4}, VISUAL, cf_scores={k: v * 1000 for k, v in raw.items()}), w)
    assert [s.aid.id for s in a] == [s.aid.id for s in b]


def test_style_signal_ranks_matching_format_first():
    cands = [(aid(1, "notes", VERBAL), 1), (aid(2, "animation", VISUAL), 1)]
    out = score_candidates(cands, LearnerView({1: 0.3}, style=(0, 0, 0.8, 0)), DEFAULT_WEIGHTS["cold"])
    assert out[0].aid.id == 2


# ------------------------------------------------------------------ rerank


def _scored(i, t, score, style=VISUAL):
    return Scored(aid=aid(i, t, style), concept_id=1, parts={}, score=score)


def test_mmr_adds_format_variety():
    pool = [_scored(1, "video", 0.9), _scored(2, "video", 0.89), _scored(3, "video", 0.88), _scored(4, "notes", 0.8, VERBAL)]
    picked = mmr(pool, 2)
    assert {p.aid.aid_type for p in picked} == {"video", "notes"}


def test_explore_slot_uses_least_used_format():
    pool = [_scored(1, "video", 0.9), _scored(2, "notes", 0.8), _scored(3, "practice", 0.5), _scored(4, "article", 0.4)]
    picked = mmr(pool, 3)
    out = with_explore_slot(picked, pool, {"video": 5, "notes": 3, "practice": 2, "article": 0}, 3)
    assert len(out) == 3
    assert out[-1].aid.aid_type == "article" and out[-1].is_explore


def test_no_explore_slot_for_tiny_lists():
    pool = [_scored(1, "video", 0.9), _scored(2, "notes", 0.8)]
    assert not any(s.is_explore for s in with_explore_slot(mmr(pool, 2), pool, {}, 2))


# ------------------------------------------------------------------ explain


def test_explanations_differ_between_cards_and_use_peers():
    w = DEFAULT_WEIGHTS["warm"]
    items = [
        Scored(aid(1, "animation", VISUAL), 1, {"need": 0.6, "style": 0.95, "level": 0.5, "cf": 0.5, "help": 0.5}, 0.7),
        Scored(aid(2, "worked_example", PRACTICE), 1, {"need": 0.6, "style": 0.5, "level": 0.98, "cf": 0.5, "help": 0.5}, 0.65),
    ]
    contrib = contributions(items, w)
    ctx = ExplainContext({1: "Recursion"}, {1: 0.42}, dominant_pole="visual", peers={1: PeerStat(40, 31), 2: PeerStat(3, 2)})
    t1, t2 = explain(items[0], contrib[0], ctx), explain(items[1], contrib[1], ctx)
    assert t1.startswith("You're at 42% on Recursion.")
    assert "visual material" in t1 and "31 of 40 similar students" in t1
    assert "just above your current level" in t2 and "similar students" not in t2  # n < 5


def test_explore_and_reoffer_and_control_texts():
    ctx = ExplainContext({1: "Hashing"}, {1: 0.3})
    s = Scored(aid(1, "practice"), 1, {}, 0.5, is_explore=True)
    assert "tries a different format" in explain(s, {}, ctx)
    r = Scored(aid(2, "notes"), 1, {}, 0.5, reoffer=True)
    assert "used every aid for Hashing" in explain(r, {}, ctx)
    assert CONTROL_REASON == "Next in the course plan."


# ------------------------------------------------------------------ CF


def _cf_rows():
    rows = []
    for u in range(10):  # A and B co-occur
        rows += [(u, 1, 0.5), (u, 2, 0.4)]
    for u in range(10, 20):  # C and D co-occur
        rows += [(u, 3, 0.5), (u, 4, 0.4)]
    return rows


def test_itemknn_scores_co_used_aids_higher():
    model = cf.train(_cf_rows())
    assert model is not None and model.kind == "itemknn"
    s = model.score({1: 0.6}, [2, 3, 4])
    assert s[2] > s[3] and s[2] > s[4]


def test_als_works_for_unseen_learners_and_round_trips():
    rng = np.random.default_rng(0)
    rows = _cf_rows() + [(int(u), int(i), float(rng.random())) for u, i in rng.integers(20, 60, (40, 2))]
    model = cf.train(rows, als_threshold=1, factors=4, iterations=10)
    assert model is not None and model.kind == "als"
    s = model.score({1: 0.6}, [2, 3])  # a learner the model never saw
    assert all(np.isfinite(v) for v in s.values())
    again = cf.loads(cf.dumps(model))
    assert again.score({1: 0.6}, [2, 3]) == pytest.approx(s)


def test_cf_needs_data():
    assert cf.train([]) is None
    assert cf.train([(1, 1, 0.0)]) is None
    assert cf.train(_cf_rows()).score({}, [1, 2]) == {}


# ------------------------------------------------------------------ group


def _group_cat():
    aids = {
        1: AidInfo(1, 1, "animation", VISUAL, 2),
        2: AidInfo(2, 1, "notes", VERBAL, 2),
        3: AidInfo(3, 1, "practice", PRACTICE, 2),
    }
    return Catalogue(syllabus=[1, 2], prereqs={1: set(), 2: {1}}, aids=aids, names={1: "Recursion", 2: "Trees"})


def _class(n_visual, n_verbal):
    s = [StudentView(i, f"S{i}", {1: 0.3, 2: 0.0}, (0.1, 0.0, 0.8, 0.2)) for i in range(n_visual)]
    return s + [StudentView(100 + i, f"R{i}", {1: 0.3, 2: 0.0}, (-0.3, 0.0, -0.8, 0.3)) for i in range(n_verbal)]


def test_class_suggestions_average_without_misery():
    out = class_suggestions(_class(8, 2), _group_cat(), aid_gain={1: 0.2, 2: 0.1, 3: 0.0})
    rec = next(c for c in out if c.concept_id == 1)
    assert rec.share_below == 1.0 and rec.class_lean == "visual"
    assert rec.aids[0].aid.aid_type == "animation"
    assert "notes" not in {a.aid.aid_type for a in rec.aids}  # poor fit for 80% of the class
    assert all(a.share_poor_fit <= 0.25 for a in rec.aids)
    alt_ids = {sid for g in rec.alternatives for sid, _ in g.students}
    assert alt_ids == {100, 101}


def test_divided_class_falls_back_to_least_misery():
    out = class_suggestions(_class(7, 3), _group_cat(), aid_gain={1: 0.2, 2: 0.1, 3: 0.0})
    rec = next(c for c in out if c.concept_id == 1)
    assert rec.aids, "a divided class still gets a suggestion"
    assert rec.aids[0].aid.aid_type == "animation"
    assert rec.alternatives


# ------------------------------------------------------------------ profiling


def test_personas_find_separated_groups():
    rng = np.random.default_rng(1)
    rows = []
    for centre in ({"share_visual": 0.9, "aid_uses": 30}, {"share_practice": 0.9, "aid_uses": 25}, {"days_since_active": 14, "aid_uses": 2}):
        for _ in range(15):
            r = {k: 0.0 for k in ("active_days", "aid_uses", "completion_rate", "check_accuracy", "mean_mastery",
                                  "mastery_slope", "days_since_active", "share_visual", "share_practice", "share_text")}
            r.update({k: v + rng.normal(0, 0.05) for k, v in centre.items()})
            rows.append(r)
    res = personas(rows)
    assert res is not None and res.k >= 2 and res.silhouette > 0.3 and len(res.labels) == 45
    assert res.stability_ari > 0.8
    assert personas(rows[:5]) is None


def test_risk_rules_give_reasons():
    r = risk({"days_since_active": 9, "n_checked": 6, "mean_gain": -0.2, "mastery_slope": 0.0})
    assert r.level == "high"
    assert "Inactive for 9 days" in r.reasons and any("below expectation" in x for x in r.reasons)
    # Low raw accuracy alone is normal (checks follow unfamiliar material): not flagged.
    assert risk({"days_since_active": 1, "check_accuracy": 0.35, "n_answers": 12, "n_checked": 4, "mean_gain": 0.02}).level == "low"
    assert risk({"days_since_active": 1, "check_accuracy": 0.15, "n_answers": 12}).reasons == ["Most quick-check answers wrong (15% correct)"]


# ------------------------------------------------------------------ policies + simulator


def test_adaptive_policy_list():
    cat = demo_catalogue()
    learner = LearnerView(mastery={c: 0.1 for c in cat.syllabus}, style=VISUAL)
    rec = AdaptivePolicy().recommend(learner, cat, k=5)
    assert rec.phase == "cold" and len(rec.items) == 5
    assert sum(s.is_explore for s in rec.items) == 1
    assert {s.concept_id for s in rec.items} == {1}  # only concept 1 is unlocked
    assert rec.focus_concept == 1


def test_recent_aids_are_skipped_and_reoffered_when_exhausted():
    cat = demo_catalogue(aids_per_concept=3)
    used = {a.id for a in cat.aids_by_concept[1]}
    learner = LearnerView(mastery={1: 0.4}, recent_aids=used, best_gain_aid={1: min(used) + 1})
    rec = AdaptivePolicy().recommend(learner, cat, k=5, concept=1)
    assert len(rec.items) == 1 and rec.items[0].reoffer and rec.items[0].aid.id == min(used) + 1


def test_static_policy_follows_course_plan():
    cat = demo_catalogue()
    pol = StaticPolicy()
    learner = LearnerView(mastery={c: 0.1 for c in cat.syllabus})
    rec = pol.recommend(learner, cat, k=5)
    assert rec.focus_concept == 1
    assert [s.aid.default_order for s in rec.items] == sorted(s.aid.default_order for s in rec.items)
    assert all(s.parts == {} for s in rec.items)
    learner.passed_check.add(1)
    assert pol.recommend(learner, cat).focus_concept == 2


def test_ablation_presets():
    assert ablation("no_style").enabled == ("need", "level", "cf", "help")
    assert ablation("style_only").weights["cold"]["style"] == 1.0
    assert RandomPolicy(seed=1).recommend(LearnerView({c: 0.0 for c in range(1, 9)}), demo_catalogue(), k=3).items


def test_simulator_is_deterministic_and_learners_learn():
    cat = demo_catalogue()
    cfg = WorldConfig()
    a = run(AdaptivePolicy, cat, n_learners=20, steps=12, cfg=cfg, seed=5)
    b = run(AdaptivePolicy, cat, n_learners=20, steps=12, cfg=cfg, seed=5)
    assert a.known_curve == b.known_curve and a.style_curve == b.style_curve
    assert a.known_curve[-1] > a.known_curve[0]
    c = run(AdaptivePolicy, cat, n_learners=20, steps=12, cfg=cfg, seed=6)
    assert c.known_curve != a.known_curve
