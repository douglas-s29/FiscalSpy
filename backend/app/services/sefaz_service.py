import os
import gzip
import base64
import tempfile
from datetime import datetime
from typing import Optional
import xml.etree.ElementTree as ET

import httpx
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.backends import default_backend

from app.core.config import settings

SEFAZ_AN_PRODUCAO = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"
SEFAZ_AN_HOMOLOG  = "https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"


def _extrair_pem(pfx_path: str, senha: str) -> tuple[str, str]:
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()
    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        pfx_data, senha.encode(), default_backend()
    )
    cert_pem = certificate.public_bytes(Encoding.PEM)
    key_pem  = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())

    cert_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    cert_tmp.write(cert_pem); cert_tmp.flush()

    key_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    key_tmp.write(key_pem); key_tmp.flush()

    return cert_tmp.name, key_tmp.name


def _build_soap(cnpj: str, ultimo_nsu: int, ambiente: int, cuf: int) -> str:
    nsu = str(ultimo_nsu).zfill(15)
    cnpj = ''.join(filter(str.isdigit, cnpj))

    return f'''<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope 
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                    xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">

                    <soap:Header>
                        <nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
                            <cUF>{cuf}</cUF>
                            <versaoDados>1.01</versaoDados>
                        </nfeCabecMsg>
                    </soap:Header>

                    <soap:Body>
                        <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
                            <nfeDadosMsg>
                                <distDFeInt versao="1.01" xmlns="http://www.portalfiscal.inf.br/nfe">
                                    <tpAmb>{ambiente}</tpAmb>
                                    <cUFAutor>{cuf}</cUFAutor>
                                    <CNPJ>{cnpj}</CNPJ>
                                    <distNSU>
                                        <ultNSU>{nsu}</ultNSU>
                                    </distNSU>
                                </distDFeInt>
                            </nfeDadosMsg>
                        </nfeDistDFeInteresse>
                    </soap:Body>

                </soap:Envelope>'''

def _parse_nota(xml_str: str, empresa_cnpj: str) -> Optional[dict]:
    try:
        NS = 'http://www.portalfiscal.inf.br/nfe'
        root = ET.fromstring(xml_str)
        inf_nfe = root.find(f'.//{{{NS}}}infNFe')
        if inf_nfe is None:
            return None

        chave = inf_nfe.get('Id', '').replace('NFe', '')
        ide   = root.find(f'.//{{{NS}}}ide')
        emit  = root.find(f'.//{{{NS}}}emit')
        dest  = root.find(f'.//{{{NS}}}dest')
        total = root.find(f'.//{{{NS}}}ICMSTot')

        cnpj_emit = ''
        cnpj_dest = ''
        valor     = 0.0
        data_emis = None
        modelo    = 'NFe'

        if emit is not None:
            node = emit.find(f'{{{NS}}}CNPJ')
            if node is not None: cnpj_emit = node.text or ''

        if dest is not None:
            node = dest.find(f'{{{NS}}}CNPJ') or dest.find(f'{{{NS}}}CPF')
            if node is not None: cnpj_dest = node.text or ''

        if total is not None:
            node = total.find(f'{{{NS}}}vNF')
            if node is not None:
                try: valor = float(node.text)
                except: pass

        if ide is not None:
            demi = ide.find(f'{{{NS}}}dhEmi') or ide.find(f'{{{NS}}}dEmi')
            if demi is not None and demi.text:
                try: data_emis = datetime.fromisoformat(demi.text[:19])
                except: pass
            mod = ide.find(f'{{{NS}}}mod')
            if mod is not None:
                modelo = 'CTe' if mod.text == '57' else 'NFe'

        cnpj_limpo = empresa_cnpj.replace('.','').replace('/','').replace('-','')
        tipo = 'entrada' if cnpj_limpo in cnpj_dest else 'saida'

        return {
            'chave': chave, 'modelo': modelo, 'tipo': tipo,
            'cnpj_emitente': cnpj_emit, 'cnpj_destinatario': cnpj_dest,
            'valor_total': valor, 'data_emissao': data_emis, 'status': 'autorizada',
        }
    except Exception as e:
        print(f"[SEFAZ] Erro parse nota: {e}")
        return None


def _parse_response(xml_text: str, empresa_cnpj: str) -> dict:
    try:
        root = ET.fromstring(xml_text)
        NS = 'http://www.portalfiscal.inf.br/nfe'

        ret = root.find(f'.//{{{NS}}}retDistDFeInt')
        if ret is None:
            print(f"[SEFAZ] retDistDFeInt não encontrado no XML!")
            return {'notas': [], 'ultimo_nsu': 0, 'max_nsu': 0, 'cStat': '999', 'xMotivo': 'Tag retDistDFeInt não encontrada'}

        c_stat   = (ret.findtext(f'{{{NS}}}cStat') or '999')
        x_motivo = (ret.findtext(f'{{{NS}}}xMotivo') or '')
        ult_nsu  = int(ret.findtext(f'{{{NS}}}ultNSU') or 0)
        max_nsu  = int(ret.findtext(f'{{{NS}}}maxNSU') or 0)

        print(f"[SEFAZ] cStat={c_stat} | xMotivo={x_motivo} | ultNSU={ult_nsu} | maxNSU={max_nsu}")

        notas = []
        if c_stat in ('137', '138'):
            doc_zips = ret.findall(f'.//{{{NS}}}docZip')
            print(f"[SEFAZ] Documentos encontrados: {len(doc_zips)}")
            for doc_zip in doc_zips:
                nsu    = doc_zip.get('NSU', '0')
                schema = doc_zip.get('schema', '')
                print(f"[SEFAZ] docZip NSU={nsu} schema={schema}")
                try:
                    xml_bytes = gzip.decompress(base64.b64decode(doc_zip.text))
                    xml_str   = xml_bytes.decode('utf-8')
                    if any(s in schema for s in ['NFe', 'CTe', 'resNFe', 'resCTe', 'procNFe', 'resEvento']):
                        nota = _parse_nota(xml_str, empresa_cnpj)
                        if nota:
                            nota['nsu'] = int(nsu)
                            nota['xml_content'] = xml_str
                            notas.append(nota)
                            print(f"[SEFAZ] Nota parseada: chave={nota['chave']} tipo={nota['tipo']} valor={nota['valor_total']}")
                        else:
                            print(f"[SEFAZ] Documento NSU={nsu} schema={schema} não retornou nota (pode ser evento/resumo)")
                except Exception as e:
                    print(f"[SEFAZ] Erro descomprimindo NSU={nsu}: {e}")
                    continue

        return {'notas': notas, 'ultimo_nsu': ult_nsu, 'max_nsu': max_nsu,
                'cStat': c_stat, 'xMotivo': x_motivo}
    except Exception as e:
        print(f"[SEFAZ] Erro parse response: {e}")
        return {'notas': [], 'ultimo_nsu': 0, 'max_nsu': 0, 'cStat': '999', 'xMotivo': str(e)}


async def consultar_sefaz(
    empresa_cnpj: str,
    pfx_path: str,
    senha_pfx: str,
    ultimo_nsu: int = 0,
    ambiente: int = 2,
    cuf: int = 53,
) -> dict:
    url = SEFAZ_AN_PRODUCAO if ambiente == 1 else SEFAZ_AN_HOMOLOG
    cert_file = key_file = None
    try:
        print(f"[SEFAZ] Consultando | CNPJ={empresa_cnpj} | NSU={ultimo_nsu} | Ambiente={'PRODUCAO' if ambiente==1 else 'HOMOLOG'} | URL={url}")
        cert_file, key_file = _extrair_pem(pfx_path, senha_pfx)
        # Debug: mostrar CNPJ do certificado
        from cryptography.hazmat.primitives.serialization import pkcs12 as _p
        _, _c, _ = _p.load_key_and_certificates(open(pfx_path,'rb').read(), senha_pfx.encode(), None)
        print(f"[SEFAZ] CNPJ no certificado: {_c.subject}")
        print(f"[SEFAZ] Certificado extraído OK")

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': '"http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"',
        }
        soap = _build_soap(empresa_cnpj, ultimo_nsu, ambiente, cuf)
        print(f"[SEFAZ] SOAP ENVIADO: {soap}")
        print(f"[SEFAZ] SOAP montado, enviando requisição...")

        async with httpx.AsyncClient(
            cert=(cert_file, key_file),
            verify=True,
            timeout=60.0,
        ) as client:
            resp = await client.post(url, content=soap.encode('utf-8'), headers=headers)
            print(f"[SEFAZ] HTTP status={resp.status_code}")
            print(f"[SEFAZ] Resposta (primeiros 1500 chars): {resp.text[:1500]}")
            resp.raise_for_status()

        return _parse_response(resp.text, empresa_cnpj)

    except httpx.HTTPStatusError as e:
        print(f"[SEFAZ] HTTP error: {e.response.status_code} - {e.response.text[:500]}")
        raise Exception(f"HTTP {e.response.status_code}: {e.response.text[:300]}")
    except Exception as e:
        print(f"[SEFAZ] Exceção: {type(e).__name__}: {e}")
        raise
    finally:
        for f in [cert_file, key_file]:
            if f and os.path.exists(f):
                try: os.unlink(f)
                except: pass
