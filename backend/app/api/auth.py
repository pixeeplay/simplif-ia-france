"""Authentification : register, login, refresh."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config import settings
from ..database import get_db
from ..models import User, UserRole, UserPlan, AuditLog
from ..schemas.auth import LoginIn, RegisterIn, TokenOut, RefreshIn
from ..schemas.user import UserOut
from ..core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user,
)

router = APIRouter()


async def _audit(db: AsyncSession, *, action: str, user_id=None, email=None, ip=None, ua=None, success=True, payload=None):
    db.add(AuditLog(
        action=action, actor_id=user_id, actor_email=email,
        ip_address=ip, user_agent=ua, success=success,
        payload=payload or {},
    ))


@router.post("/register", response_model=UserOut, status_code=201)
async def register(data: RegisterIn, request: Request, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email déjà utilisé")
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        role=UserRole.USER,
        plan=UserPlan.FREE,
    )
    db.add(user)
    await db.flush()
    await _audit(db, action="user.register", user_id=user.id, email=user.email,
                 ip=request.client.host if request.client else None,
                 ua=request.headers.get("user-agent"))
    return user


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        await _audit(db, action="user.login", email=data.email, success=False,
                     ip=request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    user.last_login_at = datetime.utcnow()
    await _audit(db, action="user.login", user_id=user.id, email=user.email,
                 ip=request.client.host if request.client else None,
                 ua=request.headers.get("user-agent"))
    return TokenOut(
        access_token=create_access_token(str(user.id), {"role": user.role.value}),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh(data: RefreshIn, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token invalide")
    sub = payload.get("sub")
    return TokenOut(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)):
    return current


@router.post("/logout", status_code=204)
async def logout(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _audit(db, action="user.logout", user_id=current.id, email=current.email)
    # Note : en prod, ajouter une blacklist Redis pour invalider le JWT
    return None
