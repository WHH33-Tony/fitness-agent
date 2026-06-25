from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["admin", "user"]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class RegisterIn(BaseModel):
    phone: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6)
    role: Role = "user"


class LoginIn(BaseModel):
    phone: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    role: Role
    is_active: bool
    created_at: datetime | None = None


class ProfileIn(BaseModel):
    nickname: str | None = None
    height: float | None = None
    weight: float | None = None
    gender: Literal["male", "female", "unknown"] = "unknown"
    age: int | None = None
    voice_type: str = "xiaoyan"


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    user_id: int


class QuestionnaireIn(BaseModel):
    physique: str | None = None
    fitness_goal: str | None = None
    exercise_level: str | None = None
    injury_history: list[str] = []
    avoid_movements: list[str] = []
    extra_info: dict[str, Any] = {}


class TrainingPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    plan_data: dict[str, Any]
    generated_at: datetime | None = None


class DailyExerciseIn(BaseModel):
    exercise_date: date
    calories_burned: float = 0
    exercise_records: dict[str, Any] = {}


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    name: str
    description: str | None = None
    difficulty: str
    video_url: str | None = None
    keypoints_template: dict[str, Any] | None = None
    target_muscles: str | None = None


class QARequest(BaseModel):
    question: str
    voice_type: str = "xiaoyan"


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice_type: str | None = None


class TTSResponse(BaseModel):
    audio_url: str | None = None
    audio_base64: str | None = None
    voice_type: str
    vcn: str | None = None


class QAResponse(BaseModel):
    question: str
    answer: str
    audio_url: str | None = None
    sources: list[str] = []
    intent: str | None = None
    meal_plan: dict | None = None
    weather: dict | None = None
    answer_mode: str | None = None


class PoseFrameIn(BaseModel):
    movement_name: str = "徒手深蹲"
    landmarks: list[dict[str, float]]
    # 可选：前端汇总指标（用于桌面端"结束一次识别就落库"）
    summary_metrics: dict | None = None
    average_score: int | float | None = None


class CreateFeedbackIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ReplyFeedbackIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FeedbackMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    feedback_id: int
    sender_type: str
    sender_id: int
    content: str
    created_at: datetime | None = None


class FeedbackDetailOut(BaseModel):
    feedback: FeedbackOut
    messages: list[FeedbackMessageOut]


class FeedbackListOut(BaseModel):
    id: int
    user_phone: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
