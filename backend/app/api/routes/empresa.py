import os
from datetime import timezone, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import get_db, get_current_empresa
from app.models.models import Empresa
from app.core.security import encrypt_aes
from app.core.config import settings

router = APIRouter()


class UpdateEmpresaRequest(BaseModel):
    nome: str


def _extrair_info_cert(pfx_bytes: bytes, senha: str) -> dict:
    """Extrai nome do titular e data de validade do .pfx."""
    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.hazmat.backends import default_backend
        _, cert, _ = pkcs12.load_key_and_certificates(
            pfx_bytes, senha.encode(), default_backend()
        )
        # Nome do titular (CN)
        cn = None
        for attr in cert.subject:
            if attr.oid.dotted_string == '2.5.4.3':
                cn = attr.value
                break

        # Data de validade — compatível com diferentes versões de cryptography
        try:
            validade = cert.not_valid_after_utc
        except AttributeError:
            validade = cert.not_valid_after.replace(tzinfo=timezone.utc)

        return {"nome_titular": cn, "validade": validade}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Certificado inválido ou senha incorreta: {str(e)}")


@router.get("/me")
async def get_empresa_me(empresa: Empresa = Depends(get_current_empresa)):
    return {
        "id": str(empresa.id),
        "nome": empresa.nome,
        "cnpj": empresa.cnpj,
        "status": empresa.status.value,
        "trial_expira_em": empresa.trial_expira_em.isoformat() if empresa.trial_expira_em else None,
        "plano_id": str(empresa.plano_id) if empresa.plano_id else None,
        "certificado_configurado": bool(
            empresa.certificado_path and os.path.exists(empresa.certificado_path)
        ),
        "nome_titular": empresa.certificado_titular or None,
        "validade": empresa.certificado_validade.isoformat() if empresa.certificado_validade else None,
    }


@router.put("/update")
async def update_empresa(
    data: UpdateEmpresaRequest,
    empresa: Empresa = Depends(get_current_empresa),
    db: AsyncSession = Depends(get_db),
):
    empresa.nome = data.nome
    await db.commit()
    return {"sucesso": True, "nome": empresa.nome}


@router.post("/upload-certificado")
async def upload_certificado(
    arquivo: UploadFile = File(...),
    senha: str = Form(...),
    empresa: Empresa = Depends(get_current_empresa),
    db: AsyncSession = Depends(get_db),
):
    if not arquivo.filename.lower().endswith('.pfx'):
        raise HTTPException(status_code=400, detail="Apenas arquivos .pfx são aceitos.")
    if not senha:
        raise HTTPException(status_code=400, detail="Senha do certificado é obrigatória.")

    content = await arquivo.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    # Valida .pfx e extrai informações
    info = _extrair_info_cert(content, senha)  # lança 400 se inválido

    # Salva o arquivo
    cert_dir = os.path.join(settings.CERT_STORAGE_PATH, str(empresa.id))
    os.makedirs(cert_dir, exist_ok=True)
    cert_path = os.path.join(cert_dir, "certificado.pfx")
    with open(cert_path, "wb") as f:
        f.write(content)

    # Salva no banco
    empresa.certificado_path = cert_path
    empresa.senha_certificado_criptografada = encrypt_aes(senha)
    empresa.certificado_titular = info["nome_titular"]
    empresa.certificado_validade = info["validade"]
    await db.commit()

    return {
        "sucesso": True,
        "mensagem": "Certificado enviado e validado com sucesso!",
        "nome_titular": info["nome_titular"],
        "validade": info["validade"].isoformat() if info["validade"] else None,
    }
