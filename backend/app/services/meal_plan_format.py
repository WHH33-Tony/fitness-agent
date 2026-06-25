from __future__ import annotations

import json
import re
from typing import Any

MEAL_PLAN_MARKER = "__MEAL_PLAN__"


def attach_meal_plan_marker(answer: str, plan: dict[str, Any]) -> str:
    text = (answer or "").strip()
    payload = json.dumps(plan, ensure_ascii=False)
    return f"{text}\n\n{MEAL_PLAN_MARKER}\n{payload}"


def strip_meal_plan_marker(answer: str) -> tuple[str, dict[str, Any] | None]:
    text = answer or ""
    marker_idx = text.find(MEAL_PLAN_MARKER)
    if marker_idx < 0:
        return text.strip(), None
    visible = text[:marker_idx].strip()
    raw_json = text[marker_idx + len(MEAL_PLAN_MARKER) :].strip()
    try:
        plan = json.loads(raw_json)
        if isinstance(plan, dict) and plan.get("days"):
            return visible, plan
    except Exception:
        pass
    return visible or text.strip(), None
