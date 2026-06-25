from app.schemas import QuestionnaireIn


def generate_training_plan(questionnaire: QuestionnaireIn) -> dict:
    goal = questionnaire.fitness_goal or "提升体能"
    level = questionnaire.exercise_level or "初级"
    avoid = "、".join(questionnaire.avoid_movements) or "无"
    injury = "、".join(questionnaire.injury_history) or "无"
    weekly_count = (questionnaire.extra_info or {}).get("weeklyCount", "3-4次")
    full_schedule = [
        {"day": "周一", "focus": "力量基础", "items": ["徒手深蹲 3x12", "俯卧撑 3x10", "平板支撑 3x30秒"]},
        {"day": "周三", "focus": "心肺与核心", "items": ["开合跳 4x30秒", "登山跑 3x30秒", "卷腹 3x15"]},
        {"day": "周五", "focus": "全身循环", "items": ["箭步蹲 3x10", "俯身划船 3x12", "臀桥 3x15"]},
        {"day": "周六", "focus": "弱项改善", "items": ["目标部位专项训练 20分钟", "低强度有氧 15分钟"]},
        {"day": "周日", "focus": "恢复", "items": ["动态拉伸 10分钟", "低强度快走 20分钟"]},
    ]
    if "1-2" in weekly_count:
        schedule = full_schedule[:2]
    elif "5" in weekly_count:
        schedule = full_schedule
    else:
        schedule = full_schedule[:4]

    return {
        "summary": f"目标：{goal}；频率：每周{weekly_count}；基础：{level}；需规避动作：{avoid}；伤病史：{injury}",
        "weekly_schedule": schedule,
        "extra_info": questionnaire.extra_info or {},
        "tips": [
            "训练前热身5到10分钟，训练后拉伸。",
            "动作质量优先于重量和次数。",
            "如出现疼痛，应立即停止并调整动作。",
        ],
    }
