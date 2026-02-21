"""
FiscalSpy — Background Workers (ARQ)
"""
from __future__ import annotations
import base64
import logging
from datetime import datetime, timezone
from uuid import UUID

from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.models import CNPJMonitor, Organization, WebhookDelivery
from app.services.document import upsert_document
from app.services.sefaz import SefazService
from app.services.webhook import deliver_webhook

log = logging.getLogger(__name__)


def redis_settings_from_url(url: str) -> RedisSettings:
    from urllib.parse import urlparse
    p = urlparse(url)
    return RedisSettings(
        host=p.hostname or "redis",
        port=p.port or 6379,
        password=p.password or None,
        database=int(p.path.lstrip("/") or 0),
    )


async def sync_cnpj(ctx: dict, monitor_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(CNPJMonitor).where(CNPJMonitor.id == UUID(monitor_id)))
        monitor = result.scalar_one_or_none()
        if not monitor or not monitor.is_active:
            return {"skipped": True}

        org_result = await db.execute(select(Organization).where(Organization.id == monitor.organization_id))
        org = org_result.scalar_one_or_none()
        if not org:
            return {"skipped": True, "error": "Organização não encontrada"}

        extra = org.extra or {}
        cert_bytes = base64.b64decode(org.cert_pfx_encrypted) if org.cert_pfx_encrypted else None

        svc = SefazService(
            ambiente=extra.get("sefaz_ambiente"),
            cert_pfx_bytes=cert_bytes,
            cert_password=org.cert_password_hash if cert_bytes else None,
            cnpj=monitor.cnpj,
            codigo_acesso=extra.get("sefaz_codigo_acesso"),
        )
        try:
            cnpj = monitor.cnpj.replace(".", "").replace("/", "").replace("-", "")
            if svc.auth_mode == "codigo_acesso":
                sefaz_result = await svc.distribuicao_dfe_codigo_acesso(
                    cnpj=cnpj,
                    codigo_acesso=extra.get("sefaz_codigo_acesso", ""),
                    ult_nsu="000000000000000",
                )
            else:
                sefaz_result = await svc.distribuicao_dfe(
                    cnpj=cnpj,
                    ult_nsu="000000000000000",
                )
            created = 0
            if sefaz_result.success:
                for sefaz_doc in sefaz_result.documents:
                    _, is_new = await upsert_document(db, monitor.organization_id, sefaz_doc)
                    if is_new:
                        created += 1
                await db.commit()

            monitor.last_sync_at = datetime.now(timezone.utc)
            monitor.sync_error = None if sefaz_result.success else sefaz_result.error
            await db.commit()
            return {"cnpj": monitor.cnpj, "new_docs": created, "success": sefaz_result.success}
        except Exception as exc:
            monitor.sync_error = str(exc)
            await db.commit()
            log.exception("sync_cnpj failed for %s", monitor.cnpj)
            return {"error": str(exc)}
        finally:
            await svc.close()


async def deliver_pending_webhooks(ctx: dict) -> dict:
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.status.in_(["pending", "retrying"]),
                (WebhookDelivery.next_retry_at == None) | (WebhookDelivery.next_retry_at <= now),
            ).limit(50)
        )
        deliveries = result.scalars().all()
        success_count = 0
        for delivery in deliveries:
            ok = await deliver_webhook(delivery.id, db)
            if ok:
                success_count += 1
        return {"processed": len(deliveries), "success": success_count}


async def send_alert_email_task(ctx: dict, to: str, subject: str, body: str) -> bool:
    import smtplib
    from email.mime.text import MIMEText
    try:
        msg = MIMEText(body, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        log.exception("Failed to send email to %s", to)
        return False


class WorkerSettings:
    functions = [sync_cnpj, deliver_pending_webhooks, send_alert_email_task]
    redis_settings = redis_settings_from_url(settings.redis_url)
    max_jobs = 10
    job_timeout = 120
    keep_result = 3600
