from typing import cast

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, RedisDep, UsersDb
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.users import User, UserProfile
from app.schemas import LoginIn, RegisterIn, Role, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["认证"])
settings = get_settings()


@router.post("/register", response_model=TokenOut)
def register(payload: RegisterIn, db: UsersDb, redis: RedisDep) -> TokenOut:
    if db.scalar(select(User).where(User.phone == payload.phone)):
        raise HTTPException(status_code=400, detail="手机号已注册")

    user = User(phone=payload.phone, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id, nickname=f"用户{user.phone[-4:]}"))
    db.commit()
    token = create_access_token(str(user.id), {"role": user.role})
    redis.setex(f"session:{user.id}", settings.access_token_expire_minutes * 60, token)
    return TokenOut(access_token=token, role=cast(Role, user.role))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: UsersDb, redis: RedisDep) -> TokenOut:
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误，请注册或重新输入")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="您的账号已被禁用，等待管理员解锁")

    token = create_access_token(str(user.id), {"role": user.role})
    redis.setex(f"session:{user.id}", settings.access_token_expire_minutes * 60, token)
    return TokenOut(access_token=token, role=cast(Role, user.role))


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)
