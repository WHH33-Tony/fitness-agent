import base64
import logging
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.deps import CurrentUser, UsersDb, get_current_user, get_users_db
from app.core.config import get_settings
from app.models.users import PoseSession
from app.schemas import PoseFrameIn
from app.services.pose_service import analyze_landmarks
from app.services.video_pose_service import analyze_video_file

router = APIRouter(prefix="/pose", tags=["姿态分析"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/frame")
def analyze_frame(payload: PoseFrameIn, current_user: CurrentUser, db: UsersDb) -> dict:
    result = analyze_landmarks(payload.movement_name, payload.landmarks)
    metrics = result.get("metrics") or {}
    if isinstance(payload.summary_metrics, dict):
        # 合并前端汇总指标，便于历史记录回看（不会覆盖后端关键角度）
        for k, v in payload.summary_metrics.items():
            if k not in metrics:
                metrics[k] = v
    if payload.average_score is not None and "average_score" not in metrics:
        try:
            metrics["average_score"] = int(payload.average_score)
        except Exception:
            pass

    # 优先使用前端传来的平均评分，无平均评分时回退后端单帧评分
    session_score = int(payload.average_score) if payload.average_score is not None else int(result.get("score") or 0)

    db.add(
        PoseSession(
            user_id=current_user.id,
            movement_name=payload.movement_name,
            score=session_score,
            metrics=metrics,
            errors=result.get("errors"),
            suggestions=result.get("suggestions"),
        )
    )
    db.commit()
    return {**result, "metrics": metrics}


@router.get("/history")
def history(current_user: CurrentUser, db: UsersDb, limit: int = 50) -> list[dict]:
    limit = max(1, min(int(limit), 200))
    rows = db.scalars(
        select(PoseSession)
        .where(PoseSession.user_id == current_user.id)
        .order_by(PoseSession.created_at.desc())
        .limit(limit)
    ).all()
    result = [
        {
            "session_id": r.session_id,
            "movement_name": r.movement_name,
            "score": r.score,
            "metrics": r.metrics or {},
            "errors": r.errors or [],
            "suggestions": r.suggestions or [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    logger.info("Pose history request: user_id=%s, returned %s records", current_user.id, len(result))
    return result


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    movement_name: str = "徒手深蹲",
    current_user=Depends(get_current_user),
    db=Depends(get_users_db),
) -> dict:
    video_dir = os.path.join(settings.upload_dir, "videos")
    os.makedirs(video_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "video.mp4")[1] or ".mp4"
    filename = f"{uuid4().hex}{ext}"
    path = os.path.join(video_dir, filename)
    with open(path, "wb") as target:
        target.write(await file.read())
    analysis = analyze_video_file(path, movement_name)
    db.add(
        PoseSession(
            user_id=current_user.id,
            movement_name=movement_name,
            score=int(analysis.get("score") or 0),
            metrics={"frames_analyzed": int(analysis.get("frames_analyzed") or 0)},
            errors=analysis.get("errors"),
            suggestions=analysis.get("suggestions"),
        )
    )
    db.commit()
    return {"message": "视频已上传并完成抽帧分析", "file": filename, "url": f"/uploads/videos/{filename}", "analysis": analysis}


@router.websocket("/ws")
async def pose_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if "landmarks" in data:
                await websocket.send_json(analyze_landmarks(data.get("movement_name", "徒手深蹲"), data["landmarks"]))
            elif "image_base64" in data:
                base64.b64decode(data["image_base64"].split(",")[-1])
                await websocket.send_json({"score": 80, "message": "已收到图像帧，建议前端传MediaPipe关键点以降低服务端压力"})
            else:
                await websocket.send_json({"score": 0, "errors": ["缺少landmarks或image_base64"]})
    except WebSocketDisconnect:
        return
