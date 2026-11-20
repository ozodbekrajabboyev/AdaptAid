"""Versioned key/value settings stored in the `settings` table.

Every change bumps the version, and recommendation lists record the weights version they
were generated with, so pilot results can be tied to the exact configuration.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Setting
from engine import clock
from engine.hybrid import DEFAULT_WEIGHTS, PHASE_THRESHOLDS
from engine.style import UpdateConfig

WEIGHTS = "recommender_weights"
STYLE_UPDATE = "style_update"
STUDY = "study"
QUESTIONNAIRE = "questionnaire"
SUS = "sus"

DEFAULTS: dict[str, dict] = {
    WEIGHTS: {"weights": DEFAULT_WEIGHTS, "phase_thresholds": list(PHASE_THRESHOLDS), "source": "blueprint v0"},
    STYLE_UPDATE: {
        "lr": UpdateConfig().lr,
        "max_step": UpdateConfig().max_step,
        "prior_pull": UpdateConfig().prior_pull,
        "ema_alpha": UpdateConfig().ema_alpha,
    },
    STUDY: {
        "active": False,
        "frozen": False,
        "posttest_open": False,
        "consent_version": "1.0",
        "consent_text": (
            "AdaptAid is part of a student research project. If you take part, we record your quiz answers, "
            "which teaching aids you open and your survey answers. Results are reported only as group "
            "statistics with pseudonymous IDs. Taking part is voluntary, does not affect your grades, and you "
            "can stop at any time."
        ),
    },
}


def get(db: Session, key: str) -> tuple[dict[str, Any], int]:
    row = db.get(Setting, key)
    if row is None:
        return DEFAULTS.get(key, {}), 0
    return row.value, row.version


def put(db: Session, key: str, value: dict[str, Any]) -> int:
    row = db.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=value, version=1, updated_at=clock.now())
        db.add(row)
    else:
        row.value = value
        row.version += 1
        row.updated_at = clock.now()
    db.flush()
    return row.version


def ensure_defaults(db: Session) -> None:
    for key, value in DEFAULTS.items():
        if db.get(Setting, key) is None:
            put(db, key, value)


def weights(db: Session) -> tuple[dict[str, dict[str, float]], tuple[int, int], int]:
    value, version = get(db, WEIGHTS)
    thresholds = tuple(value.get("phase_thresholds", PHASE_THRESHOLDS))
    return value.get("weights", DEFAULT_WEIGHTS), thresholds, version  # type: ignore[return-value]


def style_config(db: Session) -> UpdateConfig:
    value, _ = get(db, STYLE_UPDATE)
    return UpdateConfig(**{k: float(v) for k, v in value.items() if k in UpdateConfig.__dataclass_fields__})
