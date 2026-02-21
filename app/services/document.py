"""
FiscalSpy — Document Service
"""
from __future__ import annotations
import logging, uuid
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Alert, FiscalDocument, Organization
from app.schemas.schemas import DocumentFilter
from app.services.sefaz import SefazDocument
from app.services.webhook import dispatch_event

log = logging.getLogger(__name__)

EVENTOS = {
    "novo":      "documento.novo",
    "cancelado": "documento.cancelado",
    "denegado":  "documento.denegado",
}

async def check_docs_limit(db: AsyncSession, org_id: uuid.UUID) -> None:
    """Raise if org has reached their plan's document limit."""
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        log.warning("check_docs_limit: organization %s not found", org_id)
        return

    count_result = await db.execute(
        select(func.count()).select_from(FiscalDocument).where(FiscalDocument.organization_id == org_id)
    )
    current_count = count_result.scalar_one()

    if current_count >= org.docs_limit:
        raise ValueError(f"Limite de documentos atingido ({org.docs_limit}). Faça upgrade do plano.")

async def upsert_document(db: AsyncSession, org_id: uuid.UUID, sefaz_doc: SefazDocument) -> tuple[FiscalDocument, bool]:
    result = await db.execute(select(FiscalDocument).where(
        FiscalDocument.organization_id == org_id,
        FiscalDocument.chave_acesso == sefaz_doc.chave_acesso,
    ))
    existing = result.scalar_one_or_none()
    created = existing is None

    if created:
        await check_docs_limit(db, org_id)
        doc = FiscalDocument(
            organization_id=org_id, doc_type=sefaz_doc.doc_type,
            chave_acesso=sefaz_doc.chave_acesso, numero=sefaz_doc.numero,
            serie=sefaz_doc.serie, modelo=sefaz_doc.modelo,
            cnpj_emitente=sefaz_doc.cnpj_emitente, razao_emitente=sefaz_doc.razao_emitente,
            ie_emitente=sefaz_doc.ie_emitente, uf_emitente=sefaz_doc.uf_emitente,
            municipio_emitente=sefaz_doc.municipio_emitente,
            cnpj_destinatario=sefaz_doc.cnpj_destinatario, cpf_destinatario=sefaz_doc.cpf_destinatario,
            razao_destinatario=sefaz_doc.razao_destinatario, uf_destinatario=sefaz_doc.uf_destinatario,
            valor_total=Decimal(str(sefaz_doc.valor_total)),
            valor_icms=Decimal(str(sefaz_doc.valor_icms)) if sefaz_doc.valor_icms else None,
            valor_ipi=Decimal(str(sefaz_doc.valor_ipi)) if sefaz_doc.valor_ipi else None,
            data_emissao=sefaz_doc.data_emissao, data_autorizacao=sefaz_doc.data_autorizacao,
            status=sefaz_doc.status, protocolo=sefaz_doc.protocolo,
            motivo_status=sefaz_doc.motivo_status, natureza_operacao=sefaz_doc.natureza_operacao,
            cfop=sefaz_doc.cfop, xml_raw=sefaz_doc.xml_raw, extra=sefaz_doc.extra,
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)
        await dispatch_event(db, org_id, "documento.novo", doc)
        await evaluate_alerts(db, org_id, doc)
    else:
        new_status = sefaz_doc.status
        if str(existing.status) != new_status:
            existing.status = new_status
            existing.protocolo = sefaz_doc.protocolo
            existing.motivo_status = sefaz_doc.motivo_status
            if new_status == "cancelada":
                existing.data_cancelamento = sefaz_doc.data_emissao
                await dispatch_event(db, org_id, "documento.cancelado", existing)
            elif new_status == "denegada":
                await dispatch_event(db, org_id, "documento.denegado", existing)
        doc = existing

    return doc, created

async def evaluate_alerts(db: AsyncSession, org_id: uuid.UUID, document: FiscalDocument) -> None:
    from datetime import datetime, timezone
    result = await db.execute(select(Alert).where(Alert.organization_id == org_id, Alert.is_active == True))
    alerts = result.scalars().all()
    for alert in alerts:
        triggered = False
        cond, val = alert.condition, alert.condition_value
        if cond == "novo_documento":
            triggered = True
        elif cond == "documento_cancelado":
            triggered = str(document.status) == "cancelada"
        elif cond == "valor_acima" and val:
            try: triggered = float(document.valor_total) > float(val)
            except: pass
        elif cond == "cnpj_especifico" and val:
            triggered = document.cnpj_emitente == val or document.cnpj_destinatario == val
        if triggered:
            alert.last_fired_at = datetime.now(timezone.utc)
            alert.fire_count += 1
            await dispatch_event(db, org_id, "alerta.disparado", document, {"alert_name": alert.name})
    await db.flush()

async def list_documents(db: AsyncSession, org_id: uuid.UUID, filters: DocumentFilter):
    from sqlalchemy import and_, func
    conditions = [FiscalDocument.organization_id == org_id]
    if filters.doc_type: conditions.append(FiscalDocument.doc_type == filters.doc_type)
    if filters.status:   conditions.append(FiscalDocument.status == filters.status)
    if filters.uf:       conditions.append(FiscalDocument.uf_emitente == filters.uf)
    if filters.cnpj:
        c = filters.cnpj.replace(".","").replace("/","").replace("-","")
        conditions.append((FiscalDocument.cnpj_emitente == c) | (FiscalDocument.cnpj_destinatario == c))
    if filters.data_inicio: conditions.append(FiscalDocument.data_emissao >= filters.data_inicio)
    if filters.data_fim:    conditions.append(FiscalDocument.data_emissao <= filters.data_fim)
    if filters.valor_min is not None: conditions.append(FiscalDocument.valor_total >= filters.valor_min)
    if filters.valor_max is not None: conditions.append(FiscalDocument.valor_total <= filters.valor_max)
    total = (await db.execute(select(func.count()).select_from(FiscalDocument).where(and_(*conditions)))).scalar_one()
    offset = (filters.page - 1) * filters.page_size
    items = (await db.execute(select(FiscalDocument).where(and_(*conditions)).order_by(FiscalDocument.data_emissao.desc()).offset(offset).limit(filters.page_size))).scalars().all()
    return total, items
