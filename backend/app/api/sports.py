import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from sqlalchemy import select

from app.api.deps import CurrentUser, RedisDep, SportsDb, UsersDb
from app.models.sports import Category, Movement, NutritionFood
from app.models.users import DailyExercise
from app.schemas import CategoryOut, DailyExerciseIn, MovementOut

router = APIRouter(prefix="/sports", tags=["动作与运动数据"])

_BEIJING_TZ = timezone(timedelta(hours=8))


def _beijing_today() -> date:
    return datetime.now(_BEIJING_TZ).date()


def _loads_redis_json(value: object) -> list[dict]:
    if isinstance(value, (str, bytes, bytearray)):
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []
    return []


@router.get("/categories", response_model=list[CategoryOut])
def categories(db: SportsDb, redis: RedisDep) -> list[dict]:
    cache_key = "sports:categories"
    cached = redis.get(cache_key)
    if cached:
        return _loads_redis_json(cached)
    data = [{"id": item.id, "name": item.name, "description": item.description} for item in db.scalars(select(Category)).all()]
    redis.setex(cache_key, 3600, json.dumps(data, ensure_ascii=False))
    return data


@router.get("/movements", response_model=list[MovementOut])
def movements(db: SportsDb, redis: RedisDep, category_id: Optional[int] = None) -> list[dict]:
    cache_key = f"sports:movements:{category_id or 'all'}"
    cached = redis.get(cache_key)
    if cached:
        return _loads_redis_json(cached)
    stmt = select(Movement)
    if category_id:
        stmt = stmt.where(Movement.category_id == category_id)
    rows = db.scalars(stmt.order_by(Movement.id)).all()
    data = [
        {
            "id": item.id,
            "category_id": item.category_id,
            "name": item.name,
            "description": item.description,
            "difficulty": item.difficulty,
            "video_url": item.video_url,
            "keypoints_template": item.keypoints_template,
            "target_muscles": item.target_muscles,
        }
        for item in rows
    ]
    redis.setex(cache_key, 3600, json.dumps(data, ensure_ascii=False))
    return data


@router.get("/nutrition")
def nutrition_foods(db: SportsDb, category: Optional[str] = Query(None)) -> list[dict]:
    stmt = select(NutritionFood)
    if category:
        stmt = stmt.where(NutritionFood.category == category)
    return [
        {
            "id": food.id,
            "name": food.name,
            "calories_per_100g": float(food.calories_per_100g),
            "protein": float(food.protein),
            "fat": float(food.fat),
            "carbs": float(food.carbs),
            "category": food.category or "其他",
        }
        for food in db.scalars(stmt.order_by(NutritionFood.name)).all()
    ]


@router.get("/nutrition/categories")
def nutrition_categories(db: SportsDb) -> list[str]:
    rows = db.execute(select(NutritionFood.category).distinct().order_by(NutritionFood.category)).all()
    cats = [r[0] for r in rows if r and r[0]]
    return cats or ["其他"]


@router.post("/daily")
def save_daily_exercise(payload: DailyExerciseIn, current_user: CurrentUser, db: UsersDb, redis: RedisDep) -> dict:
    if payload.exercise_date > _beijing_today():
        raise HTTPException(status_code=400, detail="不能选择今天之后的日期")
    item = db.scalar(
        select(DailyExercise).where(
            DailyExercise.user_id == current_user.id,
            DailyExercise.exercise_date == payload.exercise_date,
        )
    ) or DailyExercise(user_id=current_user.id, exercise_date=payload.exercise_date)
    item.calories_burned = Decimal(str(payload.calories_burned))
    item.exercise_records = payload.exercise_records
    db.merge(item)
    db.commit()
    redis.setex(f"daily:{current_user.id}:{payload.exercise_date}", 86400, json.dumps(payload.model_dump(mode="json"), ensure_ascii=False))
    return {"message": "保存成功"}


@router.get("/daily")
def list_daily_exercise(current_user: CurrentUser, db: UsersDb) -> list[dict]:
    rows = db.scalars(select(DailyExercise).where(DailyExercise.user_id == current_user.id).order_by(DailyExercise.exercise_date.desc())).all()
    return [
        {
            "exercise_date": item.exercise_date.isoformat(),
            "calories_burned": float(item.calories_burned),
            "exercise_records": item.exercise_records or {},
        }
        for item in rows
    ]


@router.delete("/daily/{exercise_date}")
def delete_daily_exercise(exercise_date: str, current_user: CurrentUser, db: UsersDb, redis: RedisDep) -> dict:
    try:
        parsed_date = date.fromisoformat(exercise_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD") from None

    item = db.scalar(
        select(DailyExercise).where(
            DailyExercise.user_id == current_user.id,
            DailyExercise.exercise_date == parsed_date,
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(item)
    db.commit()
    redis.delete(f"daily:{current_user.id}:{exercise_date}")
    return {"message": "删除成功"}
