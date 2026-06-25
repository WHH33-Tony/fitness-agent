from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.users import AgentSession, QARecord
from app.services.nutrition_service import (
    UserContext,
    build_meal_plan,
    format_meal_plan_text,
    load_user_context,
    lookup_food_nutrition,
)
from app.services.meal_plan_format import attach_meal_plan_marker
from app.services.general_agent import run_general_agent
from app.services.mcp_bootstrap import is_mcp_tool_enabled
from app.services.mcp_tool_log import record_tool_call
from app.services.qa_service import (
    is_fitness_related,
    retrieve_knowledge,
    sanitize_answer_text,
    synthesize_agent_answer,
    synthesize_local_kb_answer,
)

settings = get_settings()

Intent = Literal["knowledge", "nutrition", "pose", "mixed", "unknown", "general"]


@dataclass(frozen=True)
class ToolResult:
    tool: str
    ok: bool
    latency_ms: int
    content: dict[str, Any] | None = None
    error: str | None = None


def _now_ms() -> int:
    return int(time.time() * 1000)


def _memory_key(user_id: int) -> str:
    return f"agent:mem:{user_id}"


def load_short_memory(redis: Redis, user_id: int, limit: int = 5) -> list[dict[str, Any]]:
    try:
        raw = redis.lrange(_memory_key(user_id), 0, limit - 1)
        if not isinstance(raw, list):
            return []
        return [json.loads(x) for x in raw if x]
    except Exception:
        return []


def append_short_memory(redis: Redis, user_id: int, item: dict[str, Any], limit: int = 5) -> None:
    try:
        key = _memory_key(user_id)
        redis.lpush(key, json.dumps(item, ensure_ascii=False))
        redis.ltrim(key, 0, limit - 1)
        redis.expire(key, 60 * 60 * 24 * 7)
    except Exception:
        return


def detect_intent(question: str, memory: list[dict[str, Any]] | None = None) -> Intent:
    q = (question or "").strip()
    if not q:
        return "unknown"

    nutrition_kw = [
        "热量",
        "卡路里",
        "千卡",
        "大卡",
        "蛋白",
        "脂肪",
        "碳水",
        "营养",
        "克",
        "kcal",
        "吃什么",
        "吃多少",
        "饮食",
        "膳食",
        "食谱",
        "一日三餐",
        "早餐",
        "午餐",
        "晚餐",
        "摄入",
        "餐单",
        "不重样",
    ]
    pose_kw = [
        "姿态",
        "纠错",
        "动作",
        "分析动作",
        "评估",
        "评分",
        "深蹲",
        "俯卧撑",
        "膝盖",
        "肘",
        "肩",
        "腰",
        "塌腰",
        "内扣",
        "外翻",
    ]
    meal_followup = any(k in q for k in ["换成", "改成", "再加", "少一点", "多一点", "调整", "修改"])
    if meal_followup and memory and memory[0].get("intent") == "nutrition":
        return "nutrition"
    if "增肌" in q and any(k in q for k in ["吃", "饮食", "营养", "蛋白"]):
        return "nutrition"
    if "减脂" in q and any(k in q for k in ["吃", "饮食", "营养", "热量"]):
        return "nutrition"

    has_nutrition = any(k in q for k in nutrition_kw)
    has_pose = any(k in q for k in pose_kw)
    if has_nutrition and has_pose:
        return "mixed"
    if has_nutrition:
        return "nutrition"
    if has_pose:
        return "pose"
    return "knowledge"


def _extract_food_and_grams(question: str) -> tuple[str | None, float | None]:
    q = question.strip()
    grams = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(克|g)\b", q, flags=re.IGNORECASE)
    if m:
        try:
            grams = float(m.group(1))
        except Exception:
            grams = None

    m2 = re.search(r"([一-龥A-Za-z]{2,20})(?:的)?(?:热量|卡路里|营养|蛋白|脂肪|碳水|多少)", q)
    food = m2.group(1) if m2 else None
    return food, grams


def _needs_meal_plan(question: str) -> bool:
    q = question or ""
    return any(
        k in q
        for k in [
            "吃什么",
            "吃多少",
            "饮食",
            "膳食",
            "食谱",
            "一日三餐",
            "早餐",
            "午餐",
            "晚餐",
            "餐单",
            "不重样",
            "摄入",
            "怎么安排吃",
        ]
    )


def _format_user_summary(ctx: UserContext) -> str:
    parts = []
    if ctx.nickname:
        parts.append(f"昵称：{ctx.nickname}")
    if ctx.height_cm:
        parts.append(f"身高：{ctx.height_cm} cm")
    if ctx.weight_kg:
        parts.append(f"体重：{ctx.weight_kg} kg")
    if ctx.age:
        parts.append(f"年龄：{ctx.age}")
    if ctx.gender and ctx.gender != "unknown":
        parts.append(f"性别：{ctx.gender}")
    if ctx.fitness_goal:
        parts.append(f"健身目标：{ctx.fitness_goal}")
    if ctx.injury_history:
        parts.append(f"伤病史：{'、'.join(ctx.injury_history)}")
    if ctx.avoid_movements:
        parts.append(f"需规避动作：{'、'.join(ctx.avoid_movements)}")
    return "；".join(parts) if parts else "用户资料尚未完善，建议先到个人中心补充身高体重与健身目标。"


def _memory_lines(memory: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in memory[:3]:
        q = (item.get("q") or "").strip()
        a = (item.get("a") or "").strip()
        if q:
            lines.append(f"用户：{q}")
        if a:
            lines.append(f"助手：{a[:220]}")
    return lines


def _injury_training_advice(ctx: UserContext, question: str) -> str | None:
    q = question or ""
    if not any(k in q for k in ["受伤", "崴", "扭伤", "骨折", "疼痛", "脚踝", "膝", "肩伤", "腰伤"]):
        return None
    injuries = ctx.injury_history or []
    injury_hint = f"已知伤病：{'、'.join(injuries)}。" if injuries else ""
    return (
        f"{injury_hint}"
        "针对受伤部位训练，优先遵循“无痛原则”："
        "1) 急性期先休息、冰敷、抬高患处，避免带痛训练；"
        "2) 恢复期从等长收缩、关节活动度练习开始，再逐步加入单侧稳定训练；"
        "3) 避免跳跃、急停变向和高冲击动作，优先选择坐姿/卧姿或支撑面更大的动作；"
        "4) 若疼痛持续加重或出现肿胀麻木，请及时就医评估。"
        "你可以告诉我具体部位（如右脚踝）和当前阶段（刚受伤/恢复期），我会进一步细化动作替代方案。"
    )


class MCPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def rpc(self, method: str, params: dict[str, Any] | None = None, *, request_id: int = 1) -> dict[str, Any]:
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
        with httpx.Client(timeout=20) as client:
            resp = client.post(f"{self.base_url}/rpc", json=payload)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                raise RuntimeError(data["error"].get("message") or "rpc error")
            return data.get("result") or {}

    def call_tool(self, *, session_id: int, name: str, arguments: dict[str, Any]) -> ToolResult:
        started = _now_ms()
        try:
            result = self.rpc(
                "tools/call",
                {"session_id": session_id, "name": name, "arguments": arguments},
                request_id=int(started),
            )
            latency = _now_ms() - started
            return ToolResult(tool=name, ok=True, latency_ms=int(result.get("latency_ms") or latency), content=result.get("content") or {})
        except Exception as e:
            latency = _now_ms() - started
            return ToolResult(tool=name, ok=False, latency_ms=latency, error=str(e))


def _format_sources(sources: list[str]) -> list[str]:
    cleaned = []
    for s in sources:
        s = sanitize_answer_text(s or "")
        if not s:
            continue
        cleaned.append(s[:800])
    return cleaned[:5]


def _save_qa_record(
    *,
    db: Session,
    user_id: int,
    question: str,
    answer: str,
    sources: list[str],
    intent: str,
    session_id: int | None,
) -> None:
    try:
        db.add(
            QARecord(
                user_id=user_id,
                question=question,
                answer=answer,
                sources=sources,
                intent=intent,
                agent_session_id=session_id,
            )
        )
        db.commit()
    except Exception:
        db.rollback()


def run_agent_question(
    *,
    question: str,
    user_id: int,
    db: Session,
    redis: Redis,
) -> dict[str, Any]:
    memory = load_short_memory(redis, user_id, limit=5)
    user_ctx = load_user_context(db, user_id)

    if not is_fitness_related(question, memory):
        intent: Intent = "general"
        general_meta = run_general_agent(question)
        answer = sanitize_answer_text(general_meta["answer"])
        weather = general_meta.get("weather")
        tool_calls = list(general_meta.get("tool_calls") or [])
        session = AgentSession(user_id=user_id, intent=intent, tool_calls=tool_calls)
        db.add(session)
        db.commit()
        db.refresh(session)
        append_short_memory(
            redis,
            user_id,
            {"q": question, "a": answer[:500], "intent": intent, "goal": user_ctx.fitness_goal, "ts": int(time.time())},
            limit=5,
        )
        _save_qa_record(
            db=db,
            user_id=user_id,
            question=question,
            answer=answer,
            sources=[],
            intent=intent,
            session_id=session.session_id,
        )
        return {
            "question": question,
            "answer": answer,
            "sources": [],
            "intent": intent,
            "session_id": session.session_id,
            "weather": weather,
            "answer_mode": general_meta.get("source") or "general",
            "knowledge_mode": "未调用",
            "tools_invoked": [str(t.get("tool")) for t in tool_calls if t.get("tool")],
        }

    intent = detect_intent(question, memory)

    session = AgentSession(user_id=user_id, intent=intent, tool_calls=[])
    db.add(session)
    db.commit()
    db.refresh(session)

    tool_calls: list[dict[str, Any]] = list(session.tool_calls or [])
    session.tool_calls = tool_calls

    tool_results: list[ToolResult] = []
    sources: list[str] = []
    structured_blocks: list[str] = []
    meal_plan: dict[str, Any] | None = None

    mcp = MCPClient(settings.mcp_server_url)

    def add_tool_call_record(result: ToolResult, arguments: dict[str, Any], *, logged_by_mcp: bool = False) -> None:
        tool_calls.append(
            {
                "tool": result.tool,
                "ok": result.ok,
                "latency_ms": result.latency_ms,
                "arguments": arguments,
                "error": result.error,
            }
        )
        if logged_by_mcp:
            return
        try:
            payload = dict(result.content or {})
            if result.error:
                payload["error"] = result.error
            record_tool_call(
                db,
                session_id=session.session_id,
                tool_name=result.tool,
                params=arguments,
                result=payload,
                status="success" if result.ok else "fail",
                latency_ms=max(0, int(result.latency_ms or 0)),
            )
        except Exception:
            db.rollback()

    pose_landmarks: list[dict[str, Any]] | None = None
    pose_movement_name: str | None = None
    try:
        payload = json.loads(question) if question.strip().startswith("{") else {}
        if isinstance(payload, dict) and isinstance(payload.get("landmarks"), list):
            pose_landmarks = payload.get("landmarks")
            pose_movement_name = str(payload.get("movement_name") or payload.get("movement") or "徒手深蹲")
    except Exception:
        pose_landmarks = None
        pose_movement_name = None

    if intent in {"pose", "mixed"} and pose_landmarks:
        args = {"movement_name": pose_movement_name or "徒手深蹲", "landmarks": pose_landmarks}
        if is_mcp_tool_enabled(db, "pose_analysis"):
            res = mcp.call_tool(session_id=session.session_id, name="pose_analysis", arguments=args)
        else:
            res = ToolResult(tool="pose_analysis", ok=False, latency_ms=0, error="工具已在管理端停用")
        tool_results.append(res)
        add_tool_call_record(res, args, logged_by_mcp=res.ok)
        if res.ok and res.content:
            score = res.content.get("score")
            errors = res.content.get("errors") or []
            suggestions = res.content.get("suggestions") or []
            structured_blocks.append(f"姿态分析（{args['movement_name']}）：评分 {score} 分。")
            if errors:
                structured_blocks.append("主要问题：" + "；".join([str(x) for x in errors][:5]) + "。")
            if suggestions:
                structured_blocks.append("改进建议：" + "；".join([str(x) for x in suggestions][:5]) + "。")

    args = {"question": question}
    knowledge_enabled = is_mcp_tool_enabled(db, "knowledge")
    if knowledge_enabled:
        # 启用 knowledge 工具：答辩对比模式 —— 纯大模型，不注入本地知识库
        res = ToolResult(
            tool="knowledge",
            ok=True,
            latency_ms=0,
            content={"mode": "llm", "snippets": []},
        )
    else:
        # 停用 knowledge 工具：仅检索本地知识库，后续不调 Qwen
        local_snippets = retrieve_knowledge(question)
        sources.extend(sanitize_answer_text(str(x)) for x in local_snippets if x)
        res = ToolResult(
            tool="knowledge",
            ok=True,
            latency_ms=0,
            content={"mode": "local_kb", "snippets": local_snippets},
        )
    tool_results.append(res)
    add_tool_call_record(res, args)

    if intent in {"nutrition", "mixed"}:
        food_name, grams = _extract_food_and_grams(question)
        nutrition_enabled = is_mcp_tool_enabled(db, "nutrition")
        if food_name:
            nutrition_args = {"food_name": food_name, "grams": float(grams or 100)}
            if not nutrition_enabled:
                structured_blocks.append("营养估算工具已在管理端停用，暂无法查询该食物营养数据。")
                nutrition_res = ToolResult(
                    tool="nutrition",
                    ok=False,
                    latency_ms=0,
                    error="工具已在管理端停用",
                )
                tool_results.append(nutrition_res)
                add_tool_call_record(nutrition_res, nutrition_args)
            else:
                local = lookup_food_nutrition(food_name, float(grams or 100))
                if local:
                    nutrition_res = ToolResult(
                        tool="nutrition",
                        ok=True,
                        latency_ms=0,
                        content=local,
                    )
                    tool_results.append(nutrition_res)
                    add_tool_call_record(nutrition_res, nutrition_args)
                    structured_blocks.append(
                        f"营养估算（{local['food_name']}，{local['grams']}g）："
                        f"热量 {local['calories']} kcal，蛋白 {local['protein']}g，"
                        f"脂肪 {local['fat']}g，碳水 {local['carbs']}g。"
                    )
                else:
                    res = mcp.call_tool(session_id=session.session_id, name="nutrition", arguments=nutrition_args)
                    tool_results.append(res)
                    add_tool_call_record(res, nutrition_args, logged_by_mcp=res.ok)
                    if res.ok and res.content:
                        structured_blocks.append(
                            f"营养估算（{food_name}，{nutrition_args['grams']}g）：热量 {res.content.get('calories')} kcal，"
                            f"蛋白 {res.content.get('protein')}g，脂肪 {res.content.get('fat')}g，碳水 {res.content.get('carbs')}g。"
                        )
        elif _needs_meal_plan(question) or (memory and memory[0].get("intent") == "nutrition"):
            plan = build_meal_plan(user_ctx, question)
            meal_plan = plan
            structured_blocks.append(format_meal_plan_text(plan))
        else:
            targets = build_meal_plan(user_ctx, question)["targets"]
            structured_blocks.append(
                "你问的是营养相关问题。根据你的资料估算："
                f"每日热量约 {targets['calories']} kcal，蛋白 {targets['protein_g']}g，"
                f"碳水 {targets['carbs_g']}g，脂肪 {targets['fat_g']}g。"
                "你可以继续问“我今天吃什么”或“鸡胸肉200克多少蛋白”。"
            )

    injury_advice = _injury_training_advice(user_ctx, question)
    if injury_advice:
        structured_blocks.append(injury_advice)

    sources = _format_sources(sources)
    answer_mode = "llm" if knowledge_enabled else "local_kb"
    if knowledge_enabled:
        answer = synthesize_agent_answer(
            question=question,
            intent=intent,
            sources=[],
            user_summary=_format_user_summary(user_ctx),
            memory_lines=_memory_lines(memory),
            structured_blocks=structured_blocks,
            llm_only=True,
        )
    else:
        answer = synthesize_local_kb_answer(
            question=question,
            intent=intent,
            sources=sources,
            memory_lines=_memory_lines(memory),
            structured_blocks=structured_blocks,
        )
    answer = sanitize_answer_text(answer)
    stored_answer = answer
    if meal_plan:
        stored_answer = attach_meal_plan_marker(answer, meal_plan)

    session.tool_calls = tool_calls
    db.merge(session)
    db.commit()

    append_short_memory(
        redis,
        user_id,
        {
            "q": question,
            "a": answer[:500],
            "intent": intent,
            "goal": user_ctx.fitness_goal,
            "ts": int(time.time()),
        },
        limit=5,
    )

    _save_qa_record(
        db=db,
        user_id=user_id,
        question=question,
        answer=stored_answer if meal_plan else answer,
        sources=sources,
        intent=intent,
        session_id=session.session_id,
    )

    return {
        "question": question,
        "answer": answer,
        "sources": sources if not knowledge_enabled else [],
        "intent": intent,
        "session_id": session.session_id,
        "meal_plan": meal_plan,
        "answer_mode": answer_mode,
        "knowledge_enabled": knowledge_enabled,
        "knowledge_mode": answer_mode,
        "tools_invoked": [str(t.get("tool")) for t in tool_calls if t.get("tool")],
    }
