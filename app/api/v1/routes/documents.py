"""
FiscalSpy — API Routes: Documents
"""

import base64
from datetime import datetime, time, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_org, get_current_user
from app.db.session import get_db
from app.models.models import FiscalDocument, Organization, User
from app.schemas.schemas import (
    ChaveConsultaRequest,
    CNPJConsultaRequest,
    DocumentFilter,
    DocumentListOut,
    DocumentOut,
    ManifestacaoRequest,
    MessageResponse,
)
from app.services.document import list_documents, upsert_document
from app.services.sefaz import NfseService, SefazService
from app.services.webhook import dispatch_event


router = APIRouter(prefix="/documents", tags=["Documents"])


def _clean_cnpj(cnpj: str) -> str:
    return cnpj.replace(".", "").replace("/", "").replace("-", "")


def _build_sefaz_service(org: Organization, cnpj: str | None = None) -> tuple[SefazService, bytes | None, dict]:
    extra = org.extra or {}
    cert_bytes = base64.b64decode(org.cert_pfx_encrypted) if org.cert_pfx_encrypted else None
    service = SefazService(
        ambiente=extra.get("sefaz_ambiente"),
        cert_pfx_bytes=cert_bytes,
        cert_password=org.cert_password_hash if cert_bytes else None,
        cnpj=cnpj,
        codigo_acesso=extra.get("sefaz_codigo_acesso"),
    )
    return service, cert_bytes, extra


@router.get("", response_model=DocumentListOut)
async def get_documents(
    doc_type: str | None = Query(None),
    status: str | None = Query(None),
    uf: str | None = Query(None),
    cnpj: str | None = Query(None),
    data_inicio: str | None = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: str | None = Query(None, description="Data final (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    parsed_inicio = None
    parsed_fim = None
    try:
        if data_inicio:
            parsed_inicio = datetime.fromisoformat(data_inicio).replace(hour=0, minute=0, second=0, microsecond=0)
            if parsed_inicio.tzinfo is None:
                parsed_inicio = parsed_inicio.replace(tzinfo=timezone.utc)
        if data_fim:
            fim_base = datetime.fromisoformat(data_fim)
            parsed_fim = datetime.combine(fim_base.date(), time.max).replace(tzinfo=fim_base.tzinfo or timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Datas inválidas. Use o formato YYYY-MM-DD") from exc

    filters = DocumentFilter(
        doc_type=doc_type,
        status=status,
        uf=uf,
        cnpj=cnpj,
        data_inicio=parsed_inicio,
        data_fim=parsed_fim,
        page=page,
        page_size=page_size,
    )
    total, items = await list_documents(db, org.id, filters)
    return DocumentListOut(total=total, page=page, page_size=page_size, items=items)


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FiscalDocument).where(
            FiscalDocument.id == document_id,
            FiscalDocument.organization_id == org.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return doc


@router.get("/{document_id}/xml", response_class=PlainTextResponse)
async def get_document_xml(
    document_id: UUID,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FiscalDocument).where(
            FiscalDocument.id == document_id,
            FiscalDocument.organization_id == org.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if not doc.xml_raw:
        raise HTTPException(status_code=404, detail="XML não disponível")
    return PlainTextResponse(content=doc.xml_raw, media_type="application/xml")


@router.post("/consulta/chave", response_model=DocumentOut)
async def consulta_por_chave(
    body: ChaveConsultaRequest,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Consulta NF-e na SEFAZ por chave de acesso e salva no banco."""
    svc, _, _ = _build_sefaz_service(org)
    result = await svc.consulta_nfe_chave(body.chave_acesso)
    await svc.close()

    if not result.success or not result.documents:
        raise HTTPException(status_code=422, detail=result.error or "Documento não encontrado na SEFAZ")

    try:
        doc, _ = await upsert_document(db, org.id, result.documents[0])
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    await db.commit()
    return doc


@router.post("/consulta/cnpj", response_model=DocumentListOut)
async def consulta_por_cnpj(
    body: CNPJConsultaRequest,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Consulta documentos fiscais pelo CNPJ conforme modo configurado na organização."""
    cnpj = _clean_cnpj(body.cnpj)
    svc, cert_bytes, extra = _build_sefaz_service(org, cnpj=cnpj)

    if svc.auth_mode == "codigo_acesso":
        result = await svc.distribuicao_dfe_codigo_acesso(
            cnpj=cnpj,
            codigo_acesso=extra.get("sefaz_codigo_acesso", ""),
        )
    else:
        result = await svc.distribuicao_dfe(cnpj=cnpj)
    await svc.close()

    if not result.success:
        raise HTTPException(status_code=422, detail=result.error or "Erro na consulta SEFAZ")

    docs = result.documents
    if body.doc_type in {"nfe", "cte"}:
        docs = [d for d in docs if d.doc_type == body.doc_type]

    range_start = body.data_inicio.replace(tzinfo=body.data_inicio.tzinfo or timezone.utc) if body.data_inicio else None
    range_end = body.data_fim.replace(tzinfo=body.data_fim.tzinfo or timezone.utc) if body.data_fim else None

    def in_range(doc_dt: datetime) -> bool:
        dt = doc_dt if doc_dt.tzinfo else doc_dt.replace(tzinfo=timezone.utc)
        if range_start and dt < range_start:
            return False
        if range_end and dt > range_end:
            return False
        return True

    docs = [d for d in docs if in_range(d.data_emissao)]

    if body.doc_type in {None, "nfse"}:
        nfse_service = NfseService(cert_pfx_bytes=cert_bytes, cert_password=org.cert_password_hash or "")
        nfse_result = await nfse_service.consulta_nfse_cnpj(cnpj)
        if nfse_result.success:
            docs.extend([d for d in nfse_result.documents if in_range(d.data_emissao)])

    saved = []
    for sefaz_doc in docs:
        try:
            doc, _ = await upsert_document(db, org.id, sefaz_doc)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        saved.append(doc)

    await db.commit()
    return DocumentListOut(total=len(saved), page=1, page_size=len(saved), items=saved)


@router.post("/manifestacao", response_model=MessageResponse)
async def enviar_manifestacao(
    body: ManifestacaoRequest,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
):
    """Envia manifestação do destinatário para a SEFAZ."""
    result = await db.execute(
        select(FiscalDocument).where(
            FiscalDocument.id == body.document_id,
            FiscalDocument.organization_id == org.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if not org.cnpj:
        raise HTTPException(status_code=400, detail="CNPJ da organização não configurado")

    svc, _, _ = _build_sefaz_service(org, cnpj=org.cnpj)
    sefaz_r = await svc.enviar_manifestacao(
        cnpj=org.cnpj.replace(".", "").replace("/", "").replace("-", ""),
        chave=doc.chave_acesso,
        tipo=body.tipo,
        justificativa=body.justificativa,
    )
    await svc.close()

    if not sefaz_r.get("success"):
        raise HTTPException(
            status_code=422,
            detail=f"SEFAZ rejeitou manifestação: {sefaz_r.get('xMotivo')}",
        )

    doc.manifestacao = body.tipo
    doc.manifestacao_at = datetime.now(timezone.utc)

    await dispatch_event(db, org.id, "manifestacao.enviada", doc, {"tipo": body.tipo})
    await db.commit()

    return MessageResponse(
        message=f"Manifestação enviada. Protocolo: {sefaz_r.get('nProt', '-')}"
    )
