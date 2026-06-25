import math
from typing import Any


def _angle(a: dict[str, float], b: dict[str, float], c: dict[str, float]) -> float:
    ab = (a["x"] - b["x"], a["y"] - b["y"])
    cb = (c["x"] - b["x"], c["y"] - b["y"])
    dot = ab[0] * cb[0] + ab[1] * cb[1]
    mag = math.hypot(*ab) * math.hypot(*cb)
    if mag == 0:
        return 0
    return math.degrees(math.acos(max(-1, min(1, dot / mag))))


def analyze_landmarks(movement_name: str, landmarks: list[dict[str, float]]) -> dict[str, Any]:
    if len(landmarks) < 33:
        return {"score": 0, "errors": ["关键点不足，需要MediaPipe Pose 33个关键点"], "suggestions": ["请确保全身进入画面"]}

    left_hip, left_knee, left_ankle = landmarks[23], landmarks[25], landmarks[27]
    right_hip, right_knee, right_ankle = landmarks[24], landmarks[26], landmarks[28]
    left_shoulder, left_elbow, left_wrist = landmarks[11], landmarks[13], landmarks[15]
    right_shoulder, right_elbow, right_wrist = landmarks[12], landmarks[14], landmarks[16]

    knee_angle = (_angle(left_hip, left_knee, left_ankle) + _angle(right_hip, right_knee, right_ankle)) / 2
    elbow_angle = (_angle(left_shoulder, left_elbow, left_wrist) + _angle(right_shoulder, right_elbow, right_wrist)) / 2

    errors: list[str] = []
    suggestions: list[str] = []
    score = 90

    if "深蹲" in movement_name and knee_angle > 115:
        score -= 25
        errors.append("深蹲幅度不足")
        suggestions.append("继续下蹲，让膝关节角度接近90度，同时保持膝盖朝向脚尖")
    if "俯卧撑" in movement_name and elbow_angle > 120:
        score -= 20
        errors.append("屈肘幅度不足")
        suggestions.append("下降时让肘关节更充分弯曲，胸部接近地面")

    return {
        "movement_name": movement_name,
        "score": max(score, 0),
        "metrics": {"knee_angle": round(knee_angle, 2), "elbow_angle": round(elbow_angle, 2)},
        "errors": errors or ["未发现明显错误"],
        "suggestions": suggestions or ["动作质量较好，继续保持稳定呼吸和节奏"],
    }
