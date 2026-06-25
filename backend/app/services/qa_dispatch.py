from __future__ import annotations

import time
from typing import Any

from redis import Redis
from sqlalchemy.orm import Session

from app.agent.engine import run_agent_question
from app.services.mcp_bootstrap import is_mcp_tool_enabled
from app.services.mcp_tool_log import record_tool_call
from app.services.qa_service import answer_question


def _knowledge_switch_label(db: Session) -> str:
    return "启用" if is_mcp_tool_enabled(db, "knowledge") else "停用"


def _route_note(result: dict[str, Any]) -> str:
    intent = str(result.get("intent") or "")
    if intent == "general":
        source = str(result.get("answer_mode") or "general")
        mapping = {
            "system-clock": "泛化问答 → 系统时钟（日期/时间）",
            "open-meteo": "泛化问答 → 天气 API",
            "qwen": "泛化问答 → 通用大模型",
            "local": "泛化问答 → 本地兜底",
            "weather-error": "泛化问答 → 天气失败兜底",
            "qwen-error": "泛化问答 → 大模型失败兜底",
        }
        return mapping.get(source, f"泛化问答 → {source}")
    if intent == "fallback":
        return "qa_agent 已停用 → 简单问答降级"
    return "健身 Agent 编排（含 knowledge / 营养 / 姿态等分支）"


def _build_qa_agent_log_result(*, question: str, db: Session, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": (question or "")[:200],
        "intent": result.get("intent"),
        "route_note": _route_note(result),
        "answer_mode": result.get("answer_mode"),
        "knowledge_switch": _knowledge_switch_label(db),
        "knowledge_mode": result.get("knowledge_mode"),
        "sources_count": len(result.get("sources") or []),
        "tools_invoked": result.get("tools_invoked") or [],
        "answer_preview": (result.get("answer") or "")[:320],
    }


def execute_qa_request(
    *,
    question: str,
    user_id: int,
    db: Session,
    redis: Redis,
) -> dict[str, Any]:
    started = time.perf_counter()
    params = {"question": question, "user_id": user_id}

    if not is_mcp_tool_enabled(db, "qa_agent"):
        fallback = answer_question(question)
        latency = max(1, int((time.perf_counter() - started) * 1000))
        record_tool_call(
            db,
            session_id=None,
            tool_name="qa_agent",
            params=params,
            result={
                "error": "工具已在管理端停用",
                "question": (question or "")[:120],
                "knowledge_switch": _knowledge_switch_label(db),
                "answer_mode": "simple",
                "knowledge_mode": "Agent已停用",
                "route_note": "qa_agent 已停用 → 简单问答降级",
                "answer_preview": (fallback.get("answer") or "")[:320],
            },
            status="fail",
            latency_ms=latency,
        )
        return {
            "question": question,
            "answer": fallback["answer"],
            "sources": fallback.get("sources", []),
            "intent": "fallback",
            "answer_mode": "simple",
            "knowledge_mode": "Agent已停用",
        }

    try:
        result = run_agent_question(question=question, user_id=user_id, db=db, redis=redis)
    except Exception:
        fallback = answer_question(question)
        latency = max(1, int((time.perf_counter() - started) * 1000))
        record_tool_call(
            db,
            session_id=None,
            tool_name="qa_agent",
            params=params,
            result={
                "error": "Agent 执行异常，已降级",
                "question": (question or "")[:120],
                "knowledge_switch": _knowledge_switch_label(db),
                "answer_mode": "simple",
                "route_note": "Agent 执行异常 → 简单问答降级",
                "answer_preview": (fallback.get("answer") or "")[:320],
            },
            status="fail",
            latency_ms=latency,
        )
        return {
            "question": question,
            "answer": fallback["answer"],
            "sources": fallback.get("sources", []),
        }

    latency = max(1, int((time.perf_counter() - started) * 1000))
    record_tool_call(
        db,
        session_id=result.get("session_id"),
        tool_name="qa_agent",
        params=params,
        result=_build_qa_agent_log_result(question=question, db=db, result=result),
        status="success",
        latency_ms=latency,
    )
    return result
