"""从静态食物库同步营养食物数据到 SQLite。"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.food_db import FOOD_DB
from app.models.sports import NutritionFood

logger = logging.getLogger(__name__)


def sync_nutrition_foods(sdb: Session) -> tuple[int, int]:
    """按 FOOD_DB 插入缺失条目并更新已有条目。"""
    by_name = {f.name: f for f in sdb.scalars(select(NutritionFood)).all()}
    added = 0
    updated = 0
    for item in FOOD_DB:
        name = item["name"]
        if name in by_name:
            row = by_name[name]
            row.calories_per_100g = item["calories"]
            row.protein = item["protein"]
            row.fat = item["fat"]
            row.carbs = item["carbs"]
            row.category = item["category"]
            updated += 1
        else:
            sdb.add(
                NutritionFood(
                    name=name,
                    calories_per_100g=item["calories"],
                    protein=item["protein"],
                    fat=item["fat"],
                    carbs=item["carbs"],
                    category=item["category"],
                )
            )
            added += 1
    if added or updated:
        sdb.commit()
    return added, updated
