from app.services.nutrition_service import lookup_food_nutrition


def nutrition_tool(food_name: str, grams: float) -> dict:
    result = lookup_food_nutrition(food_name, grams)
    if result:
        return {
            "calories": result["calories"],
            "protein": result["protein"],
            "fat": result["fat"],
            "carbs": result["carbs"],
            "food_name": result["food_name"],
        }
    return {"calories": 0, "protein": 0, "fat": 0, "carbs": 0, "food_name": food_name}
