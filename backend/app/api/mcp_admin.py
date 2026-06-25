from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import UsersDb, require_role
from app.models.users import MCPTool, ToolCall, User
from app.services.mcp_tool_log import summarize_tool_log

router = APIRouter(prefix="/mcp", tags=["MCP工具治理"])


@router.get("/tools")
def list_tools(db: UsersDb, _: User = Depends(require_role("admin"))) -> list[dict]:
    rows = db.scalars(select(MCPTool).order_by(MCPTool.tool_name)).all()
    return [
        {
            "tool_name": r.tool_name,
            "description": r.description,
            "input_schema": r.input_schema,
            "endpoint": r.endpoint,
            "is_enabled": bool(r.is_enabled),
            "call_count": int(r.call_count or 0),
            "avg_latency_ms": r.avg_latency_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/tools/{tool_name}/enable")
def enable_tool(tool_name: str, db: UsersDb, _: User = Depends(require_role("admin"))) -> dict:
    row = db.get(MCPTool, tool_name)
    if not row:
        raise HTTPException(status_code=404, detail="工具不存在")
    row.is_enabled = True
    db.commit()
    return {"tool_name": tool_name, "is_enabled": True}


@router.post("/tools/{tool_name}/disable")
def disable_tool(tool_name: str, db: UsersDb, _: User = Depends(require_role("admin"))) -> dict:
    row = db.get(MCPTool, tool_name)
    if not row:
        raise HTTPException(status_code=404, detail="工具不存在")
    row.is_enabled = False
    db.commit()
    return {"tool_name": tool_name, "is_enabled": False}


@router.get("/logs")
def list_logs(
    db: UsersDb,
    _: User = Depends(require_role("admin")),
    tool_name: str | None = None,
    limit: int = 50,
) -> list[dict]:
    limit = max(1, min(int(limit), 200))
    stmt = select(ToolCall).order_by(ToolCall.call_id.desc()).limit(limit)
    if tool_name:
        stmt = stmt.where(ToolCall.tool_name == tool_name)
    rows = db.scalars(stmt).all()
    return [
        {
            "call_id": r.call_id,
            "session_id": r.session_id,
            "tool_name": r.tool_name,
            "status": r.status,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "summary": summarize_tool_log(r.tool_name, r.result, r.status),
            "params": r.params,
            "result": r.result,
        }
        for r in rows
    ]

