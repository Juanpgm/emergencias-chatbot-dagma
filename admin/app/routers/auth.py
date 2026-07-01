from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.core.auth import (
    _get_secret,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from shared.core.config import get_settings
from shared.core.database import get_db
from shared.models.emergencia import AdminUser
from shared.schemas.admin import LoginRequest, TokenResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    try:
        result = await db.execute(select(AdminUser).where(AdminUser.username == body.username))
        user = result.scalar_one_or_none()
    except Exception:
        logger.exception("DB error en /auth/login")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

    if not user:
        # Bootstrap: crea el primer admin desde variables de entorno la primera vez
        if body.username == settings.admin_username and body.password == settings.admin_password:
            user = AdminUser(username=body.username, display_name=body.username)
            user.set_password(body.password)
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.verify_password(body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    sub = f"user:{body.username}"
    return TokenResponse(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
    )


class FirebaseLoginRequest(BaseModel):
    id_token: str


@router.post("/firebase", response_model=TokenResponse)
async def firebase_login(body: FirebaseLoginRequest, db: AsyncSession = Depends(get_db)):
    """Intercambia un Firebase ID token por un JWT del sistema."""
    settings = get_settings()

    # Verifica el ID token contra la API pública de Firebase
    verify_url = (
        f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/"
        f"getAccountInfo?key={settings.firebase_api_key}"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(verify_url, json={"idToken": body.id_token})

    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Firebase token")

    data = resp.json()
    users = data.get("users", [])
    if not users or not users[0].get("email"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No email in token")

    email: str = users[0]["email"]

    # Dominio permitido
    allowed = settings.firebase_allowed_domains.split(",")
    domain = email.split("@")[-1]
    if domain not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Domain @{domain} not authorized",
        )

    # Buscar o crear el usuario admin
    result = await db.execute(select(AdminUser).where(AdminUser.username == email))
    user = result.scalar_one_or_none()

    if not user:
        user = AdminUser(username=email, display_name=users[0].get("displayName") or email)
        user.set_password(body.id_token[-16:])
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Nuevo usuario admin creado via Google OAuth: %s", email)

    sub = f"user:{email}"
    return TokenResponse(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    try:
        payload = jwt.decode(body.refresh_token, _get_secret(), algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        sub = payload["sub"]
        return TokenResponse(
            access_token=create_access_token(sub),
            refresh_token=create_refresh_token(sub),
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
