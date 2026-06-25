from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models.users import MCPTool, ToolCall

ToolCallStatus = Literal["success", "fail", "timeout"]


def update_tool_stats(db: Session, tool_name: str, latency_ms: int) -> None:
    tool = db.get(MCPTool, tool_name)
    if not tool:
        return
    prev_count = int(tool.call_count or 0)
    new_count = prev_count + 1
    tool.call_count = new_count
    if tool.avg_latency_ms is None:
        tool.avg_latency_ms = latency_ms
    else:
        tool.avg_latency_ms = int((tool.avg_latency_ms * prev_count + latency_ms) / new_count)


def record_tool_call(
    db: Session,
    *,
    session_id: int | None,
    tool_name: str,
    params: dict[str, Any] | None,
    result: dict[str, Any] | None,
    status: ToolCallStatus,
    latency_ms: int | None,
) -> None:
    db.add(
        ToolCall(
            session_id=session_id,
            tool_name=tool_name,
            params=params,
            result=result,
            status=status,
            latency_ms=latency_ms,
        )
    )
    update_tool_stats(db, tool_name, int(latency_ms or 0))
    db.commit()


def summarize_tool_log(tool_name: str, result: dict[str, Any] | None, status: str) -> str:
    payload = result or {}
    if status == "fail":
        return str(payload.get("error") or "调用失败")

    if tool_name == "knowledge":
        mode = payload.get("mode")
        if mode == "llm":
            return "大模型模式（未注入知识库）"
        if mode == "local_kb":
            count = len(payload.get("snippets") or [])
            return f"本地知识库模式（命中 {count} 条）"

    if tool_name == "qa_agent":
        parts: list[str] = []
        question = str(payload.get("question") or "").strip()
        if question:
            parts.append(f"问：{question[:36]}{'…' if len(question) > 36 else ''}")
        intent = payload.get("intent")
        if intent:
            parts.append(f"意图 {intent}")
        knowledge_switch = payload.get("knowledge_switch")
        if knowledge_switch:
            parts.append(f"knowledge {knowledge_switch}")
        knowledge_mode = payload.get("knowledge_mode")
        if knowledge_mode:
            if knowledge_mode == "llm":
                parts.append("知识库注入：关")
            elif knowledge_mode == "local_kb":
                count = int(payload.get("sources_count") or 0)
                parts.append(f"知识库注入：开（{count} 条）")
            else:
                parts.append(str(knowledge_mode))
        route_note = payload.get("route_note")
        if route_note:
            parts.append(str(route_note))
        answer_mode = payload.get("answer_mode")
        if answer_mode:
            parts.append(f"回答 {answer_mode}")
        tools = payload.get("tools_invoked") or []
        if tools:
            parts.append(f"子工具 {', '.join(str(t) for t in tools)}")
        preview = str(payload.get("answer_preview") or "").strip()
        if preview:
            parts.append(f"答：{preview[:48]}{'…' if len(preview) > 48 else ''}")
        return " | ".join(parts) if parts else "成功"

    if tool_name == "nutrition" and payload.get("calories") is not None:
        return f"{payload.get('food_name', '食物')} {payload.get('grams', '')}g / {payload.get('calories')} kcal"

    if tool_name in {"pose_analysis", "video_analysis"} and payload.get("score") is not None:
        return f"评分 {payload.get('score')}"

    preview = str(payload.get("answer_preview") or "").strip()
    if preview:
        return preview[:80]
    return "成功"
