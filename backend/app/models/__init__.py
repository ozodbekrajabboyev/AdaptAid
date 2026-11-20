"""Import every model so Alembic autogenerate and ``Base.metadata`` see all tables."""

from app.models.content import AidConcept, Concept, ConceptPrerequisite, Course, Question, TeachingAid
from app.models.learning import (
    AidStats,
    Attempt,
    Interaction,
    LearnerFeatures,
    Mastery,
    QuestionnaireResponse,
    RecommendationItem,
    RecommendationList,
    Response,
    StyleProfile,
    StyleUpdate,
)
from app.models.ops import Consent, ModelRun, ResearchReport, Setting, SurveyResponse
from app.models.people import Enrollment, SchoolClass, User

__all__ = [
    "AidConcept",
    "AidStats",
    "Attempt",
    "Concept",
    "ConceptPrerequisite",
    "Consent",
    "Course",
    "Enrollment",
    "Interaction",
    "LearnerFeatures",
    "Mastery",
    "ModelRun",
    "Question",
    "QuestionnaireResponse",
    "RecommendationItem",
    "RecommendationList",
    "ResearchReport",
    "Response",
    "SchoolClass",
    "Setting",
    "StyleProfile",
    "StyleUpdate",
    "SurveyResponse",
    "TeachingAid",
    "User",
]
