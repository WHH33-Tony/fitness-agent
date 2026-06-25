from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Literal

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.database import UsersSessionLocal
from app.mcp.tools.knowledge import knowledge_tool
from app.mcp.tools.nutrition import nutrition_tool
from app.mcp.tools.pose_analysis import pose_analysis_tool
from app.mcp.tools.qa_agent import qa_agent_tool
from app.mcp.tools.video_analysis import video_analysis_tool
from app.models.users import MCPTool, ToolCall
from app.services.mcp_tool_log import record_tool_call, update_tool_stats

app = FastAPI(title="Fitness MCP Tool Gateway", version="0.2.0")

JsonRpcErrorCode = Literal[-32700, -32600, -32601, -32602, -32603]


@contextmanager
def _users_db():
    db = UsersSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _validate_required(input_schema: dict[str, Any], params: dict[str, Any]) -> None:
    required = input_schema.get("required") or []
    missing = [key for key in required if key not in params]
    if missing:
        raise HTTPException(status_code=400, detail=f"参数缺失: {', '.join(missing)}")

    props: dict[str, Any] = input_schema.get("properties") or {}
    for key, schema in props.items():
        if key not in params:
            continue
        expected = schema.get("type")
        if not expected:
            continue
        value = params[key]
        if expected == "string" and not isinstance(value, str):
            raise HTTPException(status_code=400, detail=f"参数类型错误: {key} 应为 string")
        if expected == "number" and not isinstance(value, (int, float)):
            raise HTTPException(status_code=400, detail=f"参数类型错误: {key} 应为 number")
        if expected == "integer" and not isinstance(value, int):
            raise HTTPException(status_code=400, detail=f"参数类型错误: {key} 应为 integer")
        if expected == "boolean" and not isinstance(value, bool):
            raise HTTPException(status_code=400, detail=f"参数类型错误: {key} 应为 boolean")
        if expected == "array" and not isinstance(value, list):
            raise HTTPException(status_code=400, detail=f"参数类型错误: {key} 应为 array")
        if expected == "object" and not isinstance(value, dict):
            raise HTTPException(status_code=400, detail=f"参数类型错误: {key} 应为 object")


def _tool_enabled(db, tool_name: str) -> bool:
    tool = db.get(MCPTool, tool_name)
    return bool(tool and tool.is_enabled)


def _upsert_tool(db, spec: ToolSpec) -> None:
    row = db.get(MCPTool, spec.name)
    if row:
        row.description = spec.description
        row.input_schema = spec.input_schema
        row.endpoint = spec.endpoint
    else:
        db.add(
            MCPTool(
                tool_name=spec.name,
                description=spec.description,
                input_schema=spec.input_schema,
                endpoint=spec.endpoint,
                is_enabled=True,
            )
        )


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    endpoint: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]


def _builtin_tools() -> dict[str, ToolSpec]:
    return {
        "pose_analysis": ToolSpec(
            name="pose_analysis",
            description="姿态关键点分析（实时/单帧），输出评分与纠错建议",
            input_schema={
                "type": "object",
                "properties": {
                    "movement_name": {"type": "string", "description": "动作名称，如 徒手深蹲/俯卧撑"},
                    "landmarks": {"type": "array", "description": "MediaPipe 33关键点（dict 列表）"},
                },
                "required": ["movement_name", "landmarks"],
            },
            endpoint="internal://pose_service.analyze_landmarks",
            handler=lambda p: pose_analysis_tool(p["movement_name"], p["landmarks"]),
        ),
        "video_analysis": ToolSpec(
            name="video_analysis",
            description="姿态关键点分析、错误检测和评分",
            input_schema={
                "type": "object",
                "properties": {
                    "movement_name": {"type": "string", "description": "动作名称，如 徒手深蹲/标准俯卧撑"},
                    "landmarks": {"type": "array", "description": "MediaPipe 33关键点（dict 列表）"},
                },
                "required": ["movement_name", "landmarks"],
            },
            endpoint="internal://pose_service.analyze_landmarks",
            handler=lambda p: video_analysis_tool(p["movement_name"], p["landmarks"]),
        ),
        "nutrition": ToolSpec(
            name="nutrition",
            description="按食物重量估算营养",
            input_schema={
                "type": "object",
                "properties": {
                    "food_name": {"type": "string", "description": "食物名称，如 鸡胸肉"},
                    "grams": {"type": "number", "description": "重量(克)"},
                },
                "required": ["food_name", "grams"],
            },
            endpoint="internal://nutrition_tool",
            handler=lambda p: nutrition_tool(p["food_name"], float(p["grams"])),
        ),
        "knowledge": ToolSpec(
            name="knowledge",
            description="检索本地健身知识库",
            input_schema={
                "type": "object",
                "properties": {"question": {"type": "string", "description": "检索问题/关键词"}},
                "required": ["question"],
            },
            endpoint="internal://knowledge_base",
            handler=lambda p: knowledge_tool(p["question"]),
        ),
        "qa_agent": ToolSpec(
            name="qa_agent",
            description="健身问答Agent（独立编排层：意图识别/多工具编排/短期记忆/结果融合）",
            input_schema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "用户问题"},
                    "user_id": {"type": "integer", "description": "用户ID（可选；提供则启用记忆与会话落库）"},
                },
                "required": ["question"],
            },
            endpoint="internal://agent_engine.run_agent_question",
            handler=lambda p: qa_agent_tool(p["question"], user_id=p.get("user_id")),
        ),
    }


@app.on_event("startup")
def _startup_register_tools() -> None:
    specs = _builtin_tools()
    try:
        with _users_db() as db:
            for spec in specs.values():
                _upsert_tool(db, spec)
            db.commit()
    except Exception:
        # 允许在未初始化数据库时启动（仅提供内存能力）
        return


class JsonRpcRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class JsonRpcError(BaseModel):
    code: int
    message: str
    data: dict[str, Any] | None = None


class JsonRpcResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None = None
    result: Any | None = None
    error: JsonRpcError | None = None


def _rpc_error(req: JsonRpcRequest, code: JsonRpcErrorCode, message: str, data: dict[str, Any] | None = None) -> JsonRpcResponse:
    return JsonRpcResponse(id=req.id, error=JsonRpcError(code=code, message=message, data=data))


@app.post("/rpc", response_model=JsonRpcResponse)
async def rpc(request: Request) -> JsonRpcResponse:
    try:
        payload = await request.json()
        req = JsonRpcRequest.model_validate(payload)
    except Exception:
        # Parse error / Invalid Request
        dummy = JsonRpcRequest(id=None, method="")  # type: ignore[arg-type]
        return _rpc_error(dummy, -32700, "Parse error")

    specs = _builtin_tools()

    if req.method == "tools/list":
        try:
            with _users_db() as db:
                rows = db.scalars(select(MCPTool).order_by(MCPTool.tool_name)).all()
                return JsonRpcResponse(
                    id=req.id,
                    result=[
                        {
                            "name": r.tool_name,
                            "description": r.description,
                            "input_schema": r.input_schema,
                            "endpoint": r.endpoint,
                            "is_enabled": bool(r.is_enabled),
                            "call_count": int(r.call_count or 0),
                            "avg_latency_ms": r.avg_latency_ms,
                        }
                        for r in rows
                    ],
                )
        except Exception:
            # 数据库不可用时回退内置工具
            return JsonRpcResponse(
                id=req.id,
                result=[
                    {
                        "name": s.name,
                        "description": s.description,
                        "input_schema": s.input_schema,
                        "endpoint": s.endpoint,
                        "is_enabled": True,
                        "call_count": 0,
                        "avg_latency_ms": None,
                    }
                    for s in specs.values()
                ],
            )

    if req.method == "tools/call":
        tool_name = str(req.params.get("name") or "")
        params = req.params.get("arguments") or {}
        if tool_name not in specs:
            return _rpc_error(req, -32601, f"Unknown tool: {tool_name}")
        if not isinstance(params, dict):
            return _rpc_error(req, -32602, "Invalid params: arguments must be object")

        spec = specs[tool_name]
        try:
            _validate_required(spec.input_schema, params)
        except HTTPException as e:
            return _rpc_error(req, -32602, str(e.detail))

        started = _now_ms()
        session_id = req.params.get("session_id")
        if session_id is not None:
            try:
                session_id = int(session_id)
            except Exception:
                session_id = None

        try:
            with _users_db() as db:
                if not _tool_enabled(db, tool_name):
                    return _rpc_error(req, -32603, f"Tool disabled: {tool_name}")
                result = spec.handler(params)
                latency = _now_ms() - started
                record_tool_call(
                    db,
                    session_id=session_id,
                    tool_name=tool_name,
                    params=params,
                    result=result,
                    status="success",
                    latency_ms=latency,
                )
                return JsonRpcResponse(id=req.id, result={"tool": tool_name, "content": result, "latency_ms": latency})
        except Exception as e:
            latency = _now_ms() - started
            try:
                with _users_db() as db:
                    record_tool_call(
                        db,
                        session_id=session_id,
                        tool_name=tool_name,
                        params=params,
                        result={"error": str(e)},
                        status="fail",
                        latency_ms=latency,
                    )
            except Exception:
                pass
            return _rpc_error(req, -32603, "Tool execution failed", {"error": str(e)})

    if req.method == "tools/set_enabled":
        tool_name = str(req.params.get("name") or "")
        enabled = req.params.get("enabled")
        if tool_name not in specs:
            return _rpc_error(req, -32601, f"Unknown tool: {tool_name}")
        if not isinstance(enabled, bool):
            return _rpc_error(req, -32602, "Invalid params: enabled must be boolean")
        try:
            with _users_db() as db:
                row = db.get(MCPTool, tool_name)
                if not row:
                    _upsert_tool(db, specs[tool_name])
                    row = db.get(MCPTool, tool_name)
                assert row is not None
                row.is_enabled = enabled
                db.commit()
                return JsonRpcResponse(id=req.id, result={"name": tool_name, "is_enabled": bool(row.is_enabled)})
        except Exception as e:
            return _rpc_error(req, -32603, "Database error", {"error": str(e)})

    if req.method == "tools/logs":
        tool_name = str(req.params.get("name") or "")
        limit = req.params.get("limit", 20)
        try:
            limit = int(limit)
        except Exception:
            limit = 20
        limit = max(1, min(limit, 200))

        try:
            with _users_db() as db:
                stmt = select(ToolCall).order_by(ToolCall.call_id.desc()).limit(limit)
                if tool_name:
                    stmt = stmt.where(ToolCall.tool_name == tool_name)
                rows = db.scalars(stmt).all()
                return JsonRpcResponse(
                    id=req.id,
                    result=[
                        {
                            "call_id": r.call_id,
                            "session_id": r.session_id,
                            "tool_name": r.tool_name,
                            "status": r.status,
                            "latency_ms": r.latency_ms,
                            "created_at": r.created_at.isoformat() if r.created_at else None,
                        }
                        for r in rows
                    ],
                )
        except Exception as e:
            return _rpc_error(req, -32603, "Database error", {"error": str(e)})

    return _rpc_error(req, -32601, f"Unknown method: {req.method}")


class NutritionPayload(BaseModel):
    food_name: str
    grams: float


class QuestionPayload(BaseModel):
    question: str


class PosePayload(BaseModel):
    movement_name: str
    landmarks: list[dict[str, float]]


@app.get("/tools")
def tools() -> list[dict]:
    # REST 兼容端点（演示用），JSON-RPC 客户端建议改用 /rpc + tools/list
    specs = _builtin_tools()
    try:
        with _users_db() as db:
            rows = db.scalars(select(MCPTool).order_by(MCPTool.tool_name)).all()
            return [
                {
                    "name": r.tool_name,
                    "description": r.description,
                    "input_schema": r.input_schema,
                    "endpoint": r.endpoint,
                    "is_enabled": bool(r.is_enabled),
                    "call_count": int(r.call_count or 0),
                    "avg_latency_ms": r.avg_latency_ms,
                }
                for r in rows
            ]
    except Exception:
        return [{"name": s.name, "description": s.description} for s in specs.values()]


def _ensure_tool_enabled(tool_name: str) -> None:
    with _users_db() as db:
        if not _tool_enabled(db, tool_name):
            raise HTTPException(status_code=403, detail=f"工具已停用: {tool_name}")


@app.post("/tools/video_analysis")
def call_video_analysis(payload: PosePayload) -> dict:
    _ensure_tool_enabled("video_analysis")
    return video_analysis_tool(payload.movement_name, payload.landmarks)


@app.post("/tools/pose_analysis")
def call_pose_analysis(payload: PosePayload) -> dict:
    _ensure_tool_enabled("pose_analysis")
    return pose_analysis_tool(payload.movement_name, payload.landmarks)


@app.post("/tools/nutrition")
def call_nutrition(payload: NutritionPayload) -> dict:
    _ensure_tool_enabled("nutrition")
    return nutrition_tool(payload.food_name, payload.grams)


@app.post("/tools/knowledge")
def call_knowledge(payload: QuestionPayload) -> dict:
    _ensure_tool_enabled("knowledge")
    return knowledge_tool(payload.question)


@app.post("/tools/qa_agent")
def call_qa_agent(payload: QuestionPayload) -> dict:
    _ensure_tool_enabled("qa_agent")
    return qa_agent_tool(payload.question)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001)
