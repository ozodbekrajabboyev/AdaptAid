from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.base import AidType, Delivery, Interactivity, QuestionPool

StyleNum = Field(ge=-1.0, le=1.0)


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    title: str
    description: str


class ConceptOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    order_index: int
    is_study: bool
    prerequisites: list[int]
    bkt: dict[str, float]
    params_source: str
    n_aids: int


class AidSummary(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    aid_type: AidType
    delivery: Delivery
    source: str
    difficulty: int
    duration_min: int
    concept_id: int
    concept_name: str
    style: list[float]
    interactivity: Interactivity
    default_order: int
    is_active: bool


class AidDetail(AidSummary):
    url: str | None
    body_md: str | None
    component_key: str | None
    n_drill_questions: int


class AidIn(BaseModel):
    slug: str = Field(min_length=3, max_length=96, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=500)
    concept_id: int
    aid_type: AidType
    delivery: Delivery
    url: str | None = None
    body_md: str | None = None
    component_key: Literal["sorting-stepper", "recursion-stack", "bst-builder"] | None = None
    source: str = "AdaptAid"
    difficulty: int = Field(default=2, ge=1, le=5)
    duration_min: int = Field(default=10, ge=1, le=240)
    style_ar: float = StyleNum
    style_si: float = StyleNum
    style_vv: float = StyleNum
    style_sg: float = StyleNum
    interactivity: Interactivity = Interactivity.expositive
    default_order: int = 0

    @field_validator("url")
    @classmethod
    def https_only(cls, v: str | None) -> str | None:
        if v and not v.startswith("https://"):
            raise ValueError("links must start with https://")
        return v

    def check_delivery(self) -> str | None:
        if self.delivery == Delivery.external_url and not self.url:
            return "An external aid needs a link."
        if self.delivery == Delivery.native_md and not (self.body_md or "").strip():
            return "A written aid needs some content."
        if self.delivery == Delivery.interactive_component and not self.component_key:
            return "A built-in interactive aid needs a component."
        return None


class QuestionOut(BaseModel):
    id: int
    key: str
    concept_id: int
    stem: str
    options: list[str]
    correct_index: int
    explanation: str
    difficulty: int
    pool: QuestionPool
    form: str | None
    aid_id: int | None
    is_active: bool


class QuestionIn(BaseModel):
    key: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9-]+$")
    concept_id: int
    stem: str = Field(min_length=5)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=3)
    difficulty: int = Field(default=2, ge=1, le=3)
    pool: QuestionPool = QuestionPool.check
    form: Literal["A", "B"] | None = None
    aid_id: int | None = None


class ImportResult(BaseModel):
    created: int
    updated: int
    errors: list[str]
