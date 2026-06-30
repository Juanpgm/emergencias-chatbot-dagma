from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from shared.core.config import get_settings

_security = HTTPBearer()

ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24h para desarrollo
REFRESH_TOKEN_EXPIRE_DAYS = 7


def _get_secret() -> str:
    return get_settings().jwt_secret_key


def create_access_token(sub: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": "admin",
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _get_secret(), algorithm="HS256")


def create_refresh_token(sub: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": "admin",
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _get_secret(), algorithm="HS256")


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=["HS256"])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)) -> dict:
    return verify_token(credentials.credentials)


async def get_current_user_optional(credentials: HTTPAuthorizationCredentials | None = Depends(_security)) -> dict | None:
    if credentials is None:
        return None
    try:
        return verify_token(credentials.credentials)
    except HTTPException:
        return None


def extract_username(payload: dict) -> str:
    sub = payload.get("sub", "unknown")
    return sub.replace("user:", "") if isinstance(sub, str) and sub.startswith("user:") else sub


async def get_current_username(current_user: dict = Depends(get_current_user)) -> str:
    return extract_username(current_user)
