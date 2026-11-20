import json
from pathlib import Path

import numpy as np
import pytest

from engine.bkt import MASTERED, BKTParams, fit_brute_force, posterior, predict_correct, trace, update

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "pybkt_reference.json"


def test_update_matches_hand_computation():
    p = BKTParams(prior=0.3, learn=0.2, guess=0.15, slip=0.12)
    # posterior = 0.3*0.88 / (0.3*0.88 + 0.7*0.15) = 0.264 / 0.369
    post = posterior(0.3, True, p)
    assert post == pytest.approx(0.264 / 0.369)
    assert update(0.3, True, p) == pytest.approx(post + (1 - post) * 0.2)
    # a wrong answer: 0.3*0.12 / (0.3*0.12 + 0.7*0.85)
    assert posterior(0.3, False, p) == pytest.approx(0.036 / (0.036 + 0.595))


def test_predictions_match_pybkt_reference():
    """Our one-step-ahead predictions equal pyBKT's for the same parameters and data."""
    ref = json.loads(FIXTURE.read_text())
    params = BKTParams(**ref["params"])
    for user, seq in ref["sequences"].items():
        preds, _ = trace(seq, params)
        assert preds == pytest.approx(ref["correct_predictions"][user], abs=1e-6)


def test_predict_correct_bounds():
    p = BKTParams(guess=0.2, slip=0.1)
    assert predict_correct(0.0, p) == pytest.approx(0.2)
    assert predict_correct(1.0, p) == pytest.approx(0.9)


def test_repeated_correct_answers_reach_mastery():
    p, params = 0.1, BKTParams()
    for _ in range(8):
        p = update(p, True, params)
    assert p >= MASTERED


def _simulate(true: BKTParams, n: int, length: int, seed: int) -> list[list[int]]:
    rng = np.random.default_rng(seed)
    seqs = []
    for _ in range(n):
        known = rng.random() < true.prior
        s = []
        for _ in range(length):
            p_correct = (1 - true.slip) if known else true.guess
            s.append(int(rng.random() < p_correct))
            if not known and rng.random() < true.learn:
                known = True
        seqs.append(s)
    return seqs


def test_brute_force_fit_recovers_parameters():
    true = BKTParams(prior=0.25, learn=0.2, guess=0.2, slip=0.1)
    fit = fit_brute_force(_simulate(true, n=400, length=15, seed=3))
    got = fit.params
    assert got.prior == pytest.approx(true.prior, abs=0.05)
    assert got.learn == pytest.approx(true.learn, abs=0.05)
    assert got.guess == pytest.approx(true.guess, abs=0.05)
    assert got.slip == pytest.approx(true.slip, abs=0.05)
    assert fit.n_sequences == 400
    assert fit.n_answers == 400 * 15


def test_brute_force_respects_bounds():
    # Data where "knowing" looks like answering badly: the bounded fit must not flip.
    fit = fit_brute_force([[0, 0, 0, 0, 1]] * 30 + [[1, 1, 1, 1, 1]] * 30)
    assert fit.params.guess <= 0.3
    assert fit.params.slip <= 0.3


def test_fit_rejects_empty_input():
    with pytest.raises(ValueError):
        fit_brute_force([[], []])
