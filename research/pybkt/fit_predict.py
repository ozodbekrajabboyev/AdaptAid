"""Fit pyBKT on a training CSV and write one-step-ahead predictions for a test CSV.

Runs in the pinned pyBKT venv (research/.venv-pybkt), called by research/src/bkt_eval.py:
    research/.venv-pybkt/bin/python -I research/pybkt/fit_predict.py train.csv test.csv out.csv
CSV columns: order_id, user_id, skill_name, correct.
"""

import sys

import pandas as pd
from pyBKT.models import Model


def main() -> None:
    train_path, test_path, out_path = sys.argv[1:4]
    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    model = Model(seed=42, num_fits=3, parallel=True)
    model.fit(data=train)
    pred = model.predict(data=test)
    pred[["order_id", "correct_predictions"]].to_csv(out_path, index=False)


if __name__ == "__main__":
    main()
