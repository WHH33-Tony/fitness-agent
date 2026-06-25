"""动作库 ExerciseDB 内容中文化。"""
from __future__ import annotations

import json
import re
from typing import Any

_ZH_RE = re.compile(r"[\u4e00-\u9fff]")
_LATIN_RE = re.compile(r"[A-Za-z]")

BODY_PART_ZH: dict[str, str] = {
    "chest": "胸部",
    "back": "背部",
    "waist": "腰腹",
    "shoulders": "肩部",
    "upper arms": "上臂",
    "lower arms": "前臂",
    "upper legs": "大腿",
    "lower legs": "小腿",
    "cardio": "有氧",
    "neck": "颈部",
}

EQUIPMENT_ZH: dict[str, str] = {
    "body weight": "徒手",
    "barbell": "杠铃",
    "dumbbell": "哑铃",
    "cable": "拉力绳",
    "ez barbell": "EZ杠铃",
    "smith machine": "史密斯机",
    "band": "弹力带",
    "kettlebell": "壶铃",
    "leverage": "器械",
    "assisted": "辅助器械",
    "medicine ball": "药球",
    "stability ball": "瑜伽球",
    "wheel": "健腹轮",
    "weighted": "负重",
    "rope": "绳",
    "bosu ball": "波速球",
    "resistance band": "弹力带",
    "olympic barbell": "奥杠",
    "trap bar": "六角杠",
    "sled machine": "雪橇机",
    "upper body ergometer": "上肢功率计",
    "elliptical machine": "椭圆机",
    "stationary bike": "固定单车",
    "stepmill machine": "台阶机",
    "skierg machine": "滑雪机",
    "hammer": "悍马机",
}

MUSCLE_ZH: dict[str, str] = {
    "pectorals": "胸大肌",
    "lats": "背阔肌",
    "abs": "腹直肌",
    "deltoids": "三角肌",
    "biceps": "肱二头肌",
    "triceps": "肱三头肌",
    "glutes": "臀大肌",
    "hamstrings": "腘绳肌",
    "quadriceps": "股四头肌",
    "calves": "小腿三头肌",
    "soleus": "比目鱼肌",
    "upper back": "上背",
    "traps": "斜方肌",
    "spine": "竖脊肌",
    "forearms": "前臂肌群",
    "abductors": "髋外展肌",
    "adductors": "髋内收肌",
    "serratus anterior": "前锯肌",
    "serratus": "前锯肌",
    "cardiovascular system": "心肺系统",
    "levator scapulae": "肩胛提肌",
    "rhomboids": "菱形肌",
}

ANGLE_ZH: dict[str, str] = {
    "elbow": "肘",
    "shoulder": "肩",
    "torso": "躯干",
    "hip": "髋",
    "knee": "膝",
    "ankle": "踝",
    "wrist": "腕",
}

DIFFICULTY_ZH: dict[str, str] = {
    "beginner": "初级",
    "intermediate": "中级",
    "advanced": "高级",
}

_EXERCISE_NAME_MAP: dict[str, str] = {
    "push up": "俯卧撑",
    "push-up": "俯卧撑",
    "wide push up": "宽距俯卧撑",
    "pull up": "引体向上",
    "pull-up": "引体向上",
    "chin up": "反手引体向上",
    "bodyweight squat": "徒手深蹲",
    "squat": "深蹲",
    "lunge": "箭步蹲",
    "front plank": "平板支撑",
    "plank": "平板支撑",
    "crunch": "卷腹",
    "jumping jack": "开合跳",
    "bench dip": "长凳臂屈伸",
    "dumbbell shoulder press": "哑铃肩推",
    "dumbbell biceps curl": "哑铃弯举",
    "dumbbell row": "哑铃划船",
    "standing calf raise": "站姿提踵",
    "seated calf raise": "坐姿提踵",
    "wrist curl": "腕弯举",
    "reverse wrist curl": "反向腕弯举",
    "cable cross-over variation": "拉力绳交叉变式",
    "cable crossover": "拉力绳交叉",
    "isometric wipers": "等长雨刷式",
    "elevated single arm push-up": "抬高手单臂俯卧撑",
    "single arm push-up": "单臂俯卧撑",
}

_NAME_WORD_MAP: dict[str, str] = {
    "bodyweight": "徒手",
    "assisted": "辅助",
    "band": "弹力带",
    "dumbbell": "哑铃",
    "barbell": "杠铃",
    "kettlebell": "壶铃",
    "cable": "拉力绳",
    "machine": "器械",
    "smith": "史密斯",
    "bench": "长凳",
    "incline": "上斜",
    "decline": "下斜",
    "standing": "站姿",
    "seated": "坐姿",
    "reverse": "反向",
    "overhand": "正握",
    "underhand": "反握",
    "neutral": "对握",
    "grip": "握法",
    "pulldown": "下拉",
    "press": "推举",
    "raise": "抬举",
    "curl": "弯举",
    "extension": "伸展",
    "row": "划船",
    "fly": "飞鸟",
    "flye": "飞鸟",
    "dip": "臂屈伸",
    "dips": "臂屈伸",
    "bridge": "臀桥",
    "squat": "深蹲",
    "lunge": "箭步蹲",
    "plank": "平板支撑",
    "crunch": "卷腹",
    "jack": "开合跳",
    "jump": "跳跃",
    "pull": "拉",
    "push": "推",
    "up": "上",
    "down": "下",
    "shoulder": "肩部",
    "chest": "胸部",
    "back": "背部",
    "leg": "腿",
    "calf": "小腿",
    "wrist": "手腕",
    "cross": "交叉",
    "over": "",
    "variation": "变式",
    "isometric": "等长",
    "wipers": "雨刷式",
    "single": "单",
    "double": "双",
    "arm": "臂",
    "elevated": "抬高",
    "hammer": "锤式",
    "lateral": "侧",
    "front": "前",
    "rear": "后",
    "wide": "宽距",
    "close": "窄距",
    "alternate": "交替",
    "rotation": "旋转",
    "twist": "扭转",
    "hold": "保持",
    "stretch": "拉伸",
}

_INSTRUCTION_PHRASES: list[tuple[str, str]] = [
    (r"adjust the cable pulleys to chest height", "将拉力绳滑轮调至胸部高度"),
    (r"stand in the center of the cable machine with one foot in front of the other", "站在拉力绳器械中央，一脚在前、一脚在后"),
    (r"grasp the handles with your palms facing down and your arms extended out to the sides", "双手握住把手，掌心向下，双臂向两侧伸直"),
    (r"take a step forward, keeping your arms slightly bent", "向前迈一步，双臂保持微屈"),
    (r"with a slight bend in your elbows, bring your hands together in front of your chest", "肘部微屈，双手在胸前靠拢"),
    (r"pause for a moment, then slowly return your arms back to the starting position", "短暂停顿后，缓慢将双臂收回起始位置"),
    (r"repeat for the desired number of repetitions", "重复至目标次数"),
    (r"start by lying flat on your back on a mat or bench", "平躺在垫子或训练凳上"),
    (r"extend your arms straight out to the sides, perpendicular to your body", "双臂向两侧伸直，与身体垂直"),
    (r"engage your core and lift both legs off the ground, keeping them together and straight", "收紧核心，双腿并拢伸直并抬离地面"),
    (r"start in a push-up position with your hands slightly wider than shoulder-width apart and your feet together", "俯卧撑起始姿势，双手略宽于肩，双脚并拢"),
    (r"extend one arm straight out to the side, parallel to the ground", "单臂向侧面伸直，与地面平行"),
    (r"lower your body towards the ground by bending your elbows, keeping your back straight and core engaged", "屈肘使身体下降，背部挺直，核心收紧"),
    (r"push back up to the starting position", "推起回到起始位置"),
    (r"return to the starting position", "回到起始位置"),
    (r"keep your back straight", "保持背部挺直"),
    (r"keep your core engaged", "保持核心收紧"),
    (r"shoulder-width apart", "与肩同宽"),
    (r"parallel to the ground", "与地面平行"),
    (r"perpendicular to your body", "与身体垂直"),
    (r"starting position", "起始位置"),
    (r"desired number of repetitions", "目标次数"),
    (r"for a moment", "片刻"),
    (r"in front of your chest", "在胸前"),
    (r"in front of the other", "在前、另一只在后"),
    (r"facing down", "向下"),
    (r"facing up", "向上"),
    (r"slightly bent", "微屈"),
    (r"slight bend", "轻微弯曲"),
    (r"both legs", "双腿"),
    (r"both arms", "双臂"),
    (r"one foot", "一只脚"),
    (r"one arm", "单臂"),
    (r"off the ground", "离开地面"),
    (r"on a mat or bench", "在垫子或训练凳上"),
    (r"on your back", "仰卧"),
    (r"on the ground", "在地面"),
    (r"towards the ground", "向地面"),
    (r"straight out to the sides", "向两侧伸直"),
    (r"cable machine", "拉力绳器械"),
    (r"cable pulleys", "拉力绳滑轮"),
    (r"chest height", "胸部高度"),
    (
        r"slowly lower your legs to one side, aiming to touch the ground with your feet while maintaining control",
        "缓慢将双腿放向一侧，双脚尽量触地，全程保持控制",
    ),
    (
        r"pause for a moment, then use your core to lift your legs back to the starting position",
        "短暂停顿后，用核心发力将双腿收回起始位置",
    ),
    (
        r"repeat the movement, this time lowering your legs to the opposite side",
        "换另一侧重复同样动作",
    ),
    (
        r"continue alternating sides for the desired number of repetitions",
        "左右交替进行至目标次数",
    ),
    (
        r"push back up to the starting position, using your chest muscles to lift your body",
        "用胸肌发力推起身体，回到起始位置",
    ),
    (r"repeat on the other arm extended", "换另一侧手臂重复"),
    (r"repeat on the other side", "换另一侧重复"),
    (r"using your chest muscles to lift your body", "用胸肌发力推起身体"),
    (r"use your core to lift your legs back", "用核心发力将双腿收回"),
    (r"alternating sides", "左右交替"),
    (r"opposite side", "另一侧"),
    (r"one side", "一侧"),
    (r"touch the ground", "触地"),
    (r"while maintaining control", "全程保持控制"),
]

_INSTRUCTION_WORD_MAP: dict[str, str] = {
    "position": "姿势",
    "your": "你的",
    "arms": "手臂",
    "arm": "手臂",
    "knees": "膝盖",
    "knee": "膝盖",
    "body": "身体",
    "parallel": "平行",
    "straight": "伸直",
    "ground": "地面",
    "hands": "双手",
    "hand": "手",
    "feet": "双脚",
    "foot": "脚",
    "elbows": "肘部",
    "elbow": "肘部",
    "hips": "髋部",
    "hip": "髋部",
    "squeeze": "收紧",
    "breathe": "呼吸",
    "repeat": "重复",
    "stand": "站立",
    "standing": "站姿",
    "sit": "坐下",
    "seated": "坐姿",
    "keep": "保持",
    "keeping": "保持",
    "maintain": "保持",
    "slowly": "缓慢",
    "raise": "抬起",
    "lower": "下放",
    "bend": "弯曲",
    "bending": "弯曲",
    "extend": "伸展",
    "extended": "伸展",
    "extending": "伸展",
    "back": "背部",
    "chest": "胸部",
    "shoulder": "肩部",
    "shoulders": "肩部",
    "core": "核心",
    "control": "控制",
    "avoid": "避免",
    "grasp": "握住",
    "handles": "把手",
    "handle": "把手",
    "palms": "掌心",
    "palm": "掌心",
    "facing": "朝向",
    "together": "并拢",
    "sides": "两侧",
    "side": "侧面",
    "center": "中央",
    "forward": "向前",
    "pause": "停顿",
    "return": "收回",
    "starting": "起始",
    "desired": "目标",
    "number": "次数",
    "repetitions": "次",
    "repetition": "次",
    "reps": "次",
    "engage": "收紧",
    "lift": "抬起",
    "lifting": "抬起",
    "legs": "双腿",
    "leg": "腿",
    "flat": "平躺",
    "lying": "仰卧",
    "mat": "垫子",
    "bench": "训练凳",
    "perpendicular": "垂直",
    "push": "推",
    "pushing": "推",
    "up": "起",
    "down": "下",
    "width": "宽度",
    "apart": "分开",
    "wide": "宽",
    "wider": "更宽",
    "narrow": "窄",
    "step": "步",
    "machine": "器械",
    "cable": "拉力绳",
    "pulleys": "滑轮",
    "pulley": "滑轮",
    "adjust": "调整",
    "moment": "片刻",
    "slight": "轻微",
    "slightly": "略微",
    "front": "前方",
    "other": "另一只",
    "one": "一只",
    "both": "双",
    "with": "用",
    "and": "并",
    "the": "",
    "a": "",
    "an": "",
    "to": "至",
    "of": "的",
    "in": "在",
    "on": "在",
    "at": "在",
    "by": "通过",
    "for": "进行",
    "then": "然后",
    "while": "同时",
    "during": "过程中",
    "until": "直到",
    "into": "进入",
    "from": "从",
    "out": "向外",
    "aiming": "尽量",
    "touch": "触碰",
    "toes": "脚尖",
    "toe": "脚尖",
    "maintaining": "保持",
    "use": "使用",
    "using": "使用",
    "muscles": "肌群",
    "muscle": "肌肉",
    "movement": "动作",
    "time": "次",
    "this": "这次",
    "opposite": "另一侧",
    "alternating": "交替",
    "continue": "继续",
    "sides": "两侧",
    "same": "同样",
    "again": "再次",
    "only": "仅",
    "throughout": "全程",
    "entire": "整个",
    "range": "幅度",
    "motion": "动作",
    "complete": "完成",
    "full": "完整",
    "hold": "保持",
    "seconds": "秒",
    "second": "秒",
}

_COMPOUND_NAME_REPLACEMENTS: list[tuple[str, str]] = [
    ("push-up", "俯卧撑"),
    ("pull-up", "引体向上"),
    ("chin-up", "反手引体向上"),
    ("cross-over", "交叉"),
    ("crossover", "交叉"),
]


def _latin_ratio(text: str) -> float:
    if not text:
        return 0.0
    latin = len(_LATIN_RE.findall(text))
    return latin / max(len(text), 1)


def translate_body_part(value: str) -> str:
    return BODY_PART_ZH.get((value or "").strip().lower(), value or "")


def translate_equipment(value: str) -> str:
    key = (value or "").strip().lower()
    return EQUIPMENT_ZH.get(key, value or "其他")


def translate_muscle(value: str) -> str:
    key = (value or "").strip().lower()
    return MUSCLE_ZH.get(key, value or "综合肌群")


def translate_difficulty(value: str) -> str:
    return DIFFICULTY_ZH.get((value or "").strip().lower(), "标准")


def translate_angle_key(value: str) -> str:
    return ANGLE_ZH.get((value or "").strip().lower(), value or "")


def translate_exercise_name(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return raw
    low = re.sub(r"\s+", " ", raw.lower())
    if low in _EXERCISE_NAME_MAP:
        return _EXERCISE_NAME_MAP[low]
    if _ZH_RE.search(raw) and _latin_ratio(raw) < 0.2:
        return raw

    for compound, zh in _COMPOUND_NAME_REPLACEMENTS:
        low = low.replace(compound, f" {zh} ")

    tokens = [t for t in re.split(r"[\s\-_/]+", low) if t]
    parts: list[str] = []
    for token in tokens:
        if token in _EXERCISE_NAME_MAP:
            parts.append(_EXERCISE_NAME_MAP[token])
        elif token in _NAME_WORD_MAP:
            zh = _NAME_WORD_MAP[token]
            if zh:
                parts.append(zh)
        else:
            parts.append(token)

    out = ""
    for part in parts:
        if not part:
            continue
        if _LATIN_RE.search(part):
            out = f"{out} {part}".strip()
        else:
            out += part
    return out or raw


def _translate_instruction_line(line: str) -> str:
    if not line:
        return line

    m = re.match(r"^\s*step\s*[:\-]?\s*(\d+)\s*[:\-]?\s*(.*)$", line, flags=re.IGNORECASE)
    if m:
        num = m.group(1)
        rest = (m.group(2) or "").strip()
        line = f"第{num}步：{rest}" if rest else f"第{num}步"

    if _ZH_RE.search(line) and _latin_ratio(line) < 0.15:
        return line

    step_prefix = ""
    body = line
    step_match = re.match(r"^(第\d+步：)(.*)$", line)
    if step_match:
        step_prefix = step_match.group(1)
        body = step_match.group(2)
    body = body.rstrip(" .。!！?？")
    for pattern, zh in sorted(_INSTRUCTION_PHRASES, key=lambda item: len(item[0]), reverse=True):
        body = re.sub(pattern, zh, body, flags=re.IGNORECASE)
    text = f"{step_prefix}{body}"

    if _latin_ratio(text) < 0.08:
        return text.strip()

    text = re.sub(r"\b(the|a|an)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip()

    words = sorted((w for w in _INSTRUCTION_WORD_MAP.keys() if _INSTRUCTION_WORD_MAP[w]), key=len, reverse=True)
    for word in words:
        zh = _INSTRUCTION_WORD_MAP[word]
        text = re.sub(rf"\b{re.escape(word)}\b", zh, text, flags=re.IGNORECASE)

    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([，。；、])", r"\1", text)
    text = text.strip(" ,.;。!！?？")
    return text or line


def translate_instructions(instructions: Any) -> list[str]:
    if not instructions:
        return []
    if isinstance(instructions, str):
        return [_translate_instruction_line(instructions)]
    if isinstance(instructions, list):
        return [_translate_instruction_line(str(item)) for item in instructions if item is not None]
    return [_translate_instruction_line(str(instructions))]


def _maybe_llm_translate(name: str, steps: list[str]) -> tuple[str, list[str]]:
    if _latin_ratio(name) < 0.08 and all(_latin_ratio(s) < 0.08 for s in steps):
        return name, steps
    try:
        from dashscope import Generation

        from app.core.runtime_config import get_dashscope_api_key

        api_key = get_dashscope_api_key()
        if not api_key:
            return name, steps
    except Exception:
        return name, steps

    import dashscope

    dashscope.api_key = api_key
    payload = {"name": name, "steps": steps}
    prompt = (
        "将以下健身动作名称和步骤翻译为自然、专业的中文健身指导用语。"
        "只返回 JSON，格式为 {\"name\":\"...\",\"steps\":[\"...\"]}，不要输出其他内容。\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )
    try:
        resp = Generation.call(model="qwen-turbo", messages=[{"role": "user", "content": prompt}], result_format="message")
        content = resp.output.choices[0].message.content if resp and resp.output else ""
        data = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
        new_name = str(data.get("name") or name).strip() or name
        new_steps = [str(s).strip() for s in (data.get("steps") or steps) if str(s).strip()]
        return new_name, new_steps or steps
    except Exception:
        return name, steps


def localize_exercise_fields(
    *,
    name: str,
    equipment: str,
    body_part: str,
    target: str,
    secondary: list[str],
    target_muscles: list[str],
    instructions: Any,
    difficulty: str,
    standard_pose: dict[str, Any],
) -> dict[str, Any]:
    zh_name = translate_exercise_name(name)
    zh_steps = translate_instructions(instructions)
    zh_name, zh_steps = _maybe_llm_translate(zh_name, zh_steps)

    muscles = [translate_muscle(m) for m in (target_muscles or []) if m]
    if not muscles and target:
        muscles = [translate_muscle(target), *[translate_muscle(m) for m in secondary if m]]

    main_angles = {
        translate_angle_key(k): v for k, v in (standard_pose.get("main_angles") or {}).items()
    }

    return {
        "name": zh_name,
        "difficulty": difficulty,
        "difficulty_label": translate_difficulty(difficulty),
        "equipment": translate_equipment(equipment),
        "body_part": body_part,
        "body_part_label": translate_body_part(body_part),
        "target_muscle": translate_muscle(target),
        "target_muscles": muscles,
        "secondary_muscles": [translate_muscle(m) for m in secondary if m],
        "steps": zh_steps,
        "standard_pose": {
            **standard_pose,
            "main_angles": main_angles,
        },
    }
