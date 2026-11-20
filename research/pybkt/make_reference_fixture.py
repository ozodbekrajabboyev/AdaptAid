"""Generate backend/tests/fixtures/pybkt_reference.json: pyBKT predictions for fixed parameters.

Run inside the pinned pyBKT venv (see research/pybkt/requirements.txt):
    research/.venv-pybkt/bin/python -I research/pybkt/make_reference_fixture.py backend/tests/fixtures/pybkt_reference.json
"""
import json
import sys

import numpy as np
import pandas as pd
from pyBKT.models import Model


def main():
    params = {"prior": 0.3, "learn": 0.2, "guess": 0.15, "slip": 0.12}
    seqs = {1: [0,0,1,0,1,1,1,0,1,1], 2: [1,1,1,0,1], 3: [0,0,0,0,1,0,0,1,1,1,1]}
    rows = []
    order = 0
    for u, s in seqs.items():
        for c in s:
            rows.append({"user_id": u, "skill_name": "s", "correct": c, "order_id": order})
            order += 1
    df = pd.DataFrame(rows)
    m = Model(seed=0, num_fits=1, parallel=False)
    m.fit(data=df)  # initialise structures, then overwrite params
    # Overwrite the fitted model with fixed parameters, keeping pyBKT's internal layout:
    # As[r] = [[1-learn, forget], [learn, 1-forget]] (column-stochastic), pi_0 = [[1-prior], [prior]].
    fm = m.fit_model["s"]
    learn, guess, slip, prior = params["learn"], params["guess"], params["slip"], params["prior"]
    fm["As"][:] = np.array([[1 - learn, 0.0], [learn, 1.0]])
    fm["pi_0"] = np.array([[1 - prior], [prior]])
    fm["learns"] = np.array([learn])
    fm["forgets"] = np.array([0.0])
    fm["guesses"][:] = guess
    fm["slips"][:] = slip
    fm["prior"] = prior
    pred = m.predict(data=df)
    out = {"params": params, "sequences": {str(u): s for u, s in seqs.items()},
           "correct_predictions": {str(u): pred[pred.user_id == u]["correct_predictions"].round(10).tolist() for u in seqs},
           "state_predictions": {str(u): pred[pred.user_id == u]["state_predictions"].round(10).tolist() for u in seqs}}
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1)
    print("written", {u: out["correct_predictions"][u][:3] for u in out["correct_predictions"]})

if __name__ == "__main__":
    main()
