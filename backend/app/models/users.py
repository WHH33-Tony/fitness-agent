from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import UsersBase


class User(UsersBase):
    __tablename__ = "users"

    # SQLite 只有 INTEGER PRIMARY KEY 才是真正自增 rowid；BigInteger 会导致插入时 id 为 NULL 而报错
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("admin", "user"), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserProfile(UsersBase):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(64))
    height: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    gender: Mapped[str] = mapped_column(Enum("male", "female", "unknown"), default="unknown")
    age: Mapped[Optional[int]] = mapped_column()
    voice_type: Mapped[str] = mapped_column(String(64), default="xiaoyan")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class UserQuestionnaire(UsersBase):
    __tablename__ = "user_questionnaire"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    physique: Mapped[Optional[str]] = mapped_column(String(64))
    fitness_goal: Mapped[Optional[str]] = mapped_column(String(128))
    exercise_level: Mapped[Optional[str]] = mapped_column(String(64))
    injury_history: Mapped[Optional[list]] = mapped_column(JSON)
    avoid_movements: Mapped[Optional[list]] = mapped_column(JSON)
    extra_info: Mapped[Optional[dict]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class TrainingPlan(UsersBase):
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    plan_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DailyExercise(UsersBase):
    __tablename__ = "daily_exercise"
    __table_args__ = (UniqueConstraint("user_id", "exercise_date", name="uk_daily_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_date: Mapped[date] = mapped_column(Date, nullable=False)
    calories_burned: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    exercise_records: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class PoseSession(UsersBase):
    __tablename__ = "pose_sessions"

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    movement_name: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[int] = mapped_column(nullable=False)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON)
    errors: Mapped[Optional[List]] = mapped_column(JSON)
    suggestions: Mapped[Optional[List]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MCPTool(UsersBase):
    __tablename__ = "mcp_tools"

    tool_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    call_count: Mapped[int] = mapped_column(BigInteger, default=0)
    avg_latency_ms: Mapped[Optional[int]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AgentSession(UsersBase):
    __tablename__ = "agent_sessions"

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    intent: Mapped[Optional[str]] = mapped_column(String(64))
    tool_calls: Mapped[Optional[List]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class ToolCall(UsersBase):
    __tablename__ = "tool_calls"

    call_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agent_sessions.session_id"))
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    params: Mapped[Optional[dict]] = mapped_column(JSON)
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(Enum("success", "fail", "timeout"), nullable=False)
    latency_ms: Mapped[Optional[int]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class QARecord(UsersBase):
    __tablename__ = "qa_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[Optional[List]] = mapped_column(JSON)
    intent: Mapped[Optional[str]] = mapped_column(String(64))
    agent_session_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agent_sessions.session_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Feedback(UsersBase):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "replied", "closed"),
        default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class FeedbackMessage(UsersBase):
    __tablename__ = "feedback_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feedback_id: Mapped[int] = mapped_column(Integer, ForeignKey("feedbacks.id"), nullable=False, index=True)
    sender_type: Mapped[str] = mapped_column(Enum("user", "admin"), nullable=False)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
