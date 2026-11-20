import pytest

from engine.style import (
    Item,
    StyleState,
    UpdateConfig,
    cosine,
    dominant_pole,
    from_ils_scores,
    score_questionnaire,
    similarity,
    update,
)

ITEMS = [
    Item("q1", "vv", +1),  # a = visual
    Item("q2", "vv", -1),  # a = verbal
    Item("q3", "ar", +1),
    Item("q4", "sg", +1),
]


def test_questionnaire_scoring():
    vec = score_questionnaire({"q1": "a", "q2": "b", "q3": "b", "q4": "a"}, ITEMS)
    # vv: +1 (q1 a) and +1 (q2 b) -> +1; ar: -1; si: no items -> 0; sg: +1
    assert vec == [-1.0, 0.0, 1.0, 1.0]


def test_questionnaire_ignores_missing_answers():
    assert score_questionnaire({"q1": "a"}, ITEMS) == [0.0, 0.0, 1.0, 0.0]


def test_ils_conversion_and_validation():
    vec = from_ils_scores({"ar": (5, "reflective"), "si": (1, "sensing"), "vv": (11, "visual"), "sg": (3, "global")})
    assert vec == pytest.approx([-5 / 11, 1 / 11, 1.0, -3 / 11], abs=1e-4)
    with pytest.raises(ValueError):
        from_ils_scores({"vv": (4, "visual")})
    with pytest.raises(ValueError):
        from_ils_scores({"vv": (5, "auditory")})


def test_similarity_is_neutral_for_zero_vector():
    assert similarity((0, 0, 0, 0), (1, 0, 0, 0)) == 0.5


def test_similarity_is_stable_for_balanced_learners():
    # A tiny vector should not produce a confident match in either direction.
    tiny = (0.03, -0.01, 0.0, 0.0)
    assert 0.4 < similarity(tiny, (1, 0, 0, 0)) < 0.6
    assert 0.4 < similarity(tiny, (-1, 0, 0, 0)) < 0.6


def test_similarity_extremes():
    strong = (0, 0, 0.9, 0)
    assert similarity(strong, (0, 0, 1, 0)) == pytest.approx(1.0)
    assert similarity(strong, (0, 0, -1, 0)) == pytest.approx(0.0)


def test_update_moves_toward_aid_after_good_gain_and_away_after_bad():
    s0 = StyleState(vector=(0, 0, 0, 0), prior=(0, 0, 0, 0))
    visual = (0, 0, 1, 0)
    good = update(s0, visual, gain=0.4)
    assert good.vector[2] > 0
    bad = update(s0, visual, gain=-0.4)
    assert bad.vector[2] < 0
    assert good.n_updates == 1


def test_update_step_is_capped_and_decays():
    cfg = UpdateConfig(lr=5.0, max_step=0.1, prior_pull=0.0)
    s0 = StyleState(vector=(0, 0, 0, 0), prior=(0, 0, 0, 0))
    s1 = update(s0, (1, 1, 1, 1), gain=1.0, cfg=cfg)
    assert max(abs(x) for x in s1.vector) == pytest.approx(0.1)
    # Later updates move less (lr / sqrt(1 + n)) for the same evidence.
    cfg2 = UpdateConfig(lr=0.2, max_step=1.0, prior_pull=0.0)
    early = update(StyleState((0, 0, 0, 0), (0, 0, 0, 0), n_updates=0), (0, 0, 1, 0), 0.5, cfg2)
    late = update(StyleState((0, 0, 0, 0), (0, 0, 0, 0), n_updates=24), (0, 0, 1, 0), 0.5, cfg2)
    assert early.vector[2] > late.vector[2] > 0


def test_update_is_pulled_back_toward_the_prior():
    cfg = UpdateConfig(lr=0.0, prior_pull=0.5)
    s = StyleState(vector=(1, 0, 0, 0), prior=(0, 0, 0, 0))
    assert update(s, (0, 0, 0, 0), gain=0.0, cfg=cfg).vector[0] == pytest.approx(0.5)


def test_dominant_pole():
    assert dominant_pole((0.1, -0.2, 0.7, 0.3)) == ("vv", "visual")
    assert dominant_pole((0.0, -0.6, 0.2, 0.1)) == ("si", "intuitive")
    assert dominant_pole((0.1, 0.1, -0.1, 0.0)) is None


def test_cosine_zero_safe():
    assert cosine((0, 0, 0, 0), (1, 0, 0, 0)) == 0.0
