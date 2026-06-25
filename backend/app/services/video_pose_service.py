from __future__ import annotations

import os
from typing import Any

import cv2
import mediapipe as mp

from app.services.pose_service import analyze_landmarks


def analyze_video_file(path: str, movement_name: str, max_frames: int = 60, frame_step: int = 5) -> dict[str, Any]:
    if not os.path.exists(path):
        return {"score": 0, "errors": ["视频文件不存在"], "suggestions": ["请重新上传视频"]}

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return {"score": 0, "errors": ["无法读取视频"], "suggestions": ["请更换视频格式或重新上传"]}

    mp_pose = mp.solutions.pose  # type: ignore[attr-defined]
    pose = mp_pose.Pose(static_image_mode=False, model_complexity=1, enable_segmentation=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)

    results: list[dict[str, Any]] = []
    frame_idx = 0
    try:
        while len(results) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            frame_idx += 1
            if frame_step > 1 and frame_idx % frame_step != 0:
                continue

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out = pose.process(image_rgb)
            if not out.pose_landmarks:
                continue

            landmarks: list[dict[str, float]] = []
            for lm in out.pose_landmarks.landmark:
                landmarks.append({"x": float(lm.x), "y": float(lm.y), "z": float(lm.z), "visibility": float(lm.visibility)})

            results.append(analyze_landmarks(movement_name, landmarks))
    finally:
        cap.release()
        pose.close()

    if not results:
        return {"score": 0, "errors": ["未检测到人体关键点"], "suggestions": ["请保证全身入镜、光线充足并保持相机稳定"]}

    scores = [int(r.get("score") or 0) for r in results]
    avg_score = int(sum(scores) / max(len(scores), 1))

    # 汇总错误/建议（简单去重）
    errors: list[str] = []
    suggestions: list[str] = []
    for r in results:
        for e in r.get("errors") or []:
            if e not in errors:
                errors.append(e)
        for s in r.get("suggestions") or []:
            if s not in suggestions:
                suggestions.append(s)

    return {
        "movement_name": movement_name,
        "score": avg_score,
        "frames_analyzed": len(results),
        "errors": errors[:6] or ["未发现明显错误"],
        "suggestions": suggestions[:6] or ["动作质量较好，继续保持稳定呼吸和节奏"],
    }

