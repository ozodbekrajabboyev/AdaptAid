"""The pre-specified pilot analysis finds a planted effect and does not invent one."""

import warnings

from research.src.pilot_analysis import analyse, self_test, simulate_pilot


def test_planted_effect_detected_and_null_not():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = self_test()
    assert res["ok"], res


def test_too_few_participants_is_reported():
    small = simulate_pilot(n_per_arm=2, effect=0.2)
    assert "error" in analyse(small)


def test_normalized_gain_and_sus_by_arm():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = analyse(simulate_pilot(n_per_arm=12, effect=0.1, seed=3), n_boot=200)
    assert set(res["secondary"]["mean_g"]) == {"adaptive", "control"}
    assert res["by_arm"]["adaptive"]["sus"] is not None
