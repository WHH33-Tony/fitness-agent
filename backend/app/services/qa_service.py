from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import dashscope
import requests
from dashscope.audio.asr import Transcription
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.runtime_config import get_dashscope_api_key

settings = get_settings()

_STOP_TOKENS = {
    "怎么",
    "怎么样",
    "什么",
    "如何",
    "为什么",
    "可以",
    "应该",
    "是否",
    "大家",
    "请问",
    "知道",
    "告诉",
}

_OFF_TOPIC_KEYWORDS = [
    "天气",
    "气温",
    "下雨",
    "下雪",
    "股票",
    "基金",
    "汇率",
    "房价",
    "新闻",
    "八卦",
    "明星",
    "电影",
    "电视剧",
    "游戏攻略",
    "彩票",
    "政治",
    "选举",
    "疫情",
    "航班",
    "高铁",
    "导航",
    "地图",
]

_FITNESS_KEYWORDS = [
    "健身",
    "训练",
    "锻炼",
    "运动",
    "减脂",
    "增肌",
    "塑形",
    "体能",
    "有氧",
    "无氧",
    "力量",
    "拉伸",
    "热身",
    "恢复",
    "肌肉",
    "体脂",
    "卡路里",
    "热量",
    "蛋白",
    "碳水",
    "脂肪",
    "营养",
    "饮食",
    "食谱",
    "深蹲",
    "俯卧撑",
    "卧推",
    "硬拉",
    "跑步",
    "姿态",
    "动作",
    "受伤",
    "膝盖",
    "肩",
    "腰",
    "脚踝",
]

_TOPIC_KEYWORDS = [
    "深蹲",
    "俯卧撑",
    "平板支撑",
    "箭步蹲",
    "硬拉",
    "卧推",
    "跑步",
    "拉伸",
    "热量",
    "蛋白",
    "碳水",
    "脂肪",
    "减脂",
    "增肌",
    "脚踝",
    "膝盖",
    "肩",
    "腰",
    "受伤",
    "崴",
    "训练",
    "饮食",
    "吃什么",
]


def _extract_query_tokens(question: str) -> list[str]:
    q = (question or "").strip()
    tokens = [t for t in re.split(r"[\s，。！？、；：]+", q) if len(t) >= 2 and t not in _STOP_TOKENS]
    for kw in _TOPIC_KEYWORDS:
        if kw in q and kw not in tokens:
            tokens.append(kw)
    if q and len(q) >= 2:
        for i in range(len(q) - 1):
            seg = q[i : i + 2]
            if seg in _STOP_TOKENS:
                continue
            if all("\u4e00" <= c <= "\u9fff" for c in seg) and seg not in tokens:
                tokens.append(seg)
    return tokens[:16]


def _score_kb_sections(question: str) -> list[tuple[int, str]]:
    q = (question or "").strip()
    kb_dir = Path("knowledge_base")
    if not kb_dir.exists() or not q:
        return []

    tokens = _extract_query_tokens(q)
    if not tokens:
        return []
    scored: list[tuple[int, str]] = []

    for path in sorted(list(kb_dir.glob("*.md")) + list(kb_dir.glob("*.txt"))):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        filename = path.name.lower()
        for section in _split_kb_sections(text):
            section = sanitize_answer_text(section)
            if not section:
                continue
            score = 0
            for token in tokens:
                if token in section:
                    score += 2 if len(token) >= 3 else 1
            if score <= 0:
                continue
            if q[:12] and q[:12] in section:
                score += 3
            if any(k in q for k in ["吃", "饮食", "营养", "蛋白", "热量", "碳水"]) and "nutrition" in filename:
                score += 5
            if any(k in q for k in ["训练", "怎么练", "练什么", "一周", "动作"]) and "training" in filename:
                score += 5
            if any(k in q for k in ["受伤", "脚踝", "膝盖", "崴", "疼痛"]) and "training" in filename:
                score += 4
            if filename == "fitness.md":
                score -= 2
            scored.append((score, section[:700]))

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


def is_fitness_related(question: str, memory: list[dict[str, Any]] | None = None) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    if q.startswith("{") and '"landmarks"' in q:
        return True
    if any(k in q for k in _OFF_TOPIC_KEYWORDS):
        return False
    if any(k in q for k in _FITNESS_KEYWORDS):
        return True
    if any(k in q for k in _TOPIC_KEYWORDS):
        return True

    memory = memory or []
    followup_hints = ["换成", "改成", "再加", "少一点", "多一点", "调整", "修改", "继续", "那午餐", "那晚餐"]
    if memory and memory[0].get("intent") in {"nutrition", "pose", "knowledge", "mixed"}:
        if any(h in q for h in followup_hints):
            return True

    scored = _score_kb_sections(q)
    return bool(scored and scored[0][0] >= 4)


def _split_kb_sections(text: str) -> list[str]:
    parts = re.split(r"\n(?=##\s+)", text)
    sections = [p.strip() for p in parts if p.strip()]
    if not sections:
        return [text.strip()] if text.strip() else []
    if not sections[0].startswith("##"):
        header = sections[0]
        if len(header) > 120:
            return sections
        merged = []
        for idx, section in enumerate(sections):
            if idx == 0:
                merged.append(section)
            else:
                merged.append(section)
        return merged
    return sections


def sanitize_answer_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    cleaned = re.sub(r"\\([\[\(])(.+?)\\([\]\)])", lambda m: m.group(2).replace(r"\sim", "~").replace("\\", ""), cleaned)
    cleaned = cleaned.replace(r"\#", "")
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def retrieve_knowledge(question: str) -> list[str]:
    scored = _score_kb_sections(question)
    unique: list[str] = []
    seen: set[str] = set()
    for _, snippet in scored:
        key = snippet[:120]
        if key in seen:
            continue
        seen.add(key)
        unique.append(snippet)
        if len(unique) >= 3:
            break
    return unique


def answer_question(question: str) -> dict:
    """
    基于本地知识库检索生成答案。

    - 非健身问题：直接调用外部大模型
    - 健身问题：优先用 Qwen 结合知识库；失败则降级到本地片段
    """
    q = (question or "").strip()
    if not is_fitness_related(q):
        answer = answer_general_question(q)
        return {"question": q, "answer": sanitize_answer_text(answer), "sources": []}

    sources = retrieve_knowledge(q)

    if get_dashscope_api_key():
        try:
            answer = _generate_answer_with_qwen(q, sources)
        except Exception:
            answer = _generate_answer_from_sources(q, sources)
    else:
        answer = _generate_answer_from_sources(q, sources)

    return {"question": q, "answer": sanitize_answer_text(answer), "sources": sources}


def answer_general_question(question: str) -> str:
    from app.services.general_agent import run_general_agent

    return run_general_agent(question)["answer"]


def answer_general_question_with_meta(question: str) -> dict[str, Any]:
    from app.services.general_agent import run_general_agent

    return run_general_agent(question)


def format_general_answer_text(text: str) -> str:
    """将大模型返回的通用回答整理为分段、分点的可读结构。"""
    cleaned = sanitize_answer_text(text)
    if not cleaned:
        return ""

    value = cleaned
    value = re.sub(r"([一二三四五六七八九十]+、)", r"\n\1", value)
    value = re.sub(r"(?:^|\n)(\d+[)）.、]\s*)", r"\n\1", value)
    # 仅在中文冒号后换行，避免把 16:36 这类时间拆成两行
    value = re.sub(r"：\s*", "：\n", value)

    if value.count("\n") < 2:
        sentences = re.split(r"(?<=[。；！？])(?=[^\s])", value)
        grouped: list[str] = []
        for sentence in sentences:
            part = sentence.strip()
            if not part:
                continue
            if any(part.startswith(prefix) for prefix in ("建议", "可以", "此外", "另外", "查询", "注意")):
                grouped.append(f"- {part}")
            else:
                grouped.append(part)
        value = "\n\n".join(grouped)

    value = re.sub(r"(?:^|\n)(建议|可以|查询|注意|推荐)([^。\n]{4,80})", r"\n- \1\2", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _generate_general_answer_with_qwen(question: str, now_context: dict[str, Any] | None = None) -> str:
    from dashscope import Generation

    dashscope.api_key = get_dashscope_api_key()
    now_context = now_context or {}
    now_hint = ""
    if now_context:
        now_hint = (
            f"\n当前系统时间（北京时间）：{now_context.get('date')} {now_context.get('time')} "
            f"{now_context.get('weekday')}\n"
        )
    prompt = f"""你是一个通用知识助手。请直接、准确地回答用户问题。
{now_hint}
用户问题：
{question}

输出格式（必须严格遵守，段与段之间空一行）：
一、直接回答
用 1-2 句话正面回应问题。

二、详细说明
- 第一点说明
- 第二点说明
（每条建议单独一行，行首必须是 - ）

三、实用建议
- 查询途径或注意事项
- 其他可执行建议

要求：
1) 使用纯中文，不要使用 Markdown、LaTeX、反斜杠、星号
2) 必须保留“一、二、三”标题，且标题后换行
3) 若涉及实时信息（天气、股价、新闻），在“一”中说明无法保证实时准确
4) 总字数 180-420 字
"""
    resp = Generation.call(
        model=settings.qwen_model,
        prompt=prompt,
        result_format="message",
        temperature=0.7,
        max_tokens=650,
    )
    if getattr(resp, "status_code", None) != 200:
        raise RuntimeError(getattr(resp, "message", "") or "Qwen调用失败")

    output = getattr(resp, "output", None) or {}
    if isinstance(output, dict):
        choices = output.get("choices") or []
        if choices and isinstance(choices, list):
            msg = (choices[0] or {}).get("message") or {}
            content = (msg.get("content") or "").strip()
            if content:
                return content
        text = (output.get("text") or "").strip()
        if text:
            return text
    raise RuntimeError("Qwen返回为空")


def _is_formatted_meal_plan(block: str) -> bool:
    return "二、具体食谱" in block or "【早餐】" in block or "【午餐】" in block


def synthesize_local_kb_answer(
    *,
    question: str,
    intent: str,
    sources: list[str],
    memory_lines: list[str] | None = None,
    structured_blocks: list[str] | None = None,
) -> str:
    """仅基于本地知识库片段与结构化块合成答案，不调用大模型。"""
    memory_lines = memory_lines or []
    structured_blocks = [sanitize_answer_text(block) for block in (structured_blocks or []) if block]
    sources = [sanitize_answer_text(s) for s in sources if (s or "").strip()]

    meal_plan_blocks = [b for b in structured_blocks if _is_formatted_meal_plan(b)]
    if meal_plan_blocks:
        intro = meal_plan_blocks[0].split("\n", 1)[0].strip()
        parts = [intro or "已为你生成食谱，详见下方表格。"]
        if memory_lines:
            parts.append("已结合你上一轮的饮食话题继续调整。")
        return sanitize_answer_text("\n\n".join(parts))

    if structured_blocks and intent == "nutrition":
        parts = list(structured_blocks)
        if memory_lines:
            parts.append("已结合你上一轮的饮食话题继续调整。")
        parts.append("安全提示：如出现不适请停止并咨询专业人士；有肾病等病史请遵医嘱调整蛋白摄入。")
        return sanitize_answer_text("\n\n".join(parts))

    if structured_blocks and intent in {"nutrition", "mixed"}:
        parts = list(structured_blocks)
        if memory_lines:
            parts.append("已结合你上一轮的饮食话题继续调整。")
        parts.append("安全提示：如出现不适请停止并咨询专业人士；有肾病等病史请遵医嘱调整蛋白摄入。")
        return sanitize_answer_text("\n\n".join(parts))

    parts: list[str] = []
    if structured_blocks:
        parts.extend(structured_blocks)
    if sources:
        best = sources[0]
        if intent in {"knowledge", "pose", "mixed"}:
            parts.append(f"结合知识库，针对你的问题给出建议：\n\n{best}")
        elif not structured_blocks:
            parts.append(f"补充参考：\n{best}")
    if not parts:
        return sanitize_answer_text(_generate_answer_from_sources(question, sources))
    if memory_lines:
        parts.append("已结合你上一轮的话题继续说明。")
    parts.append("安全提示：如出现疼痛/头晕等不适应立即停止；有伤病史建议先咨询专业人士。")
    return sanitize_answer_text("\n\n".join(parts))


def synthesize_agent_answer(
    *,
    question: str,
    intent: str,
    sources: list[str],
    user_summary: str = "",
    memory_lines: list[str] | None = None,
    structured_blocks: list[str] | None = None,
    llm_only: bool = False,
) -> str:
    memory_lines = memory_lines or []
    structured_blocks = [sanitize_answer_text(block) for block in (structured_blocks or []) if block]
    sources = [sanitize_answer_text(s) for s in sources if (s or "").strip()]

    meal_plan_blocks = [b for b in structured_blocks if _is_formatted_meal_plan(b)]
    if meal_plan_blocks:
        intro = meal_plan_blocks[0].split("\n", 1)[0].strip()
        parts = [intro or "已为你生成食谱，详见下方表格。"]
        if memory_lines:
            parts.append("已结合你上一轮的饮食话题继续调整。")
        return sanitize_answer_text("\n\n".join(parts))

    if structured_blocks and intent == "nutrition":
        parts = list(structured_blocks)
        if memory_lines:
            parts.append("已结合你上一轮的饮食话题继续调整。")
        parts.append("安全提示：如出现不适请停止并咨询专业人士；有肾病等病史请遵医嘱调整蛋白摄入。")
        return sanitize_answer_text("\n\n".join(parts))

    if llm_only:
        if get_dashscope_api_key():
            try:
                return sanitize_answer_text(
                    _generate_answer_with_qwen(
                        question,
                        [],
                        intent=intent,
                        user_summary=user_summary,
                        memory_lines=memory_lines,
                        structured_blocks=structured_blocks,
                        llm_only=True,
                    )
                )
            except Exception:
                pass
        return sanitize_answer_text(_generate_answer_from_sources(question, []))

    if get_dashscope_api_key():
        try:
            return sanitize_answer_text(
                _generate_answer_with_qwen(
                    question,
                    sources,
                    intent=intent,
                    user_summary=user_summary,
                    memory_lines=memory_lines,
                    structured_blocks=structured_blocks,
                )
            )
        except Exception:
            pass

    if structured_blocks and intent in {"nutrition", "mixed"}:
        parts = list(structured_blocks)
        if memory_lines:
            parts.append("已结合你上一轮的饮食话题继续调整。")
        parts.append("安全提示：如出现不适请停止并咨询专业人士；有肾病等病史请遵医嘱调整蛋白摄入。")
        return sanitize_answer_text("\n\n".join(parts))

    parts: list[str] = []
    if structured_blocks:
        parts.extend(structured_blocks)
    if sources:
        best = sources[0]
        if intent in {"knowledge", "pose", "mixed"}:
            parts.append(f"结合知识库，针对你的问题给出建议：\n\n{best}")
        elif not structured_blocks:
            parts.append(f"补充参考：\n{best}")
    if not parts:
        return sanitize_answer_text(_generate_answer_from_sources(question, sources))
    if memory_lines:
        parts.append("已结合你上一轮的话题继续说明。")
    parts.append("安全提示：如出现疼痛/头晕等不适应立即停止；有伤病史建议先咨询专业人士。")
    return sanitize_answer_text("\n\n".join(parts))


def _generate_answer_from_sources(question: str, sources: list[str]) -> str:
    # 如果没有命中有效知识库，返回尽量贴近问题的通用建议，但不要复读问题
    if not sources:
        # 尽量从问题里抽取主题词，让兜底回答“看起来更相关”
        q = (question or "").strip()
        topics: list[str] = []
        for k in ["深蹲", "俯卧撑", "平板支撑", "箭步蹲", "硬拉", "卧推", "跑步", "拉伸", "热量", "蛋白", "碳水", "脂肪", "减脂", "增肌"]:
            if k in q:
                topics.append(k)

        # 营养/热量类：给出“怎么问/怎么算”的明确口径
        nutrition_kw = ["热量", "卡路里", "千卡", "大卡", "蛋白", "脂肪", "碳水", "kcal", "克", "g"]
        if any(k in q for k in nutrition_kw):
            return (
                "暂未在本地知识库中找到该食物的精确营养数据。你可以按以下口径获取更准确的结果：\n"
                "1) 明确食物名称（生/熟、去皮/不去皮等）\n"
                "2) 给出重量（如 200g）\n"
                "3) 若需要减脂/增肌，请补充你的目标体重变化与训练频次\n\n"
                "示例提问：\n"
                " - “鸡胸肉（熟）200克多少热量？蛋白多少？”\n"
                " - “燕麦 50g 的碳水/蛋白/脂肪分别多少？”"
            )

        # 动作纠错类：给通用检查点（避免空答案）
        pose_kw = ["纠错", "动作", "姿态", "评分", "深蹲", "俯卧撑", "塌腰", "内扣", "外翻", "膝盖", "肩", "肘", "腰"]
        if any(k in q for k in pose_kw):
            return (
                "暂未在本地知识库中找到该动作的专门条目。我先给你一个通用纠错清单（你也可以补充视频/关键点以获得更精确分析）：\n"
                "1) 关节对齐：膝盖/脚尖方向一致，肩/髋保持稳定\n"
                "2) 动作幅度：在可控范围内逐步增加，不要借力摆动\n"
                "3) 核心收紧：避免塌腰、耸肩等代偿\n"
                "4) 呼吸节奏：发力阶段呼气，回程吸气\n\n"
                "如果你告诉我具体动作（如“徒手深蹲/俯卧撑”）和你出现的问题（如“膝盖内扣/塌腰”），我可以给更细的针对性建议。"
            )

        topic_hint = f"你关注的主题可能是：{'、'.join(topics)}。" if topics else "你可以补充具体动作/目标/频次等信息，我会给更精确的建议。"
        return (
            "暂未在本地知识库中找到直接相关内容。"
            f"{topic_hint}"
            "建议补充训练目标（增肌/减脂/体能）、训练基础、可用器械、每周频次以及是否有伤病史；"
            "在未明确前，优先保证动作标准与循序渐进。"
        )

    # 以“片段引用 + 可执行要点 + 安全提示”的形式组织，保证可追溯 & 不固定模板
    snippets = "\n\n".join([s.strip() for s in sources if (s or "").strip()][:2]).strip()
    snippets = snippets[:900]
    return (
        f"结合知识库，针对你的问题给出建议：\n\n"
        f"{snippets}\n\n"
        f"安全提示：如出现疼痛/头晕等不适应立即停止；有伤病史建议先咨询专业人士。"
    )


def _generate_answer_with_qwen(
    question: str,
    sources: list[str],
    *,
    intent: str = "knowledge",
    user_summary: str = "",
    memory_lines: list[str] | None = None,
    structured_blocks: list[str] | None = None,
    llm_only: bool = False,
) -> str:
    """
    使用 DashScope 的 Qwen 生成答案。

    说明：此处实现尽量轻量，失败则由上层降级到 `_generate_answer_from_sources`。
    """
    from dashscope import Generation

    dashscope.api_key = get_dashscope_api_key()
    if llm_only:
        context = "（本次不注入本地知识库，请仅凭大模型常识与推理作答）"
        role_hint = "请结合用户资料、对话记忆与结构化计算结果回答问题（不引用本地知识库）。"
    else:
        context = "\n\n".join([s.strip() for s in sources if (s or "").strip()][:3]).strip() or "（知识库未命中）"
        role_hint = "请结合用户资料、对话记忆、结构化计算结果与知识库片段回答问题。"
    memory_text = "\n".join(memory_lines or []) or "（无）"
    structured_text = "\n\n".join(structured_blocks or []) or "（无）"

    prompt = f"""你是一位专业的健身教练助手。{role_hint}

用户问题：
{question}

当前意图：{intent}

用户资料/计算摘要：
{user_summary or "（未提供）"}

最近对话记忆：
{memory_text}

结构化计算结果（如营养目标、餐单、营养估算）：
{structured_text}

知识库片段：
{context}

要求：
1) 必须直接回答当前问题，不要复读固定模板
2) 若提供了营养目标/餐单，优先列出具体食物名称和克数
3) 若用户在追问，承接上一轮话题并允许修改计划
4) 不要向用户复述身高、体重、年龄、昵称等个人资料，这些仅用于内部计算
5) 使用纯中文自然语言，不要使用 Markdown、LaTeX、反斜杠符号
6) 分段输出，每一点之间空一行，控制在 260-480 字
"""


    resp = Generation.call(
        model=settings.qwen_model,
        prompt=prompt,
        result_format="message",
        temperature=0.6,
        max_tokens=450,
    )

    if getattr(resp, "status_code", None) != 200:
        raise RuntimeError(getattr(resp, "message", "") or "Qwen调用失败")

    output = getattr(resp, "output", None) or {}
    # DashScope 在不同版本下输出结构可能不同；做兼容提取
    if isinstance(output, dict):
        # message 格式: {"choices":[{"message":{"content":"..."}}]}
        choices = output.get("choices") or []
        if choices and isinstance(choices, list):
            msg = (choices[0] or {}).get("message") or {}
            content = (msg.get("content") or "").strip()
            if content:
                return content
        text = (output.get("text") or "").strip()
        if text:
            return text

    raise RuntimeError("Qwen返回为空")


def transcribe_audio_file(file_path: str, *, filename: str = "") -> str:
    """从本地音频文件识别文本，优先讯飞 IAT，其次百炼实时识别。"""
    import os

    from app.core.runtime_config import xfyun_configured
    from app.services.xfyun_asr import prepare_pcm_audio, transcribe_pcm_bytes

    if not os.path.isfile(file_path) or os.path.getsize(file_path) <= 0:
        raise HTTPException(status_code=400, detail="音频文件为空或不存在")

    with open(file_path, "rb") as fp:
        raw = fp.read()

    try:
        pcm = prepare_pcm_audio(raw, filename=filename or os.path.basename(file_path))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    xfyun_error: str | None = None
    if xfyun_configured():
        text, xfyun_error = transcribe_pcm_bytes(pcm)
        if text:
            return text
        if xfyun_error and not get_dashscope_api_key():
            raise HTTPException(status_code=502, detail=xfyun_error)

    if get_dashscope_api_key():
        text = _transcribe_with_dashscope_pcm(file_path, pcm)
        if text:
            return text

    if xfyun_configured():
        raise HTTPException(status_code=502, detail=xfyun_error or "讯飞语音识别失败")
    raise HTTPException(
        status_code=500,
        detail="未配置语音识别：请在管理控制台填写讯飞凭证，或配置百炼 API Key",
    )


def _transcribe_with_dashscope_pcm(file_path: str, pcm: bytes) -> str:
    import os
    import tempfile

    from dashscope.audio.asr import Recognition, RecognitionCallback

    dashscope.api_key = get_dashscope_api_key()
    pcm_path = file_path
    temp_path: str | None = None
    if not file_path.lower().endswith(".pcm"):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pcm")
        temp.write(pcm)
        temp.close()
        temp_path = temp.name
        pcm_path = temp_path

    class _SilentCallback(RecognitionCallback):
        pass

    try:
        recognition = Recognition(
            model="paraformer-realtime-v2",
            callback=_SilentCallback(),
            format="pcm",
            sample_rate=16000,
        )
        result = recognition.call(file=pcm_path)
        sentence = result.get_sentence() if result else None
        if isinstance(sentence, dict):
            text = str(sentence.get("text") or "").strip()
            if text:
                return text
        if isinstance(sentence, list):
            texts = [str(item.get("text") or "").strip() for item in sentence if isinstance(item, dict)]
            joined = "".join(t for t in texts if t)
            if joined:
                return joined
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"百炼语音识别失败：{exc}") from exc
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass
    return ""


def transcribe_audio(audio_url: str) -> str:
    if not get_dashscope_api_key():
        raise HTTPException(status_code=500, detail="未配置 DASHSCOPE_API_KEY，无法调用阿里云百炼ASR")

    dashscope.api_key = get_dashscope_api_key()
    task_response = Transcription.async_call(model="paraformer-v2", file_urls=[audio_url])
    if task_response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"ASR任务提交失败：{getattr(task_response, 'message', '未知错误')}")

    task_id = get_output_value(task_response.output, "task_id")
    transcription_response = Transcription.wait(task=task_id)
    if transcription_response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"ASR识别失败：{getattr(transcription_response, 'message', '未知错误')}")

    text = extract_transcription_text(transcription_response.output)
    if not text:
        raise HTTPException(status_code=502, detail="ASR未返回有效识别文本，请确认音频地址可公网访问")
    return text


def build_upload_url(relative_path: str) -> str:
    return urljoin(settings.public_base_url.rstrip("/") + "/", relative_path.lstrip("/"))


def get_output_value(output: object, key: str) -> str:
    if isinstance(output, dict):
        return output.get(key, "")
    return getattr(output, key, "")


def extract_transcription_text(output: object) -> str:
    data = output if isinstance(output, dict) else getattr(output, "__dict__", {})
    results = data.get("results") or []
    texts: list[str] = []
    for item in results:
        transcription_url = item.get("transcription_url")
        if transcription_url:
            texts.append(fetch_transcription_text(transcription_url))
        text = item.get("text") or item.get("transcript")
        if text:
            texts.append(text)
        sentences = item.get("sentences") or []
        texts.extend(sentence.get("text", "") for sentence in sentences if sentence.get("text"))
    return " ".join(texts).strip()


def fetch_transcription_text(transcription_url: str) -> str:
    response = requests.get(transcription_url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    transcripts = payload.get("transcripts") or []
    texts: list[str] = []
    for transcript in transcripts:
        text = transcript.get("text")
        if text:
            texts.append(text)
        sentences = transcript.get("sentences") or []
        texts.extend(sentence.get("text", "") for sentence in sentences if sentence.get("text"))
    return " ".join(texts)


def synthesize_speech(text: str, voice_type: str) -> str | None:
    """调用讯飞 TTS 合成语音，返回可播放的音频 URL。"""
    from app.core.config import get_settings
    from app.services.xfyun_tts import synthesize_and_save

    return synthesize_and_save(text, voice_type, get_settings().upload_dir)


def synthesize_speech_placeholder(text: str, voice_type: str) -> str | None:
    return synthesize_speech(text, voice_type)
