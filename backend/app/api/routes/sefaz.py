from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
import logging

from app.core.deps import get_db, get_current_empresa, require_active_empresa
from app.models.models import Empresa, ControleNSU, Nota, NotaModelo, NotaTipo, NotaStatus
from app.services.sefaz_service import consultar_sefaz
from app.core.security import decrypt_aes
from app.core.config import settings
from datetime import datetime, timezone

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/sincronizar")
async def sincronizar(
    empresa: Empresa = Depends(require_active_empresa),
    db: AsyncSession = Depends(get_db),
):
    if not empresa.certificado_path or not os.path.exists(empresa.certificado_path):
        raise HTTPException(status_code=400, detail="Certificado digital não configurado.")

    try:
        senha = decrypt_aes(empresa.senha_certificado_criptografada)
    except Exception:
        raise HTTPException(status_code=400, detail="Erro ao descriptografar senha do certificado.")

    result = await db.execute(select(ControleNSU).where(ControleNSU.empresa_id == empresa.id))
    controle = result.scalar_one_or_none()
    ultimo_nsu = controle.ultimo_nsu if controle else 0

    try:
        ambiente = 1 if settings.ENVIRONMENT == "production" else 2
        resultado = await consultar_sefaz(
            empresa_cnpj=empresa.cnpj,
            pfx_path=empresa.certificado_path,
            senha_pfx=senha,
            ultimo_nsu=ultimo_nsu,
            ambiente=ambiente,
        )
    except Exception as e:
        logger.error(f"Erro SEFAZ: {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao consultar SEFAZ: {str(e)}")

    # Log detalhado para debug
    logger.info(
        f"SEFAZ retorno | cStat={resultado.get('cStat')} | "
        f"xMotivo={resultado.get('xMotivo')} | "
        f"ultNSU={resultado.get('ultimo_nsu')} | "
        f"maxNSU={resultado.get('max_nsu')} | "
        f"notas={len(resultado.get('notas', []))}"
    )

    notas_salvas = 0
    for nota_data in resultado.get('notas', []):
        result_exist = await db.execute(
            select(Nota).where(Nota.empresa_id == empresa.id, Nota.chave == nota_data['chave'])
        )
        if result_exist.scalar_one_or_none():
            continue

        xml_path = None
        if nota_data.get('xml_content'):
            xml_dir = os.path.join(settings.XML_STORAGE_PATH, str(empresa.id))
            os.makedirs(xml_dir, exist_ok=True)
            xml_path = os.path.join(xml_dir, f"{nota_data['chave']}.xml")
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(nota_data['xml_content'])

        nota = Nota(
            empresa_id=empresa.id,
            chave=nota_data['chave'],
            modelo=NotaModelo.NFe if nota_data['modelo'] == 'NFe' else NotaModelo.CTe,
            tipo=NotaTipo.entrada if nota_data['tipo'] == 'entrada' else NotaTipo.saida,
            cnpj_emitente=nota_data.get('cnpj_emitente', ''),
            cnpj_destinatario=nota_data.get('cnpj_destinatario', ''),
            valor_total=nota_data.get('valor_total', 0),
            data_emissao=nota_data.get('data_emissao'),
            status=NotaStatus.autorizada,
            xml_path=xml_path,
            nsu=nota_data.get('nsu', 0),
        )
        db.add(nota)
        notas_salvas += 1

    novo_nsu = resultado.get('ultimo_nsu', ultimo_nsu)
    if controle:
        controle.ultimo_nsu = novo_nsu
        controle.ultima_sincronizacao = datetime.now(timezone.utc)
    else:
        controle = ControleNSU(
            empresa_id=empresa.id,
            ultimo_nsu=novo_nsu,
            ultima_sincronizacao=datetime.now(timezone.utc),
        )
        db.add(controle)

    await db.commit()

    return {
        "sucesso": True,
        "notas_importadas": notas_salvas,
        "ultimo_nsu": novo_nsu,
        "max_nsu": resultado.get('max_nsu', 0),
        "cStat": resultado.get('cStat'),
        "xMotivo": resultado.get('xMotivo'),
        "mensagem": f"{notas_salvas} notas importadas. NSU: {novo_nsu}/{resultado.get('max_nsu', 0)}",
    }


@router.get("/status")
async def status_sefaz(
    empresa: Empresa = Depends(get_current_empresa),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ControleNSU).where(ControleNSU.empresa_id == empresa.id))
    controle = result.scalar_one_or_none()
    return {
        "certificado_configurado": bool(
            empresa.certificado_path and os.path.exists(empresa.certificado_path)
        ),
        "ultimo_nsu": controle.ultimo_nsu if controle else 0,
        "ultima_sincronizacao": controle.ultima_sincronizacao.isoformat() if controle and controle.ultima_sincronizacao else None,
        "ambiente": "producao" if settings.ENVIRONMENT == "production" else "homologacao",
    }
