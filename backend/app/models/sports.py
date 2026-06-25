from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import SportsBase


class Category(SportsBase):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))


class Movement(SportsBase):
    __tablename__ = "movements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(Enum("beginner", "intermediate", "advanced"), default="beginner")
    video_url: Mapped[Optional[str]] = mapped_column(String(255))
    keypoints_template: Mapped[Optional[dict]] = mapped_column(JSON)
    target_muscles: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NutritionFood(SportsBase):
    __tablename__ = "nutrition_foods"

    # SQLite 需 INTEGER PRIMARY KEY 才能自增；BigInteger 会导致插入失败
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    calories_per_100g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    protein: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    fat: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    carbs: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    category: Mapped[Optional[str]] = mapped_column(String(64), default="其他")
