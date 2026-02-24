from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.db.database import get_db
from app.models.models import Usuario, Empresa, EmpresaStatus
from app.core.security import decode_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.ativo:
        raise credentials_exception
    return user


async def get_current_empresa(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Empresa:
    result = await db.execute(select(Empresa).where(Empresa.id == current_user.empresa_id))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa


async def require_active_empresa(
    empresa: Empresa = Depends(get_current_empresa),
) -> Empresa:
    from datetime import datetime, timezone
    
    if empresa.status == EmpresaStatus.bloqueado:
        raise HTTPException(status_code=403, detail="Empresa bloqueada por inadimplência")
    
    if empresa.status == EmpresaStatus.inadimplente:
        raise HTTPException(status_code=402, detail="Pagamento pendente. Por favor, regularize sua assinatura.")
    
    if empresa.status == EmpresaStatus.trial:
        if empresa.trial_expira_em and empresa.trial_expira_em < datetime.now(timezone.utc):
            raise HTTPException(status_code=402, detail="Período trial expirado. Por favor, assine um plano.")
    
    return empresa


async def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return current_user
