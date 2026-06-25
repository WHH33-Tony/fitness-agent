from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_redis, get_sports_db, get_users_db
from app.core.security import decode_token
from app.models.users import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

UsersDb = Annotated[Session, Depends(get_users_db)]
SportsDb = Annotated[Session, Depends(get_sports_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: UsersDb, redis: RedisDep) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise ValueError("missing sub")
        user_id = int(sub)
    except (JWTError, TypeError, ValueError):
        raise credentials_error from None

    if redis.get(f"token:blacklist:{token}"):
        raise credentials_error

    user = db.get(User, user_id)
    if not user:
        raise credentials_error
    if not user.is_active:
        raise HTTPException(status_code=403, detail="您的账号已被禁用，等待管理员解锁")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_user_allow_disabled(token: Annotated[str, Depends(oauth2_scheme)], db: UsersDb, redis: RedisDep) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise ValueError("missing sub")
        user_id = int(sub)
    except (JWTError, TypeError, ValueError):
        raise credentials_error from None

    if redis.get(f"token:blacklist:{token}"):
        raise credentials_error

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise credentials_error
    return user


CurrentUserAllowDisabled = Annotated[User, Depends(get_current_user_allow_disabled)]


def require_role(*roles: str):
    def checker(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="当前角色无权访问该功能")
        return current_user

    return checker
