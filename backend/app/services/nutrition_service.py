from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SportsSessionLocal
from app.data.food_db import FOOD_DB
from app.models.sports import NutritionFood
from app.models.users import UserProfile, UserQuestionnaire


@dataclass(frozen=True)
class FoodItem:
    name: str
    category: str
    calories_per_100g: float
    protein: float
    fat: float
    carbs: float


# 营养库未初始化时的兜底食物（保证食谱始终能给出具体食材）
DEFAULT_FOODS: list[FoodItem] = [
    FoodItem(
        name=item["name"],
        category=item["category"],
        calories_per_100g=item["calories"],
        protein=item["protein"],
        fat=item["fat"],
        carbs=item["carbs"],
    )
    for item in FOOD_DB
]


@dataclass
class UserContext:
    user_id: int
    nickname: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    age: int | None = None
    gender: str = "unknown"
    fitness_goal: str | None = None
    exercise_level: str | None = None
    injury_history: list[str] | None = None
    avoid_movements: list[str] | None = None


def load_user_context(db: Session, user_id: int) -> UserContext:
    profile = db.get(UserProfile, user_id)
    questionnaire = db.get(UserQuestionnaire, user_id)
    injuries: list[str] = []
    avoids: list[str] = []
    if questionnaire:
        raw_injuries = questionnaire.injury_history or []
        raw_avoids = questionnaire.avoid_movements or []
        if isinstance(raw_injuries, list):
            injuries = [str(x) for x in raw_injuries if x]
        if isinstance(raw_avoids, list):
            avoids = [str(x) for x in raw_avoids if x]
    return UserContext(
        user_id=user_id,
        nickname=getattr(profile, "nickname", None) if profile else None,
        height_cm=float(profile.height) if profile and profile.height else None,
        weight_kg=float(profile.weight) if profile and profile.weight else None,
        age=getattr(profile, "age", None) if profile else None,
        gender=getattr(profile, "gender", "unknown") if profile else "unknown",
        fitness_goal=getattr(questionnaire, "fitness_goal", None) if questionnaire else None,
        exercise_level=getattr(questionnaire, "exercise_level", None) if questionnaire else None,
        injury_history=injuries or None,
        avoid_movements=avoids or None,
    )


def _goal_from_text(question: str, fitness_goal: str | None) -> str:
    q = question or ""
    goal = (fitness_goal or "").strip()
    if any(k in q for k in ["减脂", "减重", "瘦身", "掉秤"]):
        return "减脂"
    if any(k in q for k in ["增肌", "增重", "练大", "肌肉"]):
        return "增肌"
    if goal:
        if "减脂" in goal or "减重" in goal:
            return "减脂"
        if "增肌" in goal:
            return "增肌"
    return "维持"


def estimate_daily_targets(ctx: UserContext, question: str = "") -> dict[str, Any]:
    weight = ctx.weight_kg or 65.0
    height = ctx.height_cm or 170.0
    age = float(ctx.age or 25)
    gender = ctx.gender or "unknown"
    goal = _goal_from_text(question, ctx.fitness_goal)

    if gender == "female":
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    elif gender == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 78

    activity_factor = 1.55
    if ctx.exercise_level and any(k in ctx.exercise_level for k in ["初", "新手", "少"]):
        activity_factor = 1.375
    elif ctx.exercise_level and any(k in ctx.exercise_level for k in ["高", "频繁", "每天"]):
        activity_factor = 1.725

    calories = bmr * activity_factor
    if goal == "减脂":
        calories -= 400
        protein_per_kg = 2.0
        fat_per_kg = 0.8
    elif goal == "增肌":
        calories += 300
        protein_per_kg = 2.0
        fat_per_kg = 0.9
    else:
        protein_per_kg = 1.4
        fat_per_kg = 0.8

    protein_g = round(weight * protein_per_kg, 1)
    fat_g = round(weight * fat_per_kg, 1)
    calories = max(1400.0, round(calories, 0))
    carbs_g = round(max(0.0, (calories - protein_g * 4 - fat_g * 9) / 4), 1)

    return {
        "goal": goal,
        "calories": calories,
        "protein_g": protein_g,
        "fat_g": fat_g,
        "carbs_g": carbs_g,
        "bmr": round(bmr, 0),
    }


def lookup_food_nutrition(food_name: str, grams: float) -> dict[str, Any] | None:
    name = (food_name or "").strip()
    if not name:
        return None
    matched: FoodItem | None = None
    try:
        with SportsSessionLocal() as sdb:
            food = sdb.scalar(select(NutritionFood).where(NutritionFood.name == name))
            if not food:
                food = sdb.scalar(select(NutritionFood).where(NutritionFood.name.contains(name)))
            if food:
                matched = FoodItem(
                    name=food.name,
                    category=food.category or "其他",
                    calories_per_100g=float(food.calories_per_100g),
                    protein=float(food.protein),
                    fat=float(food.fat),
                    carbs=float(food.carbs),
                )
    except Exception:
        matched = None
    if not matched:
        for item in DEFAULT_FOODS:
            if name in item.name or item.name in name:
                matched = item
                break
    if not matched:
        return None
    ratio = float(grams) / 100.0
    return {
        "food_name": matched.name,
        "grams": float(grams),
        "calories": round(matched.calories_per_100g * ratio, 1),
        "protein": round(matched.protein * ratio, 1),
        "fat": round(matched.fat * ratio, 1),
        "carbs": round(matched.carbs * ratio, 1),
        "category": matched.category,
    }


def _load_food_catalog() -> list[FoodItem]:
    catalog: list[FoodItem] = []
    try:
        with SportsSessionLocal() as sdb:
            rows = list(sdb.scalars(select(NutritionFood).order_by(NutritionFood.name)).all())
            for row in rows:
                catalog.append(
                    FoodItem(
                        name=row.name,
                        category=row.category or "其他",
                        calories_per_100g=float(row.calories_per_100g),
                        protein=float(row.protein),
                        fat=float(row.fat),
                        carbs=float(row.carbs),
                    )
                )
    except Exception:
        catalog = []
    return catalog or DEFAULT_FOODS.copy()


def _foods_by_category(catalog: list[FoodItem], category: str) -> list[FoodItem]:
    return [f for f in catalog if f.category == category]


def _pick(catalog: list[FoodItem], category: str, index: int) -> FoodItem:
    items = _foods_by_category(catalog, category) or catalog
    return items[index % len(items)]


def recipe_days_from_question(question: str) -> int:
    q = question or ""
    if any(k in q for k in ["不重样", "三天", "3天", "一周食谱", "7天", "七天"]):
        return 3
    if any(k in q for k in ["两天", "2天", "两日"]):
        return 2
    return 1


def _meal_items(catalog: list[FoodItem], day_index: int) -> list[tuple[FoodItem, float]]:
    staple_a = _pick(catalog, "主食", day_index)
    staple_b = _pick(catalog, "主食", day_index + 1)
    protein_a = _pick(catalog, "肉蛋", day_index)
    protein_b = _pick(catalog, "肉蛋", day_index + 1)
    veggie = _pick(catalog, "蔬菜", day_index)
    fruit = _pick(catalog, "水果", day_index)
    dairy = _foods_by_category(catalog, "乳制品")
    milk = dairy[day_index % len(dairy)] if dairy else _pick(catalog, "肉蛋", day_index + 2)

    return [
        (staple_a, 50),
        (protein_b, 50),
        (milk, 200),
        (staple_b, 150),
        (protein_a, 150),
        (veggie, 150),
        (staple_a, 120),
        (protein_b, 120),
        (veggie, 120),
        (fruit, 150),
    ]


def _build_day_meals(catalog: list[FoodItem], day_index: int) -> list[dict[str, Any]]:
    breakfast_items = _meal_items(catalog, day_index)[:3]
    lunch_items = _meal_items(catalog, day_index)[3:6]
    dinner_items = _meal_items(catalog, day_index)[6:9]
    snack_items = _meal_items(catalog, day_index)[9:10]
    day_meals: list[dict[str, Any]] = []

    for title, items in [("早餐", breakfast_items), ("午餐", lunch_items), ("晚餐", dinner_items), ("加餐", snack_items)]:
        detail: list[dict[str, Any]] = []
        total = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        for food, grams in items:
            ratio = grams / 100.0
            calories = food.calories_per_100g * ratio
            protein = food.protein * ratio
            fat = food.fat * ratio
            carbs = food.carbs * ratio
            total["calories"] += calories
            total["protein"] += protein
            total["fat"] += fat
            total["carbs"] += carbs
            detail.append(
                {
                    "name": food.name,
                    "grams": int(round(grams)),
                    "calories": round(calories, 1),
                    "protein": round(protein, 1),
                    "fat": round(fat, 1),
                    "carbs": round(carbs, 1),
                }
            )
        day_meals.append({"title": title, "items": detail, "totals": {k: round(v, 1) for k, v in total.items()}})

    return day_meals


def _scale_day_meals(meals: list[dict[str, Any]], target_calories: float) -> list[dict[str, Any]]:
    current = sum(float(meal["totals"]["calories"]) for meal in meals)
    if current <= 0 or target_calories <= 0:
        return meals
    ratio = min(2.5, target_calories * 0.9 / current)
    if ratio <= 1.05:
        return meals

    scaled: list[dict[str, Any]] = []
    for meal in meals:
        detail: list[dict[str, Any]] = []
        totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        for item in meal["items"]:
            grams = max(20, int(round(item["grams"] * ratio)))
            factor = grams / item["grams"] if item["grams"] else 1.0
            calories = round(item["calories"] * factor, 1)
            protein = round(item["protein"] * factor, 1)
            fat = round(item["fat"] * factor, 1)
            carbs = round(item["carbs"] * factor, 1)
            totals["calories"] += calories
            totals["protein"] += protein
            totals["fat"] += fat
            totals["carbs"] += carbs
            detail.append(
                {
                    "name": item["name"],
                    "grams": grams,
                    "calories": calories,
                    "protein": protein,
                    "fat": fat,
                    "carbs": carbs,
                }
            )
        scaled.append({"title": meal["title"], "items": detail, "totals": {k: round(v, 1) for k, v in totals.items()}})
    return scaled


def build_meal_plan(ctx: UserContext, question: str = "") -> dict[str, Any]:
    targets = estimate_daily_targets(ctx, question)
    catalog = _load_food_catalog()
    days = recipe_days_from_question(question)
    day_plans: list[dict[str, Any]] = []

    for day_index in range(days):
        meals = _scale_day_meals(_build_day_meals(catalog, day_index), float(targets.get("calories") or 0))
        day_total = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        for meal in meals:
            for key in day_total:
                day_total[key] += meal["totals"][key]
        day_plans.append(
            {
                "day_label": f"第{day_index + 1}天",
                "meals": meals,
                "day_totals": {k: round(v, 1) for k, v in day_total.items()},
            }
        )

    return {
        "targets": targets,
        "days": day_plans,
        "day_count": days,
        "tips": [
            {"label": "食物互换", "desc": "同类食物可互换，例如鸡胸肉可换牛肉或虾仁。"},
            {"label": "灵活调整", "desc": "想调整某一餐，可直接说“把午餐换成牛肉”或“蛋白再高一点”。"},
            {
                "label": "安全提示",
                "desc": "如出现不适请停止并咨询专业人士；有肾病等病史请遵医嘱调整蛋白摄入。",
            },
        ],
        "note": "当日合计为估算值，与参考目标可能存在小幅偏差，可据体重变化与训练强度微调。",
    }


def meal_plan_intro_text(plan: dict[str, Any]) -> str:
    goal = (plan.get("targets") or {}).get("goal", "维持")
    return f"已按「{goal}」目标为你生成食谱（以下为估算值，可据实际效果微调）。"


def format_meal_plan_text(plan: dict[str, Any]) -> str:
    targets = plan.get("targets") or {}
    goal = targets.get("goal", "维持")
    lines = [
        meal_plan_intro_text(plan),
        "",
        "一、每日营养参考",
        f"- 热量约 {targets.get('calories')} kcal",
        f"- 蛋白质约 {targets.get('protein_g')} g",
        f"- 碳水化合物约 {targets.get('carbs_g')} g",
        f"- 脂肪约 {targets.get('fat_g')} g",
        "",
        "二、具体食谱",
    ]

    for day in plan.get("days") or []:
        if plan.get("day_count", 1) > 1:
            lines.append("")
            lines.append(day.get("day_label", "今日"))
        for meal in day.get("meals") or []:
            lines.append("")
            lines.append(f"【{meal.get('title')}】")
            for item in meal.get("items") or []:
                lines.append(f"- {item['name']} {item['grams']}g")
            totals = meal.get("totals") or {}
            lines.append(
                f"  小计：热量 {totals.get('calories', 0)} kcal，蛋白 {totals.get('protein', 0)}g，碳水 {totals.get('carbs', 0)}g，脂肪 {totals.get('fat', 0)}g"
            )
        day_totals = day.get("day_totals") or {}
        lines.append(
            f"  当日合计：热量 {day_totals.get('calories', 0)} kcal，蛋白 {day_totals.get('protein', 0)}g，碳水 {day_totals.get('carbs', 0)}g，脂肪 {day_totals.get('fat', 0)}g"
        )

    lines.extend(
        [
            "",
            "三、使用提示",
            "- 同类食物可互换，例如鸡胸肉可换牛肉/虾仁。",
            "- 想调整某一餐，可直接说“把午餐换成牛肉”或“蛋白再高一点”。",
        ]
    )
    return "\n".join(lines)
