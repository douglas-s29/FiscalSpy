import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Organization, User

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer  = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_access_token(subject: str | UUID, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "exp": expire, "type": "access", **(extra or {})}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("Wrong token type")
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def sign_webhook(secret: str, payload: bytes) -> str:
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={sig}"

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    result  = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user    = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user

async def get_current_org(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id, Organization.is_active == True)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organização inativa")
    return org

def require_role(*roles: str):
    async def _check(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão insuficiente. Requerido: {list(roles)}",
            )
        return current_user
    return _check

require_admin  = require_role("owner", "admin")
require_owner  = require_role("owner")
require_member = require_role("owner", "admin", "member")
