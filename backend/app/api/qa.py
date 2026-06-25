import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import CurrentUser, RedisDep, UsersDb, get_current_user, get_users_db, require_role
from app.core.config import get_settings
from app.models.users import QARecord, User, UserProfile
from app.schemas import QARequest, QAResponse, TTSRequest, TTSResponse
from app.services.meal_plan_format import strip_meal_plan_marker
from app.services.qa_dispatch import execute_qa_request
from app.services.qa_service import synthesize_speech, transcribe_audio_file
from app.services.xfyun_tts import synthesize_speech_result

router = APIRouter(prefix="/qa", tags=["健身问答"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("", response_model=QAResponse)
def ask(payload: QARequest, current_user: CurrentUser, db: UsersDb, redis: RedisDep) -> QAResponse:
    profile = db.get(UserProfile, current_user.id)
    voice_type = payload.voice_type or getattr(profile, "voice_type", None) or "xiaoyan"
    result = execute_qa_request(
        question=payload.question,
        user_id=current_user.id,
        db=db,
        redis=redis,
    )
    return QAResponse(
        question=result["question"],
        answer=result["answer"],
        sources=result.get("sources", []),
        intent=result.get("intent"),
        meal_plan=result.get("meal_plan"),
        weather=result.get("weather"),
        answer_mode=result.get("answer_mode"),
        audio_url=synthesize_speech(result["answer"], voice_type),
    )


@router.post("/tts", response_model=TTSResponse)
def synthesize_tts(payload: TTSRequest, current_user: CurrentUser, db: UsersDb) -> TTSResponse:
    profile = db.get(UserProfile, current_user.id)
    voice_type = payload.voice_type or getattr(profile, "voice_type", None) or "xiaoyan"
    result, error = synthesize_speech_result(payload.text, voice_type, settings.upload_dir)
    if not result:
        raise HTTPException(status_code=503, detail=error or "讯飞语音合成未配置或合成失败，请在管理控制台填写讯飞凭证")
    return TTSResponse(
        audio_url=result.get("audio_url"),
        audio_base64=result.get("audio_base64"),
        voice_type=voice_type,
        vcn=result.get("vcn"),
    )


@router.post("/voice", response_model=QAResponse)
async def ask_by_voice(
    current_user: CurrentUser,
    db: UsersDb,
    redis: RedisDep,
    audio: UploadFile = File(...),
) -> QAResponse:
    profile = db.get(UserProfile, current_user.id)
    voice_type = getattr(profile, "voice_type", None) or "xiaoyan"
    audio_dir = os.path.join(settings.upload_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    filename = f"{uuid4().hex}_{audio.filename or 'voice.wav'}"
    path = os.path.join(audio_dir, filename)
    with open(path, "wb") as target:
        target.write(await audio.read())
    question = transcribe_audio_file(path, filename=filename)
    result = execute_qa_request(
        question=question,
        user_id=current_user.id,
        db=db,
        redis=redis,
    )
    return QAResponse(
        question=result["question"],
        answer=result["answer"],
        sources=result.get("sources", []),
        intent=result.get("intent"),
        meal_plan=result.get("meal_plan"),
        weather=result.get("weather"),
        answer_mode=result.get("answer_mode"),
        audio_url=synthesize_speech(result["answer"], voice_type),
    )


@router.post("/knowledge")
async def upload_knowledge(file: UploadFile = File(...), _: User = Depends(require_role("admin"))) -> dict:
    os.makedirs("knowledge_base", exist_ok=True)
    filename = file.filename or "knowledge.md"
    path = os.path.join("knowledge_base", filename)
    with open(path, "wb") as target:
        target.write(await file.read())
    return {"message": "知识库文件已上传", "file": filename}


@router.get("/knowledge")
def list_knowledge_files(_: User = Depends(require_role("admin"))) -> list[dict]:
    kb_dir = Path("knowledge_base")
    if not kb_dir.exists():
        return []
    rows: list[dict] = []
    for p in sorted(kb_dir.iterdir()):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        stat = p.stat()
        rows.append(
            {
                "filename": p.name,
                "size": int(stat.st_size),
                "modified_at": int(stat.st_mtime),
            }
        )
    return rows


@router.delete("/knowledge/{filename}")
def delete_knowledge_file(filename: str, _: User = Depends(require_role("admin"))) -> dict:
    kb_dir = Path("knowledge_base")
    target = (kb_dir / filename).resolve()
    if not kb_dir.exists():
        raise HTTPException(status_code=404, detail="知识库目录不存在")
    # 防止目录穿越
    if kb_dir.resolve() not in target.parents:
        raise HTTPException(status_code=400, detail="非法文件名")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    target.unlink()
    return {"message": "已删除", "file": filename}


@router.get("/history")
def history(current_user: CurrentUser, db: UsersDb, limit: int = 50) -> list[dict]:
    limit = max(1, min(int(limit), 200))
    rows = db.scalars(
        select(QARecord).where(QARecord.user_id == current_user.id).order_by(QARecord.created_at.desc()).limit(limit)
    ).all()
    result = []
    for r in rows:
        display_answer, meal_plan = strip_meal_plan_marker(r.answer or "")
        result.append(
            {
                "id": r.id,
                "question": r.question,
                "answer": display_answer or r.answer,
                "meal_plan": meal_plan,
                "weather": None,
                "sources": r.sources or [],
                "intent": r.intent,
                "agent_session_id": r.agent_session_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    logger.info("QA history request: user_id=%s, returned %s records", current_user.id, len(result))
    return result
