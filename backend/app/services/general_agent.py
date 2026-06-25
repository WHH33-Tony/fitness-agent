from __future__ import annotations

import time
from typing import Any

from app.core.runtime_config import get_dashscope_api_key
from app.services.datetime_service import answer_datetime_question, get_now_context, is_datetime_question
from app.services.qa_service import _generate_general_answer_with_qwen, format_general_answer_text
from app.services.weather_service import answer_weather_question, extract_city_from_question, is_weather_question


def _city_hint(question: str) -> str:
    city = extract_city_from_question(question)
    return f"{city}" if city else "该城市"


def _tool_record(tool: str, *, ok: bool, latency_ms: int, error: str | None = None) -> dict[str, Any]:
    return {
        "tool": tool,
        "ok": ok,
        "latency_ms": latency_ms,
        "arguments": {},
        "error": error,
    }


def run_general_agent(question: str) -> dict[str, Any]:
    """
    非健身问题的 Agent 编排：
    1) 日期时间 → 系统时钟（无需外网）
    2) 天气 → Open-Meteo
    3) 其他 → Qwen 通用大模型（需 API Key）
    """
    q = (question or "").strip()
    tool_calls: list[dict[str, Any]] = []

    if is_datetime_question(q):
        started = time.time()
        try:
            answer, datetime_ctx = answer_datetime_question(q)
            tool_calls.append(_tool_record("datetime", ok=True, latency_ms=int((time.time() - started) * 1000)))
            return {
                "answer": format_general_answer_text(answer),
                "weather": None,
                "datetime": datetime_ctx,
                "tool_calls": tool_calls,
                "source": "system-clock",
            }
        except Exception as exc:
            tool_calls.append(
                _tool_record("datetime", ok=False, latency_ms=int((time.time() - started) * 1000), error=str(exc))
            )

    if is_weather_question(q):
        started = time.time()
        try:
            answer, weather = answer_weather_question(q)
            tool_calls.append(_tool_record("weather_api", ok=True, latency_ms=int((time.time() - started) * 1000)))
            return {
                "answer": format_general_answer_text(answer),
                "weather": weather,
                "datetime": None,
                "tool_calls": tool_calls,
                "source": "open-meteo",
            }
        except Exception as exc:
            tool_calls.append(
                _tool_record("weather_api", ok=False, latency_ms=int((time.time() - started) * 1000), error=str(exc))
            )
            return {
                "answer": format_general_answer_text(
                    f"一、直接回答\n暂时无法获取{_city_hint(q)}实时天气。\n\n"
                    f"二、详细说明\n- 错误信息：{exc}\n- 请检查网络连接后重试，或换个问法如「北京天气怎么样」"
                ),
                "weather": None,
                "datetime": None,
                "tool_calls": tool_calls,
                "source": "weather-error",
            }

    if not get_dashscope_api_key():
        return {
            "answer": (
                "我是智能健身教练助手，主要解答健身、营养与运动训练相关问题。"
                "日期/天气类问题可走本地工具；其他通用问题需管理员配置 DASHSCOPE_API_KEY。"
            ),
            "weather": None,
            "datetime": None,
            "tool_calls": tool_calls,
            "source": "local",
        }

    started = time.time()
    try:
        answer = format_general_answer_text(_generate_general_answer_with_qwen(q, get_now_context()))
        tool_calls.append(_tool_record("qwen_general", ok=True, latency_ms=int((time.time() - started) * 1000)))
        return {
            "answer": answer,
            "weather": None,
            "datetime": None,
            "tool_calls": tool_calls,
            "source": "qwen",
        }
    except Exception as exc:
        tool_calls.append(
            _tool_record("qwen_general", ok=False, latency_ms=int((time.time() - started) * 1000), error=str(exc))
        )
        return {
            "answer": "暂时无法连接外部大模型，请稍后重试。若持续失败，请管理员检查 DASHSCOPE_API_KEY 是否有效。",
            "weather": None,
            "datetime": None,
            "tool_calls": tool_calls,
            "source": "qwen-error",
        }
