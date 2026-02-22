"""
FiscalSpy — API Routes: Auth
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.models import Organization, RefreshToken, User
from app.schemas.schemas import (
    LoginRequest,
    MessageResponse,
    OrgOut,
    PasswordChange,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def slugify(name: str) -> str:
    import re
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:60] + "-" + secrets.token_hex(4)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    org = Organization(
        name       = body.org_name,
        slug       = slugify(body.org_name),
        cnpj       = body.org_cnpj,
        plan       = "free",
        docs_limit = 500,
    )
    db.add(org)
    await db.flush()

    user = User(
        organization_id = org.id,
        email           = body.email,
        full_name       = body.full_name,
        hashed_password = hash_password(body.password),
        role            = "owner",
        is_verified     = False,
    )
    db.add(user)
    await db.flush()

    access_token   = create_access_token(user.id, {"org_id": str(org.id), "role": user.role})
    refresh_raw    = create_refresh_token()
    refresh_hashed = hash_token(refresh_raw)

    rt = RefreshToken(
        user_id    = user.id,
        token_hash = refresh_hashed,
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(rt)
    await db.commit()

    return TokenResponse(
        access_token  = access_token,
        refresh_token = refresh_raw,
        expires_in    = settings.access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email, User.is_active == True))
    user   = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    user.last_login_at = datetime.now(timezone.utc)

    access_token   = create_access_token(user.id, {"org_id": str(user.organization_id), "role": user.role})
    refresh_raw    = create_refresh_token()
    refresh_hashed = hash_token(refresh_raw)

    rt = RefreshToken(
        user_id    = user.id,
        token_hash = refresh_hashed,
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(rt)
    await db.commit()

    return TokenResponse(
        access_token  = access_token,
        refresh_token = refresh_raw,
        expires_in    = settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked    == False,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=401, detail="Refresh token inválido ou expirado")

    rt.revoked = True

    result2 = await db.execute(select(User).where(User.id == rt.user_id, User.is_active == True))
    user = result2.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário inativo")

    access_token   = create_access_token(user.id, {"org_id": str(user.organization_id), "role": user.role})
    refresh_raw    = create_refresh_token()
    new_rt = RefreshToken(
        user_id    = user.id,
        token_hash = hash_token(refresh_raw),
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_rt)
    await db.commit()

    return TokenResponse(
        access_token  = access_token,
        refresh_token = refresh_raw,
        expires_in    = settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        await db.commit()
    return MessageResponse(message="Logout realizado com sucesso")


@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    result = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = result.scalar_one_or_none()
    return {
        "id": str(current_user.id),
        "organization_id": str(current_user.organization_id),
        "org_name": org.name if org else "Minha Empresa",
        "org_plan": org.plan if org else "free",
        "docs_limit": org.docs_limit if org else 500,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "last_login_at": str(current_user.last_login_at) if current_user.last_login_at else None,
        "created_at": str(current_user.created_at),
    }


@router.patch("/me/password", response_model=MessageResponse)
async def change_password(
    body: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    current_user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return MessageResponse(message="Senha alterada com sucesso")
