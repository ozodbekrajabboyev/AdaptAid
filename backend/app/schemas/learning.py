from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.base import AidType, AttemptKind, EventSource, EventType


class RecAid(BaseModel):
    id: int
    title: str
    description: str
    aid_type: AidType
    source: str
    duration_min: int
    difficulty: int


class RecItemOut(BaseModel):
    id: int
    rank: int
    aid: RecAid
    concept_id: int
    concept_name: str
    mastery: float
    match: int | None = Field(description="0-100; hidden in study mode and for the course-plan arm")
    explanation: str
    is_explore: bool
    opened: bool
    completed: bool


class FocusOut(BaseModel):
    concept_id: int
    name: str
    mastery: float
    minutes: int


class RecListOut(BaseModel):
    id: int
    scope: str
    phase: str
    focus: FocusOut | None
    items: list[RecItemOut]
    created_at: datetime
    message: str | None = None


class RefreshIn(BaseModel):
    concept_id: int | None = None


class ImpressionIn(BaseModel):
    list_id: int


class EventIn(BaseModel):
    aid_id: int
    event: EventType
    item_id: int | None = None
    use_id: int | None = None
    source: EventSource = EventSource.direct
    rating: int | None = Field(default=None, ge=1, le=5)
    seconds: int | None = Field(default=None, ge=0, le=3600)


class EventOut(BaseModel):
    use_id: int | None
    p_open: float | None = None


class QuizStartIn(BaseModel):
    kind: AttemptKind
    concept_id: int | None = None
    use_id: int | None = None
    aid_id: int | None = None


class QuizQuestion(BaseModel):
    id: int
    concept_id: int
    concept_name: str
    stem: str
    options: list[str]


class AttemptOut(BaseModel):
    id: int
    kind: AttemptKind
    concept_id: int | None
    questions: list[QuizQuestion]
    answered: dict[int, int]


class AnswerIn(BaseModel):
    question_id: int
    chosen_index: int = Field(ge=0, le=3)
    time_ms: int | None = Field(default=None, ge=0)


class AnswerOut(BaseModel):
    question_id: int
    correct: bool
    correct_index: int
    explanation: str
    concept_id: int
    p_before: float
    p_after: float
    is_repeat: bool


class ConceptChange(BaseModel):
    concept_id: int
    name: str
    before: float
    after: float


class FinishOut(BaseModel):
    attempt_id: int
    kind: AttemptKind
    n_correct: int
    n_total: int
    changes: list[ConceptChange]
    gain: float | None
    passed: bool | None
    next_list_id: int | None


class QuestionnaireItemOut(BaseModel):
    key: str
    prompt: str
    a: str
    b: str


class QuestionnaireOut(BaseModel):
    title: str
    intro: str
    note: str
    items: list[QuestionnaireItemOut]


class QuestionnaireIn(BaseModel):
    answers: dict[str, Literal["a", "b"]]


class IlsIn(BaseModel):
    ar: tuple[int, Literal["active", "reflective"]]
    si: tuple[int, Literal["sensing", "intuitive"]]
    vv: tuple[int, Literal["visual", "verbal"]]
    sg: tuple[int, Literal["sequential", "global"]]


class StyleOut(BaseModel):
    vector: list[float]
    prior: list[float]
    n_updates: int
    dominant: str | None
    labels: list[list[str]]


class OnboardingStatus(BaseModel):
    in_class: bool
    consent_needed: bool
    pretest_needed: bool
    questionnaire_done: bool
    diagnostic_done: bool
    next_step: Literal["join", "consent", "pretest", "questionnaire", "diagnostic", "done"]
