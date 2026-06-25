from __future__ import annotations

from typing import Any

from app.agent.engine import run_agent_question
from app.core.database import UsersSessionLocal, get_redis
from app.services.qa_service import answer_question


def qa_agent_tool(question: str, *, user_id: int | None = None) -> dict[str, Any]:
    """
    MCP 暴露的 `qa_agent` 工具入口。

    约定：
    - 当提供 user_id 时：走独立 Agent 编排层（支持记忆、多工具编排、日志落库）
    - 当未提供 user_id 时：降级为无状态回答（仍基于知识库检索，避免固定模板）
    """
    if not user_id:
        result = answer_question(question)
        # 兼容 Agent 返回结构
        return {
            "question": result.get("question") or question,
            "answer": result.get("answer") or "",
            "sources": result.get("sources") or [],
            "intent": "unknown",
            "session_id": None,
        }

    redis = get_redis()
    db = UsersSessionLocal()
    try:
        return run_agent_question(question=question, user_id=int(user_id), db=db, redis=redis)
    except Exception:
        fallback = answer_question(question)
        return {
            "question": fallback.get("question") or question,
            "answer": fallback.get("answer") or "",
            "sources": fallback.get("sources") or [],
            "intent": "unknown",
            "session_id": None,
        }
    finally:
        db.close()
