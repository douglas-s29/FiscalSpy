from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from app.db.database import get_db
from app.models.models import Empresa, Usuario, ControleNSU, EmpresaStatus, UserRole
from app.schemas.schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from app.core.security import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token, decode_token
)
from app.core.config import settings
from app.services.asaas_service import AsaasService

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check CNPJ uniqueness
    result = await db.execute(select(Empresa).where(Empresa.cnpj == data.cnpj))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado")

    # Check email uniqueness
    result = await db.execute(select(Usuario).where(Usuario.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Create empresa
    trial_expira = datetime.now(timezone.utc) + timedelta(days=settings.TRIAL_DAYS)
    empresa = Empresa(
        nome=data.nome_empresa,
        cnpj=data.cnpj,
        status=EmpresaStatus.trial,
        trial_expira_em=trial_expira,
    )
    db.add(empresa)
    await db.flush()

    # Create admin user
    usuario = Usuario(
        empresa_id=empresa.id,
        nome=data.nome_usuario,
        email=data.email,
        senha_hash=get_password_hash(data.senha),
        role=UserRole.admin,
        ativo=True,
    )
    db.add(usuario)

    # Create NSU control
    nsu = ControleNSU(empresa_id=empresa.id, ultimo_nsu=0)
    db.add(nsu)

    # Create Asaas customer
    try:
        asaas = AsaasService()
        customer_id = await asaas.criar_cliente(data.nome_empresa, data.cnpj, data.email)
        empresa.asaas_customer_id = customer_id
    except Exception:
        pass  # Don't fail registration if Asaas is unavailable

    await db.commit()
    await db.refresh(usuario)

    # Generate tokens
    access_token = create_access_token({"sub": usuario.id})
    refresh_token = create_refresh_token({"sub": usuario.id})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.email == data.email))
    usuario = result.scalar_one_or_none()

    if not usuario or not verify_password(data.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário inativo")

    # Check empresa status
    result = await db.execute(select(Empresa).where(Empresa.id == usuario.empresa_id))
    empresa = result.scalar_one_or_none()

    if empresa and empresa.status == EmpresaStatus.bloqueado:
        raise HTTPException(status_code=403, detail="Empresa bloqueada por inadimplência")

    access_token = create_access_token({"sub": usuario.id})
    refresh_token = create_refresh_token({"sub": usuario.id})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    from jose import JWTError
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    usuario = result.scalar_one_or_none()
    if not usuario or not usuario.ativo:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    access_token = create_access_token({"sub": usuario.id})
    refresh_token = create_refresh_token({"sub": usuario.id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
async def logout():
    # In a production system, add token to blacklist in Redis
    return {"message": "Logout realizado com sucesso"}
