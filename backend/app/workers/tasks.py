import asyncio
from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.core.security import decrypt_aes


@celery_app.task(bind=True, max_retries=3)
def sincronizar_todas_empresas(self):
    """Main task: synchronize all active companies with SEFAZ"""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_sync_all())


async def _sync_all():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.core.config import settings
    from app.models.models import Empresa, EmpresaStatus, ControleNSU, Nota, NotaTipo, NotaModelo, NotaStatus
    from app.services.sefaz_service import SefazService

    DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # Get all active companies with certificate
        result = await db.execute(
            select(Empresa).where(
                Empresa.status.in_([EmpresaStatus.ativo, EmpresaStatus.trial]),
                Empresa.certificado_path.isnot(None)
            )
        )
        empresas = result.scalars().all()

        for empresa in empresas:
            try:
                await _sync_empresa(db, empresa)
            except Exception as e:
                print(f"[Worker] Erro ao sincronizar empresa {empresa.id}: {e}")

    await engine.dispose()


async def _sync_empresa(db, empresa):
    from sqlalchemy import select
    from app.models.models import ControleNSU, Nota, NotaTipo, NotaModelo, NotaStatus
    from app.services.sefaz_service import SefazService

    # Get NSU
    result = await db.execute(select(ControleNSU).where(ControleNSU.empresa_id == empresa.id))
    controle = result.scalar_one_or_none()
    ultimo_nsu = controle.ultimo_nsu if controle else 0

    cert_password = ""
    if empresa.senha_certificado_criptografada:
        cert_password = decrypt_aes(empresa.senha_certificado_criptografada)

    from app.services.ibge import UF_IBGE

    cuf = UF_IBGE.get(empresa.uf.upper())

    if not cuf:
        print(f"[Worker] UF inválida para empresa {empresa.id}")
        return

    sefaz = SefazService(empresa.certificado_path, cert_password)

    docs_salvos = 0
    ambiente = 1 if empresa.ambiente == "producao" else 2

    while True:

        dados = await sefaz.consultar_dfe(
            empresa.cnpj,
            ultimo_nsu,
            cuf=cuf,
            ambiente=ambiente
        )

        cstat = dados.get("cStat")

        # 🔴 Consumo indevido
        if cstat == "656":
            print("[Worker] Consumo indevido. Encerrando sincronização.")
            ultimo_nsu = dados.get("ultimo_nsu", ultimo_nsu)
            break
        
        # 🟡 Sem documentos
        if cstat == "137":
            print("[Worker] Nenhum documento novo.")
            ultimo_nsu = dados.get("ultimo_nsu", ultimo_nsu)
            break
        
        # 🟢 Documento disponível (fluxo normal)
        if cstat != "138":
            print(f"[Worker] cStat inesperado: {cstat}")
            break
        
        notas = dados.get("notas", [])
            
        max_nsu = dados.get("max_nsu", ultimo_nsu)

        if not notas:
            break

        for doc in notas:
            xml_content = doc.get("xml_content", "")
            nsu = doc.get("nsu", 0)

            nfe_data = sefaz._parse_nfe_xml(xml_content)
            if not nfe_data.get("chave"):
                continue

            result = await db.execute(
                select(Nota).where(
                    Nota.empresa_id == empresa.id,
                    Nota.chave == nfe_data["chave"]
                )
            )
            if result.scalar_one_or_none():
                continue

            tipo = NotaTipo.entrada
            if nfe_data.get("cnpj_emitente") == empresa.cnpj:
                tipo = NotaTipo.saida

            xml_path = await sefaz.save_xml(empresa.id, nfe_data["chave"], xml_content)

            nota = Nota(
                empresa_id=empresa.id,
                chave=nfe_data["chave"],
                modelo=NotaModelo.NFe if nfe_data.get("modelo") == "NFe" else NotaModelo.CTe,
                tipo=tipo,
                cnpj_emitente=nfe_data.get("cnpj_emitente"),
                cnpj_destinatario=nfe_data.get("cnpj_destinatario"),
                valor_total=nfe_data.get("valor_total"),
                data_emissao=nfe_data.get("data_emissao"),
                status=NotaStatus.autorizada,
                xml_path=xml_path,
                nsu=nsu,
            )

            db.add(nota)
            docs_salvos += 1

        ultimo_nsu = dados.get("ultimo_nsu", ultimo_nsu)

        if ultimo_nsu >= max_nsu:
            break

    novo_nsu = ultimo_nsu

    if controle:
        controle.ultimo_nsu = novo_nsu
        controle.ultima_sincronizacao = datetime.now(timezone.utc)
    else:
        from app.models.models import ControleNSU as NSU
        db.add(
            NSU(
                empresa_id=empresa.id,
                ultimo_nsu=novo_nsu,
                ultima_sincronizacao=datetime.now(timezone.utc)
            )
        )

    await db.commit()

    print(f"[Worker] Empresa {empresa.cnpj}: {docs_salvos} notas importadas, NSU={novo_nsu}")
