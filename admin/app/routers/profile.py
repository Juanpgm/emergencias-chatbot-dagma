from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.core.auth import _get_secret, get_current_username, get_current_user, create_access_token, create_refresh_token
from shared.core.config import get_settings
from shared.core.database import get_db
from shared.models.emergencia import AdminUser
from shared.schemas.admin import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    ResetPasswordRequest,
    TokenResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Profile"])


def _user_to_profile(u: AdminUser) -> ProfileResponse:
    return ProfileResponse(
        username=u.username,
        display_name=u.display_name,
        email=u.email,
        created_at=u.created_at.isoformat(),
    )


async def _get_or_create_user(username: str, db: AsyncSession) -> AdminUser:
    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if not user:
        settings = get_settings()
        user = AdminUser(
            username=username,
            display_name=username,
        )
        user.set_password(settings.admin_password)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    username: str = Depends(get_current_username),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_or_create_user(username, db)
    return _user_to_profile(user)


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    username: str = Depends(get_current_username),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_or_create_user(username, db)

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.email is not None:
        user.email = body.email

    await db.commit()
    await db.refresh(user)
    return _user_to_profile(user)


@router.post("/change-password", status_code=200)
async def change_password(
    body: ChangePasswordRequest,
    username: str = Depends(get_current_username),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_or_create_user(username, db)

    if not user.verify_password(body.current_password):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

    user.set_password(body.new_password)
    await db.commit()
    return {"message": "Contraseña actualizada correctamente"}


@router.post("/forgot-password", status_code=200)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if body.username == settings.admin_username:
        user = await _get_or_create_user(body.username, db)
    else:
        result = await db.execute(select(AdminUser).where(AdminUser.username == body.username))
        user = result.scalar_one_or_none()
    if not user:
        return {"message": "Si el usuario existe, recibirá un enlace de recuperación"}

    now = datetime.now(timezone.utc)
    payload = {
        "sub": f"reset:{user.username}",
        "type": "reset",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    token = jwt.encode(payload, _get_secret(), algorithm="HS256")

    user.reset_token = token
    user.reset_token_expires = now + timedelta(hours=1)
    await db.commit()

    logger.info("Password reset token generated for user: %s", user.username)
    return {"message": "Si el usuario existe, recibirá un enlace de recuperación"}


@router.post("/reset-password", response_model=TokenResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = jwt.decode(body.token, _get_secret(), algorithms=["HS256"])
        if payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Token inválido")
        sub = payload["sub"]
        if not sub.startswith("reset:"):
            raise HTTPException(status_code=400, detail="Token inválido")
        username = sub.replace("reset:", "")
    except JWTError:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.reset_token != body.token:
        raise HTTPException(status_code=400, detail="Token ya fue utilizado")
    
    now = datetime.now(timezone.utc)
    if user.reset_token_expires and user.reset_token_expires < now:
        raise HTTPException(status_code=400, detail="Token expirado")

    user.set_password(body.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()

    sub_jwt = f"user:{username}"
    return TokenResponse(
        access_token=create_access_token(sub_jwt),
        refresh_token=create_refresh_token(sub_jwt),
    )
