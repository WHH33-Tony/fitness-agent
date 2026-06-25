from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app.api.deps import CurrentUser, CurrentUserAllowDisabled, UsersDb, require_role
from app.models.users import Feedback, FeedbackMessage, User
from app.schemas import (
    CreateFeedbackIn,
    FeedbackDetailOut,
    FeedbackListOut,
    FeedbackMessageOut,
    FeedbackOut,
    ReplyFeedbackIn,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut)
def create_feedback(payload: CreateFeedbackIn, current_user: CurrentUserAllowDisabled, db: UsersDb) -> Feedback:
    feedback = Feedback(user_id=current_user.id)
    db.add(feedback)
    db.flush()

    feedback.updated_at = func.now()
    db.add(
        FeedbackMessage(
            feedback_id=feedback.id,
            sender_type="user",
            sender_id=current_user.id,
            content=payload.content,
        )
    )
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/my", response_model=list[FeedbackOut])
def get_my_feedbacks(current_user: CurrentUserAllowDisabled, db: UsersDb) -> list[Feedback]:
    return list(
        db.scalars(select(Feedback).where(Feedback.user_id == current_user.id).order_by(Feedback.updated_at.desc())).all()
    )


@router.get("/{feedback_id}", response_model=FeedbackDetailOut)
def get_feedback_detail(feedback_id: int, current_user: CurrentUserAllowDisabled, db: UsersDb) -> dict[str, Any]:
    feedback = db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    if current_user.role != "admin" and feedback.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此反馈")

    messages = list(
        db.scalars(
            select(FeedbackMessage)
            .where(FeedbackMessage.feedback_id == feedback_id)
            .order_by(FeedbackMessage.created_at)
        ).all()
    )

    return {"feedback": feedback, "messages": messages}


@router.post("/{feedback_id}/reply", response_model=FeedbackMessageOut)
def reply_feedback(
    feedback_id: int,
    payload: ReplyFeedbackIn,
    current_user: CurrentUserAllowDisabled,
    db: UsersDb,
) -> FeedbackMessage:
    feedback = db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    is_admin = current_user.role == "admin"
    is_owner = feedback.user_id == current_user.id
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="无权回复此反馈")

    message = FeedbackMessage(
        feedback_id=feedback_id,
        sender_type="admin" if is_admin else "user",
        sender_id=current_user.id,
        content=payload.content,
    )
    db.add(message)

    if is_admin:
        feedback.status = "replied"
    else:
        feedback.status = "pending"
    feedback.updated_at = func.now()

    db.commit()
    db.refresh(message)
    return message


@router.get("", response_model=list[FeedbackListOut])
def list_all_feedbacks(
    db: UsersDb,
    _: User = Depends(require_role("admin")),
    status: Optional[str] = None,
) -> list[dict[str, Any]]:
    query = select(Feedback, User).join(User, Feedback.user_id == User.id)
    if status:
        query = query.where(Feedback.status == status)
    query = query.order_by(Feedback.updated_at.desc())

    results: list[dict[str, Any]] = []
    for feedback, user in db.execute(query).all():
        results.append(
            {
                "id": feedback.id,
                "user_phone": user.phone,
                "status": feedback.status,
                "created_at": feedback.created_at,
                "updated_at": feedback.updated_at,
            }
        )
    return results


@router.patch("/{feedback_id}/close")
def close_feedback(
    feedback_id: int,
    db: UsersDb,
    current_user: CurrentUserAllowDisabled,
) -> dict[str, str]:
    feedback = db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    is_admin = current_user.role == "admin"
    is_owner = feedback.user_id == current_user.id
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="无权关闭此反馈")

    feedback.status = "closed"
    feedback.updated_at = func.now()
    db.commit()
    return {"message": "已关闭"}

