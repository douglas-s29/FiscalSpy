from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.database import get_db
from app.models.models import Plano, Assinatura, Empresa, EmpresaStatus
from app.schemas.schemas import PlanoResponse, CriarAssinaturaRequest, AssinaturaResponse
from app.core.deps import get_current_user, get_current_empresa, require_admin
from app.models.models import Usuario
from app.services.asaas_service import AsaasService

router = APIRouter()


@router.get("/planos", response_model=List[PlanoResponse])
async def listar_planos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plano).where(Plano.ativo == True))
    return result.scalars().all()


@router.post("/assinatura/criar", response_model=AssinaturaResponse)
async def criar_assinatura(
    data: CriarAssinaturaRequest,
    current_user: Usuario = Depends(get_current_user),
    empresa: Empresa = Depends(get_current_empresa),
    db: AsyncSession = Depends(get_db)
):
    # Get plano
    result = await db.execute(select(Plano).where(Plano.id == data.plano_id))
    plano = result.scalar_one_or_none()
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    if not empresa.asaas_customer_id:
        raise HTTPException(status_code=400, detail="Cliente Asaas não configurado")

    # Create subscription in Asaas
    try:
        asaas = AsaasService()
        subscription = await asaas.criar_assinatura(
            customer_id=empresa.asaas_customer_id,
            valor=float(plano.valor_mensal),
            ciclo=data.ciclo,
            descricao=f"FiscalSpy - Plano {plano.nome}"
        )
        asaas_sub_id = subscription.get("id")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao criar assinatura: {str(e)}")

    # Save to DB
    assinatura = Assinatura(
        empresa_id=empresa.id,
        asaas_subscription_id=asaas_sub_id,
        status="pendente",
    )
    db.add(assinatura)
    empresa.plano_id = plano.id
    await db.commit()
    await db.refresh(assinatura)
    return assinatura


@router.get("/assinatura/status")
async def status_assinatura(
    empresa: Empresa = Depends(get_current_empresa),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Assinatura)
        .where(Assinatura.empresa_id == empresa.id)
        .order_by(Assinatura.criado_em.desc())
    )
    assinatura = result.scalar_one_or_none()

    return {
        "empresa_status": empresa.status,
        "trial_expira_em": empresa.trial_expira_em,
        "assinatura": assinatura,
    }
