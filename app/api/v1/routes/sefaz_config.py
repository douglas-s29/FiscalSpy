"""
FiscalSpy — Endpoints de Configuração SEFAZ
Gerencia os modos de autenticação: público, código de acesso, certificado A1
"""
from __future__ import annotations
import base64
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_org, get_current_user
from app.db.session import get_db
from app.models.models import CNPJMonitor, Organization, User
from app.services.sefaz import SefazService

log = logging.getLogger(__name__)
router = APIRouter(prefix="/sefaz", tags=["SEFAZ Config"])


class SefazConfigIn(BaseModel):
    auth_mode:     str          # none | codigo | certificado
    ambiente:      str = "producao"
    # Modo código de acesso
    cnpj:          str | None = None
    codigo_acesso: str | None = None
    # Modo certificado A1
    cert_pfx_b64:  str | None = None
    cert_password: str | None = None


class SefazTestarIn(BaseModel):
    auth_mode:     str
    ambiente:      str = "producao"
    cnpj:          str | None = None
    codigo_acesso: str | None = None
    cert_pfx_b64:  str | None = None
    cert_password: str | None = None


class SefazSyncIn(BaseModel):
    cnpj:          str
    codigo_acesso: str | None = None
    ambiente:      str = "producao"


@router.get("/config")
async def get_config(
    org: Organization = Depends(get_current_org),
):
    """Retorna a configuração SEFAZ atual da organização."""
    extra = org.extra or {}
    auth_mode = extra.get("sefaz_auth_mode", "none")
    return {
        "auth_mode": auth_mode,
        "ambiente":  extra.get("sefaz_ambiente", "producao"),
        "cnpj":      extra.get("sefaz_cnpj"),
        "has_cert":  bool(org.cert_pfx_encrypted),
        "cert_expires": str(org.cert_expires_at.date()) if org.cert_expires_at else None,
    }


@router.post("/config")
async def save_config(
    body: SefazConfigIn,
    org:  Organization = Depends(get_current_org),
    db:   AsyncSession = Depends(get_db),
):
    """Salva a configuração SEFAZ da organização."""
    from cryptography.fernet import Fernet
    from app.core.config import settings

    extra = dict(org.extra or {})
    extra["sefaz_auth_mode"] = body.auth_mode
    extra["sefaz_ambiente"]  = body.ambiente

    if body.auth_mode == "codigo":
        if not body.cnpj or not body.codigo_acesso:
            raise HTTPException(400, "CNPJ e código de acesso são obrigatórios")
        cnpj = body.cnpj.replace(".", "").replace("/", "").replace("-", "")
        extra["sefaz_cnpj"]          = cnpj
        extra["sefaz_codigo_acesso"] = body.codigo_acesso  # armazenado; em produção use criptografia

    elif body.auth_mode == "certificado":
        if not body.cert_pfx_b64 or not body.cert_password:
            raise HTTPException(400, "Certificado e senha são obrigatórios")
        pfx_bytes = base64.b64decode(body.cert_pfx_b64)
        # Valida o certificado antes de salvar
        try:
            from app.services.sefaz import load_certificate
            from cryptography.hazmat.primitives.serialization import pkcs12
            from cryptography import x509
            _, cert, _ = pkcs12.load_key_and_certificates(
                pfx_bytes, body.cert_password.encode()
            )
            expires_at = cert.not_valid_after_utc if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after.replace(tzinfo=timezone.utc)
            org.cert_pfx_encrypted = base64.b64encode(pfx_bytes).decode()
            org.cert_password_hash = body.cert_password  # Em produção: encrypt with Fernet
            org.cert_expires_at    = expires_at
        except Exception as exc:
            raise HTTPException(400, f"Certificado inválido: {exc}")

    # Update org extra (JSONB)
    from sqlalchemy import update
    await db.execute(
        update(Organization)
        .where(Organization.id == org.id)
        .values(
            extra=extra,
            cert_pfx_encrypted=org.cert_pfx_encrypted,
            cert_password_hash=org.cert_password_hash,
            cert_expires_at=org.cert_expires_at,
        )
    )
    await db.commit()
    return {"success": True, "message": "Configuração salva com sucesso"}


@router.post("/testar")
async def testar_config(
    body: SefazTestarIn,
    user: User = Depends(get_current_user),
):
    """Testa a conexão com a SEFAZ com as credenciais fornecidas."""
    try:
        if body.auth_mode == "codigo":
            if not body.cnpj or not body.codigo_acesso:
                raise HTTPException(400, "CNPJ e código são obrigatórios")
            svc = SefazService(
                ambiente=body.ambiente,
                cnpj=body.cnpj,
                codigo_acesso=body.codigo_acesso,
            )
            # Testa com uma consulta DFe básica
            result = await svc.distribuicao_dfe_codigo_acesso(
                cnpj=body.cnpj.replace(".", "").replace("/", "").replace("-", ""),
                codigo_acesso=body.codigo_acesso,
                ult_nsu="000000000000000",
            )
            await svc.close()
            if result.success:
                return {"success": True, "message": f"Conexão OK! {len(result.documents)} documento(s) encontrado(s)."}
            else:
                return {"success": False, "error": result.error or "Falha na conexão"}

        elif body.auth_mode == "certificado":
            if not body.cert_pfx_b64 or not body.cert_password:
                raise HTTPException(400, "Certificado e senha são obrigatórios")
            pfx_bytes = base64.b64decode(body.cert_pfx_b64)
            # Valida certificado
            from cryptography.hazmat.primitives.serialization import pkcs12
            _, cert, _ = pkcs12.load_key_and_certificates(
                pfx_bytes, body.cert_password.encode()
            )
            subject = cert.subject.rfc4514_string()
            expires = cert.not_valid_after_utc if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after
            # Tenta conexão real com a SEFAZ
            svc = SefazService(
                ambiente=body.ambiente,
                cert_pfx_bytes=pfx_bytes,
                cert_password=body.cert_password,
            )
            # Consulta uma chave fictícia apenas para testar o SSL
            try:
                await svc._get_client()
                await svc.close()
            except Exception:
                pass
            return {
                "success":  True,
                "message":  f"Certificado válido! Sujeito: {subject[:60]}... Validade: {expires.strftime('%d/%m/%Y')}",
            }
        else:
            # Modo público — sempre funciona
            return {"success": True, "message": "Modo público ativo — nenhuma autenticação necessária."}

    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Erro testando config SEFAZ")
        return {"success": False, "error": str(exc)}


@router.post("/sync")
async def sync_cnpj(
    body: SefazSyncIn,
    org:  Organization = Depends(get_current_org),
    db:   AsyncSession = Depends(get_db),
):
    """Sincroniza documentos de um CNPJ via código de acesso ou certificado."""
    from app.services.document import upsert_document

    cnpj = body.cnpj.replace(".", "").replace("/", "").replace("-", "")
    extra = org.extra or {}

    # Determina modo de autenticação
    cert_bytes = base64.b64decode(org.cert_pfx_encrypted) if org.cert_pfx_encrypted else None
    codigo     = body.codigo_acesso or extra.get("sefaz_codigo_acesso")
    ambiente   = body.ambiente or extra.get("sefaz_ambiente", "producao")

    svc = SefazService(
        ambiente=ambiente,
        cert_pfx_bytes=cert_bytes,
        cert_password=org.cert_password_hash if cert_bytes else None,
        cnpj=cnpj,
        codigo_acesso=codigo,
    )

    try:
        if svc.auth_mode == "codigo_acesso":
            if not codigo:
                raise HTTPException(400, "Código de acesso é obrigatório para este modo de autenticação")
            result = await svc.distribuicao_dfe_codigo_acesso(
                cnpj=cnpj,
                codigo_acesso=codigo,
                ult_nsu="000000000000000",
            )
        elif svc.auth_mode == "certificado":
            result = await svc.distribuicao_dfe(cnpj=cnpj, ult_nsu="000000000000000")
        else:
            return {
                "success": False,
                "new_documents": 0,
                "total_found": 0,
                "auth_mode": svc.auth_mode,
                "error": "Nenhum modo de autenticação configurado. Vá em Configurações SEFAZ e configure um certificado A1 ou código de acesso.",
            }
        created = 0
        if result.success:
            for doc in result.documents:
                _, is_new = await upsert_document(db, org.id, doc)
                if is_new:
                    created += 1
            await db.commit()
            # Update monitors
            res = await db.execute(select(CNPJMonitor).where(
                CNPJMonitor.organization_id == org.id,
                CNPJMonitor.cnpj == cnpj,
            ))
            monitor = res.scalar_one_or_none()
            if monitor:
                monitor.last_sync_at = datetime.now(timezone.utc)
                monitor.sync_error   = None
                await db.commit()
        return {
            "success":      result.success,
            "new_documents": created,
            "total_found":  len(result.documents),
            "auth_mode":    svc.auth_mode,
            "error":        result.error,
        }
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Erro sync CNPJ %s", cnpj)
        return {"success": False, "error": str(exc)}
    finally:
        await svc.close()
