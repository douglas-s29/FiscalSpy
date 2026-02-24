from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.db.database import get_db
from app.models.models import Empresa, Assinatura, EmpresaStatus, AssinaturaStatus
from app.core.config import settings

router = APIRouter()


@router.post("/webhook")
async def asaas_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    asaas_access_token: Optional[str] = Header(None)
):
    # Validate token
    if asaas_access_token != settings.ASAAS_WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")

    payload = await request.json()
    event = payload.get("event")
    payment = payload.get("payment", {})

    if not event:
        return {"ok": True}

    subscription_id = payment.get("subscription")
    customer_id = payment.get("customer")

    # Find empresa by customer_id or subscription
    empresa = None

    if customer_id:
        result = await db.execute(
            select(Empresa).where(Empresa.asaas_customer_id == customer_id)
        )
        empresa = result.scalar_one_or_none()

    if not empresa and subscription_id:
        result = await db.execute(
            select(Assinatura).where(Assinatura.asaas_subscription_id == subscription_id)
        )
        assinatura = result.scalar_one_or_none()
        if assinatura:
            result = await db.execute(select(Empresa).where(Empresa.id == assinatura.empresa_id))
            empresa = result.scalar_one_or_none()

    if not empresa:
        return {"ok": True, "message": "Empresa não encontrada"}

    # Handle events
    if event == "PAYMENT_CONFIRMED" or event == "PAYMENT_RECEIVED":
        empresa.status = EmpresaStatus.ativo
        # Update assinatura
        if subscription_id:
            result = await db.execute(
                select(Assinatura).where(Assinatura.asaas_subscription_id == subscription_id)
            )
            assinatura = result.scalar_one_or_none()
            if assinatura:
                assinatura.status = AssinaturaStatus.ativa

    elif event == "PAYMENT_OVERDUE":
        empresa.status = EmpresaStatus.inadimplente

    elif event in ("PAYMENT_DELETED", "SUBSCRIPTION_DELETED"):
        empresa.status = EmpresaStatus.bloqueado
        if subscription_id:
            result = await db.execute(
                select(Assinatura).where(Assinatura.asaas_subscription_id == subscription_id)
            )
            assinatura = result.scalar_one_or_none()
            if assinatura:
                assinatura.status = AssinaturaStatus.cancelada

    await db.commit()
    return {"ok": True, "event": event}
