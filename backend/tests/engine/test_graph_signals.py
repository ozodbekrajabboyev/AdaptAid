import pytest

from engine.bkt import BKTParams, update
from engine.graph import (
    CycleError,
    downstream_counts,
    frontier,
    layers,
    next_concept_adaptive,
    next_concept_static,
    projected_route,
    status,
    topological_order,
    validate_dag,
)
from engine.signals import level_fit, need, percentile_ranks, residual_gain, smoothed_mean, target_difficulty

# 1 -> 2 -> 4, 1 -> 3, 3 -> 5, 4 -> 5   (edges are (concept, prerequisite))
NODES = [1, 2, 3, 4, 5]
EDGES = [(2, 1), (3, 1), (4, 2), (5, 3), (5, 4)]
PRE = {1: set(), 2: {1}, 3: {1}, 4: {2}, 5: {3, 4}}


def test_topological_order_and_cycles():
    order = topological_order(NODES, EDGES)
    assert order.index(1) < order.index(2) < order.index(4) < order.index(5)
    with pytest.raises(CycleError):
        validate_dag([1, 2], [(1, 2), (2, 1)])
    with pytest.raises(ValueError):
        validate_dag([1], [(1, 9)])


def test_layers_and_downstream():
    assert layers(NODES, EDGES) == {1: 0, 2: 1, 3: 1, 4: 2, 5: 3}
    assert downstream_counts(NODES, EDGES) == {1: 4, 2: 2, 3: 1, 4: 1, 5: 0}


def test_frontier_respects_prerequisites():
    mastery = {1: 0.96, 2: 0.5, 3: 0.65}
    assert status(1, mastery, PRE) == "mastered"
    assert status(3, mastery, PRE) == "in_progress"
    assert status(4, mastery, PRE) == "locked"  # prerequisite 2 is below 0.70
    assert frontier(NODES, mastery, PRE) == [2, 3]


def test_adaptive_next_concept_prefers_concepts_that_unlock_more():
    mastery = {1: 0.96, 2: 0.4, 3: 0.4}
    down = downstream_counts(NODES, EDGES)
    order = {c: i for i, c in enumerate(NODES)}
    # same need, but 2 unlocks two concepts and 3 only one
    assert next_concept_adaptive([2, 3], mastery, down, order) == 2
    # a much larger need wins over unlock count
    assert next_concept_adaptive([2, 3], {1: 0.96, 2: 0.9, 3: 0.1}, down, order) == 3


def test_static_next_concept_follows_the_syllabus():
    syllabus = [1, 2, 3, 4, 5]
    assert next_concept_static(syllabus, {}, set(), {}) == 1
    assert next_concept_static(syllabus, {1: 0.97}, set(), {}) == 2
    assert next_concept_static(syllabus, {}, {1}, {}) == 2  # passed a check on 1
    assert next_concept_static(syllabus, {}, set(), {1: 3, 2: 1}) == 2  # used 3 aids on 1
    # after the whole plan: revise the first concept that is still not mastered
    finished = {c: 3 for c in syllabus}
    assert next_concept_static(syllabus, {1: 0.97, 2: 0.5}, set(), finished) == 2
    assert next_concept_static(syllabus, {c: 0.99 for c in syllabus}, set(), finished) is None


def test_projected_route():
    down = downstream_counts(NODES, EDGES)
    route = projected_route(NODES, {1: 0.96}, PRE, down, {c: i for i, c in enumerate(NODES)}, steps=3)
    assert route[0] == 2 and len(route) == 3 and set(route) <= {2, 3, 4}


def test_residual_gain_hand_case():
    params = BKTParams(guess=0.2, slip=0.1)
    # P(correct | p=0.5) = 0.5*0.9 + 0.5*0.2 = 0.55; observed 2/3
    assert residual_gain(0.5, [True, True, False], params) == pytest.approx(2 / 3 - 0.55)


def test_residual_gain_is_not_inflated_by_the_learn_step():
    """Three wrong answers raise the chained BKT estimate (learn step) but the residual is negative."""
    params = BKTParams(prior=0.1, learn=0.15, guess=0.2, slip=0.1)
    p = 0.1
    for _ in range(3):
        p = update(p, False, params)
    assert p > 0.1  # the bias the residual avoids
    assert residual_gain(0.1, [False, False, False], params) < 0


def test_residual_gain_needs_answers():
    with pytest.raises(ValueError):
        residual_gain(0.5, [], BKTParams())


def test_need_level_and_smoothing():
    assert need(0.3) == pytest.approx(0.7)
    assert target_difficulty(0.0) == 1.5 and target_difficulty(1.0) == 5.0
    assert level_fit(target_difficulty(0.5), 0.5) == pytest.approx(1.0)
    assert level_fit(5, 0.0) < level_fit(2, 0.0)
    assert smoothed_mean(1.0, 1, prior_mean=0.0, m=4) == pytest.approx(0.2)


def test_percentile_ranks():
    assert percentile_ranks([None, None]) == [None, None]
    assert percentile_ranks([3.0, None]) == [0.5, None]
    assert percentile_ranks([1.0, 5.0, 3.0]) == [0.0, 1.0, 0.5]
    ties = percentile_ranks([2.0, 2.0, 1.0])
    assert ties[0] == ties[1] == pytest.approx(0.75) and ties[2] == 0.0
