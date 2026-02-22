"""
FiscalSpy — API Routes: Monitors, Webhooks, Alerts
"""

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_org, get_current_user, require_admin
from app.db.session import get_db
from app.models.models import Alert, CNPJMonitor, Organization, User, Webhook, WebhookDelivery
from app.schemas.schemas import (
    AlertCreate,
    AlertOut,
    AlertUpdate,
    MessageResponse,
    MonitorCreate,
    MonitorOut,
    MonitorUpdate,
    WebhookCreate,
    WebhookDeliveryOut,
    WebhookOut,
    WebhookUpdate,
)

monitors_router = APIRouter(prefix="/monitors", tags=["Monitors"])


@monitors_router.get("", response_model=list[MonitorOut])
async def list_monitors(
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CNPJMonitor).where(CNPJMonitor.organization_id == org.id)
        .order_by(CNPJMonitor.created_at.desc())
    )
    return result.scalars().all()


@monitors_router.post("", response_model=MonitorOut, status_code=201)
async def create_monitor(
    body: MonitorCreate,
    org:  Organization = Depends(get_current_org),
    db:   AsyncSession = Depends(get_db),
    _:    User         = Depends(require_admin),
):
    existing = await db.execute(
        select(CNPJMonitor).where(
            CNPJMonitor.organization_id == org.id,
            CNPJMonitor.cnpj == body.cnpj,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="CNPJ já monitorado")

    monitor = CNPJMonitor(organization_id=org.id, **body.model_dump())
    db.add(monitor)
    await db.commit()
    await db.refresh(monitor)
    return monitor


@monitors_router.get("/{monitor_id}", response_model=MonitorOut)
async def get_monitor(
    monitor_id: UUID,
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CNPJMonitor).where(CNPJMonitor.id == monitor_id, CNPJMonitor.organization_id == org.id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Monitor não encontrado")
    return m


@monitors_router.patch("/{monitor_id}", response_model=MonitorOut)
async def update_monitor(
    monitor_id: UUID,
    body: MonitorUpdate,
    org:  Organization = Depends(get_current_org),
    db:   AsyncSession = Depends(get_db),
    _:    User         = Depends(require_admin),
):
    result = await db.execute(
        select(CNPJMonitor).where(CNPJMonitor.id == monitor_id, CNPJMonitor.organization_id == org.id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Monitor não encontrado")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(m, k, v)
    await db.commit()
    await db.refresh(m)
    return m


@monitors_router.delete("/{monitor_id}", response_model=MessageResponse)
async def delete_monitor(
    monitor_id: UUID,
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
    _:   User         = Depends(require_admin),
):
    result = await db.execute(
        select(CNPJMonitor).where(CNPJMonitor.id == monitor_id, CNPJMonitor.organization_id == org.id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Monitor não encontrado")
    await db.delete(m)
    await db.commit()
    return MessageResponse(message="Monitor removido")


@monitors_router.post("/{monitor_id}/sync", response_model=MessageResponse)
async def sync_monitor(
    monitor_id: UUID,
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CNPJMonitor).where(CNPJMonitor.id == monitor_id, CNPJMonitor.organization_id == org.id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Monitor não encontrado")

    try:
        from arq import create_pool
        from app.workers.main import redis_settings_from_url
        from app.core.config import settings
        pool = await create_pool(redis_settings_from_url(settings.redis_url))
        await pool.enqueue_job("sync_cnpj", str(m.id))
        await pool.aclose()
    except Exception as exc:
        import logging as _log
        _log.getLogger(__name__).error("Erro ao enfileirar sincronização para monitor %s: %s", monitor_id, exc)
        raise HTTPException(status_code=503, detail="Erro ao enfileirar sincronização. Tente novamente mais tarde.")

    return MessageResponse(message=f"Sincronização do CNPJ {m.cnpj} enfileirada")


webhooks_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@webhooks_router.get("", response_model=list[WebhookOut])
async def list_webhooks(
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Webhook).where(Webhook.organization_id == org.id).order_by(Webhook.created_at.desc())
    )
    return result.scalars().all()


@webhooks_router.post("", response_model=WebhookOut, status_code=201)
async def create_webhook(
    body: WebhookCreate,
    org:  Organization = Depends(get_current_org),
    db:   AsyncSession = Depends(get_db),
    _:    User         = Depends(require_admin),
):
    wh = Webhook(
        organization_id = org.id,
        name            = body.name,
        url             = body.url,
        secret          = secrets.token_hex(32),
        events          = body.events,
    )
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


@webhooks_router.get("/{webhook_id}", response_model=WebhookOut)
async def get_webhook(
    webhook_id: UUID,
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.organization_id == org.id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")
    return wh


@webhooks_router.patch("/{webhook_id}", response_model=WebhookOut)
async def update_webhook(
    webhook_id: UUID,
    body: WebhookUpdate,
    org:  Organization = Depends(get_current_org),
    db:   AsyncSession = Depends(get_db),
    _:    User         = Depends(require_admin),
):
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.organization_id == org.id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(wh, k, v)
    await db.commit()
    await db.refresh(wh)
    return wh


@webhooks_router.delete("/{webhook_id}", response_model=MessageResponse)
async def delete_webhook(
    webhook_id: UUID,
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
    _:   User         = Depends(require_admin),
):
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.organization_id == org.id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")
    await db.delete(wh)
    await db.commit()
    return MessageResponse(message="Webhook removido")


@webhooks_router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryOut])
async def list_deliveries(
    webhook_id: UUID,
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.organization_id == org.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Webhook não encontrado")

    deliveries = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(50)
    )
    return deliveries.scalars().all()


@webhooks_router.post("/{webhook_id}/rotate-secret", response_model=dict)
async def rotate_secret(
    webhook_id: UUID,
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
    _:   User         = Depends(require_admin),
):
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.organization_id == org.id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")
    wh.secret = secrets.token_hex(32)
    await db.commit()
    return {"secret": wh.secret}


alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])


@alerts_router.get("", response_model=list[AlertOut])
async def list_alerts(
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.organization_id == org.id).order_by(Alert.created_at.desc())
    )
    return result.scalars().all()


@alerts_router.post("", response_model=AlertOut, status_code=201)
async def create_alert(
    body: AlertCreate,
    org:  Organization = Depends(get_current_org),
    db:   AsyncSession = Depends(get_db),
    _:    User         = Depends(require_admin),
):
    alert = Alert(organization_id=org.id, **body.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@alerts_router.patch("/{alert_id}", response_model=AlertOut)
async def update_alert(
    alert_id: UUID,
    body: AlertUpdate,
    org:  Organization = Depends(get_current_org),
    db:   AsyncSession = Depends(get_db),
    _:    User         = Depends(require_admin),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.organization_id == org.id)
    )
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(a, k, v)
    await db.commit()
    await db.refresh(a)
    return a


@alerts_router.delete("/{alert_id}", response_model=MessageResponse)
async def delete_alert(
    alert_id: UUID,
    org: Organization = Depends(get_current_org),
    db:  AsyncSession = Depends(get_db),
    _:   User         = Depends(require_admin),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.organization_id == org.id)
    )
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    await db.delete(a)
    await db.commit()
    return MessageResponse(message="Alerta removido")
