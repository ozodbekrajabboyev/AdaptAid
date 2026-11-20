from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClassCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    course_id: int


class JoinIn(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    course_id: int
    course_title: str
    teacher_id: int
    teacher_name: str
    join_code: str
    n_students: int
    created_at: datetime
