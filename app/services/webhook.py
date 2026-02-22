"""
FiscalSpy — Webhook Service
"""
from __future__ import annotations
import json, logging, uuid
from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import sign_webhook
from app.models.models import FiscalDocument, Webhook, WebhookDelivery

log = logging.getLogger(__name__)

def build_payload(event: str, document: FiscalDocument | None = None, extra: dict | None = None) -> dict:
    payload = {"event": event, "id": str(uuid.uuid4()), "created_at": datetime.now(timezone.utc).isoformat(), "data": extra or {}}
    if document:
        payload["data"] = {
            "document_id": str(document.id),
            "doc_type": str(document.doc_type),
            "chave_acesso": document.chave_acesso,
            "numero": document.numero,
            "serie": document.serie,
            "cnpj_emitente": document.cnpj_emitente,
            "razao_emitente": document.razao_emitente,
            "cnpj_destinatario": document.cnpj_destinatario,
            "valor_total": str(document.valor_total),
            "data_emissao": document.data_emissao.isoformat() if document.data_emissao else None,
            "status": str(document.status),
            **(extra or {}),
        }
    return payload

async def dispatch_event(db: AsyncSession, org_id: uuid.UUID, event: str, document: FiscalDocument | None = None, extra: dict | None = None) -> None:
    result = await db.execute(select(Webhook).where(Webhook.organization_id == org_id, Webhook.is_active == True))
    webhooks = result.scalars().all()
    for webhook in webhooks:
        if event not in (webhook.events or []):
            continue
        payload = build_payload(event, document, extra)
        delivery = WebhookDelivery(
            webhook_id=webhook.id, document_id=document.id if document else None,
            event=event, payload=payload, status="pending",
        )
        db.add(delivery)
    await db.flush()

async def deliver_webhook(delivery_id: uuid.UUID, db: AsyncSession) -> bool:
    result = await db.execute(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id).with_for_update(skip_locked=True))
    delivery = result.scalar_one_or_none()
    if not delivery: return False
    result2 = await db.execute(select(Webhook).where(Webhook.id == delivery.webhook_id))
    webhook = result2.scalar_one_or_none()
    if not webhook or not webhook.is_active:
        delivery.status = "failed"; delivery.error_message = "Webhook desativado"
        await db.commit(); return False

    payload_bytes = json.dumps(delivery.payload, ensure_ascii=False).encode()
    signature = sign_webhook(webhook.secret, payload_bytes)
    headers = {
        "Content-Type": "application/json",
        "X-FiscalSpy-Event": str(delivery.event),
        "X-FiscalSpy-Signature": signature,
        "X-FiscalSpy-Delivery": str(delivery.id),
        "User-Agent": "FiscalSpy-Webhooks/1.0",
    }
    delivery.attempt += 1
    success = False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(webhook.url, content=payload_bytes, headers=headers)
            delivery.response_code = resp.status_code
            delivery.response_body = resp.text[:500]
            success = 200 <= resp.status_code < 300
    except Exception as exc:
        delivery.error_message = str(exc)[:500]

    if success:
        delivery.status = "success"; delivery.delivered_at = datetime.now(timezone.utc)
        webhook.failure_count = 0; webhook.last_success_at = datetime.now(timezone.utc)
    else:
        webhook.failure_count += 1; webhook.last_failure_at = datetime.now(timezone.utc)
        delays = settings.webhook_retry_delays_list
        if delivery.attempt <= len(delays):
            delivery.status = "retrying"
            delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delays[delivery.attempt - 1])
        else:
            delivery.status = "failed"
        if webhook.failure_count >= 10:
            webhook.is_active = False

    await db.commit()
    return success
