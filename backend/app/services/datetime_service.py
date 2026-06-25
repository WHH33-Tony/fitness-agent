from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

_BEIJING_TZ = timezone(timedelta(hours=8))
_WEEKDAY_ZH = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def get_now_context(tz_name: str = "Asia/Shanghai") -> dict[str, Any]:
    _ = tz_name
    now = datetime.now(_BEIJING_TZ)
    return {
        "timezone": "Asia/Shanghai (UTC+8)",
        "iso": now.isoformat(timespec="seconds"),
        "date": now.strftime("%Y年%m月%d日"),
        "time": now.strftime("%H:%M"),
        "weekday": _WEEKDAY_ZH[now.weekday()],
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "hour": now.hour,
        "minute": now.minute,
    }


def is_datetime_question(question: str) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    keywords = [
        "星期几",
        "礼拜几",
        "周几",
        "几号",
        "几月几号",
        "几月几日",
        "今天日期",
        "什么日期",
        "哪天",
        "几号了",
        "现在几点",
        "几点了",
        "什么时间",
        "当前时间",
        "今天是",
        "今日是",
    ]
    if any(k in q for k in keywords):
        return True
    return bool(re.search(r"(今天|现在|当前).{0,6}(星期|礼拜|周几|日期|时间|几点)", q))


def answer_datetime_question(question: str) -> tuple[str, dict[str, Any]]:
    ctx = get_now_context()
    q = (question or "").strip().lower()

    wants_time = any(k in q for k in ["几点", "时间", "几时"])
    wants_date = any(k in q for k in ["几号", "日期", "几月", "哪天"])
    wants_weekday = any(k in q for k in ["星期", "礼拜", "周几"]) or "星期几" in q

    if not wants_time and not wants_date and not wants_weekday:
        wants_weekday = True
        wants_date = True

    direct_parts: list[str] = []
    if wants_weekday:
        direct_parts.append(f"今天是{ctx['weekday']}")
    if wants_date:
        direct_parts.append(f"日期是{ctx['date']}")
    if wants_time:
        direct_parts.append(f"当前时间是{ctx['time']}")

    direct = "，".join(direct_parts) + "。"

    lines = [
        "一、直接回答",
        direct,
        "",
        "二、详细说明",
        f"- 时区：{ctx['timezone']}（北京时间）",
        f"- 完整时间：{ctx['date']} {ctx['time']} {ctx['weekday']}",
        "",
        "三、实用建议",
        "- 以上时间来自服务器系统时钟，可直接用于安排训练与饮食计划。",
    ]
    return "\n".join(lines), ctx
