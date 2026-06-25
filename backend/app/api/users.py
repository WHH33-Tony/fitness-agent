from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, UsersDb, require_role
from app.models.users import User, UserProfile
from app.schemas import ProfileIn, ProfileOut, UserOut

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", response_model=list[UserOut])
def list_users(db: UsersDb, _: User = Depends(require_role("admin"))) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id.desc())).all())


@router.patch("/{user_id}", response_model=UserOut)
def update_user_role(
    user_id: int,
    db: UsersDb,
    _: User = Depends(require_role("admin")),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if role is not None:
        if role not in {"admin", "user"}:
            raise HTTPException(status_code=400, detail="非法角色")
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


@router.get("/profile", response_model=ProfileOut)
def get_profile(current_user: CurrentUser, db: UsersDb) -> UserProfile:
    profile = db.get(UserProfile, current_user.id)
    if not profile:
        profile = UserProfile(user_id=current_user.id, nickname=f"用户{current_user.phone[-4:]}")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put("/profile", response_model=ProfileOut)
def save_profile(payload: ProfileIn, current_user: CurrentUser, db: UsersDb) -> UserProfile:
    profile = db.get(UserProfile, current_user.id) or UserProfile(user_id=current_user.id)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.merge(profile)
    db.commit()
    saved = db.get(UserProfile, current_user.id)
    if saved is None:
        raise HTTPException(status_code=500, detail="用户资料保存失败")
    return saved


@router.get("/{user_id}/profile", response_model=ProfileOut)
def get_user_profile(user_id: int, current_user: CurrentUser, db: UsersDb) -> UserProfile:
    # 管理员可查看任意用户；普通用户只能查看自己
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="权限不足")
    profile = db.get(UserProfile, user_id)
    if profile:
        return profile
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    profile = UserProfile(user_id=user_id, nickname=f"用户{user.phone[-4:]}")
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/{user_id}/profile", response_model=ProfileOut)
def update_user_profile(user_id: int, payload: ProfileIn, db: UsersDb, _: User = Depends(require_role("admin"))) -> UserProfile:
    # 仅管理员可修改任意用户资料
    profile = db.get(UserProfile, user_id)
    if not profile:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        profile = UserProfile(user_id=user_id, nickname=f"用户{user.phone[-4:]}")
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.merge(profile)
    db.commit()
    saved = db.get(UserProfile, user_id)
    if saved is None:
        raise HTTPException(status_code=500, detail="用户资料保存失败")
    return saved


