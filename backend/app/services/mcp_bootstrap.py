"""启动时注册 MCP 工具，并在首次运行时写入演示调用日志（便于管理端展示）。"""
from __future__ import annotations

import logging
import time

from sqlalchemy import func, select

from app.core.database import UsersSessionLocal
from app.models.users import ToolCall

logger = logging.getLogger(__name__)


def is_mcp_tool_enabled(db, tool_name: str, *, default: bool = True) -> bool:
    from app.models.users import MCPTool

    row = db.get(MCPTool, tool_name)
    if not row:
        return default
    return bool(row.is_enabled)


def bootstrap_mcp_tools(*, seed_demo_logs: bool = True) -> None:
    try:
        from app.mcp.server import _builtin_tools, _upsert_tool
        from app.services.mcp_tool_log import record_tool_call
    except Exception:
        logger.exception("MCP 工具模块加载失败")
        return

    specs = _builtin_tools()
    try:
        from app.core.database import UsersBase, users_engine
        from app.models.users import MCPTool, ToolCall  # noqa: F401

        UsersBase.metadata.create_all(bind=users_engine)

        with UsersSessionLocal() as db:
            for spec in specs.values():
                _upsert_tool(db, spec)
            db.commit()

            if not seed_demo_logs:
                return

            existing = int(db.scalar(select(func.count()).select_from(ToolCall)) or 0)
            if existing > 0:
                return

            demo_calls: list[tuple[str, dict]] = [
                ("knowledge", {"question": "深蹲动作要领"}),
                ("nutrition", {"food_name": "鸡胸肉", "grams": 100}),
                ("qa_agent", {"question": "减脂期间如何安排训练？", "user_id": None}),
            ]

            for tool_name, params in demo_calls:
                spec = specs.get(tool_name)
                if not spec:
                    continue
                started = int(time.time() * 1000)
                try:
                    result = spec.handler(params)
                    latency = max(1, int(time.time() * 1000) - started)
                    record_tool_call(
                        db,
                        session_id=None,
                        tool_name=tool_name,
                        params=params,
                        result=result if isinstance(result, dict) else {"ok": True},
                        status="success",
                        latency_ms=latency,
                    )
                except Exception as exc:
                    latency = max(1, int(time.time() * 1000) - started)
                    record_tool_call(
                        db,
                        session_id=None,
                        tool_name=tool_name,
                        params=params,
                        result={"error": str(exc)},
                        status="fail",
                        latency_ms=latency,
                    )
                    logger.warning("MCP 演示调用失败 tool=%s: %s", tool_name, exc)

            logger.info("MCP 工具已注册，并写入演示调用日志")
    except Exception:
        logger.exception("MCP 工具启动初始化失败")
