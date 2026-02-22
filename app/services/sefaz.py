"""
FiscalSpy — SEFAZ Multi-Modal Service
Suporta todos os tipos de CNPJ:
  - MEI / sem certificado: consulta pública por chave de acesso
  - Código de acesso e-CAC: para MEI/ME com código gerado no portal
  - Certificado A1 (.pfx): acesso completo, DFe, manifestação
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import uuid
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import xmltodict
from lxml import etree
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

log = logging.getLogger(__name__)

ENDPOINTS = {
    "homologacao": {
        "nfe_consulta_chave":    "https://hom.nfe.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx",
        "nfe_distribuicao_dfe":  "https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
        "nfe_manifestacao":      "https://hom.nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
        "cte_consulta":          "https://hom.cte.fazenda.gov.br/CTeConsultaProtocolo/CTeConsultaProtocolo.asmx",
        "cte_distribuicao":      "https://hom.cte.fazenda.gov.br/CTeDistribuicaoDFe/CTeDistribuicaoDFe.asmx",
    },
    "producao": {
        "nfe_consulta_chave":    "https://nfe.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx",
        "nfe_distribuicao_dfe":  "https://nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
        "nfe_manifestacao":      "https://nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
        "cte_consulta":          "https://cte.fazenda.gov.br/CTeConsultaProtocolo/CTeConsultaProtocolo.asmx",
        "cte_distribuicao":      "https://cte.fazenda.gov.br/CTeDistribuicaoDFe/CTeDistribuicaoDFe.asmx",
    },
}

SEFAZ_STATUS_MAP = {
    "100": "autorizada", "101": "cancelada",  "110": "denegada",
    "135": "cancelada",  "155": "cancelada",  "301": "denegada",
    "302": "denegada",   "136": "autorizada",
}

MANIFESTACAO_DESC = {
    "210200": "Confirmação da Operação",
    "210210": "Ciência da Operação",
    "210220": "Desconhecimento da Operação",
    "210240": "Operação não Realizada",
}

AUTH_NONE        = "none"
AUTH_CODIGO      = "codigo_acesso"
AUTH_CERTIFICADO = "certificado"


@dataclass
class SefazDocument:
    doc_type:           str
    chave_acesso:       str
    numero:             str
    serie:              str
    modelo:             str
    cnpj_emitente:      str
    razao_emitente:     str | None
    ie_emitente:        str | None
    uf_emitente:        str | None
    municipio_emitente: str | None
    cnpj_destinatario:  str | None
    cpf_destinatario:   str | None
    razao_destinatario: str | None
    uf_destinatario:    str | None
    valor_total:        float
    valor_icms:         float | None
    valor_ipi:          float | None
    data_emissao:       datetime
    data_autorizacao:   datetime | None
    status:             str
    protocolo:          str | None
    motivo_status:      str | None
    natureza_operacao:  str | None
    cfop:               str | None
    xml_raw:            str | None
    extra:              dict | None = None


@dataclass
class SefazResult:
    success:      bool
    documents:    list[SefazDocument] = field(default_factory=list)
    error:        str | None = None
    raw_response: str | None = None
    auth_mode:    str = AUTH_NONE


def load_certificate(pfx_data: bytes, password: str) -> tuple[bytes, bytes]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization import pkcs12
    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        pfx_data, password.encode() if password else None
    )
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
    key_pem  = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return cert_pem, key_pem


class SefazService:
    """
    Serviço multi-modal de integração com a SEFAZ.
    Modos: AUTH_NONE (consulta pública), AUTH_CODIGO (e-CAC), AUTH_CERTIFICADO (A1)
    """

    def __init__(
        self,
        ambiente:        str | None = None,
        cert_pfx_bytes:  bytes | None = None,
        cert_password:   str | None = None,
        cert_path:       str | None = None,
        cnpj:            str | None = None,
        codigo_acesso:   str | None = None,
    ):
        self.ambiente      = ambiente or settings.sefaz_ambiente
        self.endpoints     = ENDPOINTS[self.ambiente]
        self._client: httpx.AsyncClient | None = None
        self._cert_bytes   = cert_pfx_bytes
        self._cert_pass    = cert_password or ""
        self._cert_path    = cert_path or settings.sefaz_cert_path
        self._cnpj         = (cnpj or "").replace(".", "").replace("/", "").replace("-", "")
        self._codigo       = codigo_acesso or ""
        self.auth_mode = self._detect_auth_mode()
        log.info("SefazService iniciado em modo: %s ambiente: %s", self.auth_mode, self.ambiente)

    def _detect_auth_mode(self) -> str:
        if self._cert_bytes:
            return AUTH_CERTIFICADO
        if self._cert_path and Path(self._cert_path).exists():
            return AUTH_CERTIFICADO
        if self._cnpj and self._codigo:
            return AUTH_CODIGO
        return AUTH_NONE

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            kwargs: dict[str, Any] = {"timeout": settings.sefaz_timeout, "verify": True}
            if self.auth_mode == AUTH_CERTIFICADO:
                import tempfile, os
                pfx_data = self._cert_bytes or Path(self._cert_path).read_bytes()
                cert_pem, key_pem = load_certificate(pfx_data, self._cert_pass)
                tc = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
                tk = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
                tc.write(cert_pem); tc.flush(); tc.close()
                tk.write(key_pem);  tk.flush(); tk.close()
                kwargs["cert"] = (tc.name, tk.name)
            self._client = httpx.AsyncClient(**kwargs)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _soap_envelope(self, body_xml: str, action: str) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <soapenv:Header>
    <nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/{action}">
      <cUF>AN</cUF><versaoDados>4.00</versaoDados>
    </nfeCabecMsg>
  </soapenv:Header>
  <soapenv:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/{action}">{body_xml}</nfeDadosMsg>
  </soapenv:Body>
</soapenv:Envelope>"""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _soap_post(self, url: str, envelope: str, soap_action: str) -> str:
        client = await self._get_client()
        resp = await client.post(url, content=envelope.encode("utf-8"), headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction":   soap_action,
        })
        resp.raise_for_status()
        return resp.text

    async def consulta_nfe_chave(self, chave: str) -> SefazResult:
        tp_amb = 1 if self.ambiente == "producao" else 2
        body = f"""<consSitNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <tpAmb>{tp_amb}</tpAmb><xServ>CONSULTAR</xServ><chNFe>{chave}</chNFe>
</consSitNFe>"""
        try:
            if self.auth_mode == AUTH_CERTIFICADO:
                raw = await self._soap_post(
                    self.endpoints["nfe_consulta_chave"],
                    self._soap_envelope(body, "NFeConsultaProtocolo4"),
                    "http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4/nfeConsultaNF",
                )
                result = self._parse_consulta_nfe(raw, chave)
                result.auth_mode = AUTH_CERTIFICADO
                return result
            else:
                async with httpx.AsyncClient(timeout=30) as client:
                    raw = await client.post(
                        self.endpoints["nfe_consulta_chave"],
                        content=self._soap_envelope(body, "NFeConsultaProtocolo4").encode(),
                        headers={"Content-Type": "text/xml; charset=utf-8",
                                 "SOAPAction": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4/nfeConsultaNF"},
                    )
                    result = self._parse_consulta_nfe(raw.text, chave)
                    result.auth_mode = AUTH_NONE
                    return result
        except Exception as exc:
            log.exception("Erro consultando NF-e chave=%s", chave)
            return self._doc_from_chave(chave)

    def _doc_from_chave(self, chave: str) -> SefazResult:
        try:
            if len(chave) != 44:
                return SefazResult(success=False, error="Chave deve ter 44 dígitos")
            uf_cod    = chave[0:2]
            ano_mes   = chave[2:6]
            cnpj_emit = chave[6:20]
            modelo    = chave[20:22]
            serie     = chave[22:25]
            numero    = chave[25:34]
            doc_type  = "nfe" if modelo == "55" else "cte" if modelo == "57" else "nfe"
            ano = int("20" + ano_mes[0:2])
            mes = int(ano_mes[2:4])
            data_emi = datetime(ano, mes, 1, tzinfo=timezone.utc)
            UF_MAP = {"11":"RO","12":"AC","13":"AM","14":"RR","15":"PA","16":"AP","17":"TO",
                      "21":"MA","22":"PI","23":"CE","24":"RN","25":"PB","26":"PE","27":"AL",
                      "28":"SE","29":"BA","31":"MG","32":"ES","33":"RJ","35":"SP","41":"PR",
                      "42":"SC","43":"RS","50":"MS","51":"MT","52":"GO","53":"DF"}
            uf = UF_MAP.get(uf_cod, uf_cod)
            doc = SefazDocument(
                doc_type=doc_type, chave_acesso=chave,
                numero=str(int(numero)), serie=str(int(serie)), modelo=modelo,
                cnpj_emitente=cnpj_emit, razao_emitente=None, ie_emitente=None,
                uf_emitente=uf, municipio_emitente=None,
                cnpj_destinatario=None, cpf_destinatario=None,
                razao_destinatario=None, uf_destinatario=None,
                valor_total=0.0, valor_icms=None, valor_ipi=None,
                data_emissao=data_emi, data_autorizacao=None,
                status="processando", protocolo=None,
                motivo_status="Consulta offline — dados básicos da chave",
                natureza_operacao=None, cfop=None, xml_raw=None,
                extra={"fonte": "chave_decodificada"},
            )
            return SefazResult(success=True, documents=[doc], auth_mode=AUTH_NONE)
        except Exception as exc:
            return SefazResult(success=False, error=f"Chave inválida: {exc}")

    async def distribuicao_dfe_codigo_acesso(
        self,
        cnpj: str,
        codigo_acesso: str,
        ult_nsu: str = "000000000000000",
    ) -> SefazResult:
        cnpj_clean = cnpj.replace(".", "").replace("/", "").replace("-", "")
        tp_amb = 1 if self.ambiente == "producao" else 2
        body = f"""<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
  <tpAmb>{tp_amb}</tpAmb>
  <cUFAutor>91</cUFAutor>
  <CNPJ>{cnpj_clean}</CNPJ>
  <codAcesso>{codigo_acesso}</codAcesso>
  <distNSU><ultNSU>{ult_nsu}</ultNSU></distNSU>
</distDFeInt>"""
        try:
            raw = await self._soap_post(
                self.endpoints["nfe_distribuicao_dfe"],
                self._soap_envelope(body, "NFeDistribuicaoDFe"),
                "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse",
            )
            result = self._parse_distribuicao(raw)
            result.auth_mode = AUTH_CODIGO
            return result
        except Exception as exc:
            log.exception("Erro DFe código acesso CNPJ=%s", cnpj_clean)
            return SefazResult(success=False, error=str(exc), auth_mode=AUTH_CODIGO)

    async def distribuicao_dfe(
        self,
        cnpj: str,
        ult_nsu: str = "000000000000000",
    ) -> SefazResult:
        if self.auth_mode != AUTH_CERTIFICADO:
            return SefazResult(
                success=False,
                error="Certificado digital A1 necessário para consulta por CNPJ.",
                auth_mode=self.auth_mode,
            )
        cnpj_clean = cnpj.replace(".", "").replace("/", "").replace("-", "")
        tp_amb = 1 if self.ambiente == "producao" else 2
        body = f"""<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
  <tpAmb>{tp_amb}</tpAmb>
  <cUFAutor>91</cUFAutor>
  <CNPJ>{cnpj_clean}</CNPJ>
  <distNSU><ultNSU>{ult_nsu}</ultNSU></distNSU>
</distDFeInt>"""
        try:
            raw = await self._soap_post(
                self.endpoints["nfe_distribuicao_dfe"],
                self._soap_envelope(body, "NFeDistribuicaoDFe"),
                "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse",
            )
            result = self._parse_distribuicao(raw)
            result.auth_mode = AUTH_CERTIFICADO
            return result
        except Exception as exc:
            log.exception("Erro distribuicao DFe CNPJ=%s", cnpj_clean)
            return SefazResult(success=False, error=str(exc), auth_mode=AUTH_CERTIFICADO)

    async def enviar_manifestacao(
        self,
        cnpj: str,
        chave: str,
        tipo: str,
        justificativa: str | None = None,
    ) -> dict:
        if self.auth_mode == AUTH_NONE:
            return {
                "success": False,
                "error": "Manifestação requer certificado digital A1 ou código de acesso e-CAC.",
                "requires_auth": True,
            }
        cnpj_clean = cnpj.replace(".", "").replace("/", "").replace("-", "")
        tp_amb     = 1 if self.ambiente == "producao" else 2
        dh_evento  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S-03:00")
        desc       = MANIFESTACAO_DESC.get(tipo, "Manifestação")
        just_xml   = f"<xJust>{justificativa[:255]}</xJust>" if tipo == "210240" and justificativa else ""

        inf_evento = f"""<infEvento Id="ID{tipo}{chave}01">
  <cOrgao>91</cOrgao><tpAmb>{tp_amb}</tpAmb>
  <CNPJ>{cnpj_clean}</CNPJ><chNFe>{chave}</chNFe>
  <dhEvento>{dh_evento}</dhEvento><tpEvento>{tipo}</tpEvento>
  <nSeqEvento>1</nSeqEvento><verEvento>1.00</verEvento>
  <detEvento versao="1.00"><descEvento>{desc}</descEvento>{just_xml}</detEvento>
</infEvento>"""

        body = f"""<envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <idLote>1</idLote>
  <evento versao="1.00">{inf_evento}</evento>
</envEvento>"""

        try:
            raw  = await self._soap_post(
                self.endpoints["nfe_manifestacao"],
                self._soap_envelope(body, "NFeRecepcaoEvento4"),
                "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4/nfeRecepcaoEvento",
            )
            data = xmltodict.parse(raw)
            ret  = (
                data.get("soap:Envelope", {}).get("soap:Body", {})
                    .get("nfeRecepcaoEventoNFResult", {})
                    .get("retEnvEvento", {})
                    .get("retEvento", {})
                    .get("infEvento", {})
            )
            return {
                "success":     ret.get("cStat") in ("135", "136"),
                "cStat":       ret.get("cStat"),
                "xMotivo":     ret.get("xMotivo"),
                "nProt":       ret.get("nProt"),
                "dhRegEvento": ret.get("dhRegEvento"),
                "auth_mode":   self.auth_mode,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _parse_consulta_nfe(self, raw_xml: str, chave: str) -> SefazResult:
        try:
            tree  = etree.fromstring(raw_xml.encode())
            ns    = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
            ret   = tree.find(".//nfe:retConsSitNFe", ns)
            if ret is None:
                return SefazResult(success=False, error="Resposta inesperada da SEFAZ")

            cstat = ret.findtext("nfe:cStat", namespaces=ns, default="")
            xmot  = ret.findtext("nfe:xMotivo", namespaces=ns, default="")
            prot  = ret.find(".//nfe:infProt", ns)
            proto_num = prot.findtext("nfe:nProt", namespaces=ns) if prot else None

            nfe_node = tree.find(".//nfe:NFe", ns)
            if nfe_node is None:
                return SefazResult(success=False, error=f"SEFAZ: {cstat} - {xmot}")

            inf  = nfe_node.find("nfe:infNFe", ns)
            emit = inf.find("nfe:emit", ns)
            dest = inf.find("nfe:dest", ns)
            ide  = inf.find("nfe:ide", ns)
            tot  = inf.find(".//nfe:ICMSTot", ns)

            def txt(node, path):
                el = node.find(path, ns) if node is not None else None
                return el.text if el is not None else None

            dh_emi_str = txt(ide, "nfe:dhEmi") or txt(ide, "nfe:dEmi")
            dh_emi = datetime.fromisoformat(dh_emi_str) if dh_emi_str else datetime.now(timezone.utc)

            doc = SefazDocument(
                doc_type="nfe", chave_acesso=chave,
                numero=txt(ide, "nfe:nNF") or "", serie=txt(ide, "nfe:serie") or "",
                modelo=txt(ide, "nfe:mod") or "55",
                cnpj_emitente=txt(emit, "nfe:CNPJ") or "",
                razao_emitente=txt(emit, "nfe:xNome"), ie_emitente=txt(emit, "nfe:IE"),
                uf_emitente=txt(ide, "nfe:cUF"), municipio_emitente=txt(emit, ".//nfe:xMun"),
                cnpj_destinatario=txt(dest, "nfe:CNPJ") if dest else None,
                cpf_destinatario=txt(dest, "nfe:CPF") if dest else None,
                razao_destinatario=txt(dest, "nfe:xNome") if dest else None,
                uf_destinatario=txt(dest, ".//nfe:UF") if dest else None,
                valor_total=float(txt(tot, "nfe:vNF") or 0),
                valor_icms=float(txt(tot, "nfe:vICMS") or 0) or None,
                valor_ipi=float(txt(tot, "nfe:vIPI") or 0) or None,
                data_emissao=dh_emi, data_autorizacao=None,
                status=SEFAZ_STATUS_MAP.get(cstat, "processando"),
                protocolo=proto_num, motivo_status=xmot,
                natureza_operacao=txt(ide, "nfe:natOp"), cfop=None, xml_raw=raw_xml,
            )
            return SefazResult(success=True, documents=[doc], raw_response=raw_xml)
        except Exception as exc:
            log.exception("Erro parseando NF-e")
            return SefazResult(success=False, error=str(exc))

    def _parse_distribuicao(self, raw_xml: str) -> SefazResult:
        try:
            tree = etree.fromstring(raw_xml.encode())
            ns   = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
            docs: list[SefazDocument] = []
            for doc_zip in tree.findall(".//nfe:docZip", ns):
                schema = doc_zip.get("schema", "")
                try:
                    raw_bytes = base64.b64decode(doc_zip.text or "")
                    xml_bytes = zlib.decompress(raw_bytes, 16 + zlib.MAX_WBITS)
                    xml_str   = xml_bytes.decode("utf-8")
                except Exception:
                    continue
                if "procNFe" in schema or "NFe" in schema:
                    sub = self._parse_nfe_xml(xml_str)
                elif "procCTe" in schema or "CTe" in schema:
                    sub = self._parse_cte_xml(xml_str)
                else:
                    sub = None
                if sub:
                    docs.append(sub)
            return SefazResult(success=True, documents=docs, raw_response=raw_xml)
        except Exception as exc:
            return SefazResult(success=False, error=str(exc))

    def _parse_nfe_xml(self, xml_str: str) -> SefazDocument | None:
        try:
            data  = xmltodict.parse(xml_str)
            nfe   = data.get("nfeProc", data).get("NFe", {})
            inf   = nfe.get("infNFe", {})
            ide   = inf.get("ide", {})
            emit  = inf.get("emit", {})
            dest  = inf.get("dest", {})
            tot   = inf.get("total", {}).get("ICMSTot", {})
            chave = inf.get("@Id", "NFe")[3:]
            prot  = data.get("nfeProc", {}).get("protNFe", {}).get("infProt", {})
            cstat = prot.get("cStat", "")
            dh    = ide.get("dhEmi") or ide.get("dEmi")
            return SefazDocument(
                doc_type="nfe", chave_acesso=chave,
                numero=str(ide.get("nNF", "")), serie=str(ide.get("serie", "")),
                modelo=str(ide.get("mod", "55")),
                cnpj_emitente=str(emit.get("CNPJ", "")),
                razao_emitente=emit.get("xNome"), ie_emitente=emit.get("IE"),
                uf_emitente=str(ide.get("cUF", "")),
                municipio_emitente=emit.get("enderEmit", {}).get("xMun"),
                cnpj_destinatario=dest.get("CNPJ"), cpf_destinatario=dest.get("CPF"),
                razao_destinatario=dest.get("xNome"),
                uf_destinatario=dest.get("enderDest", {}).get("UF"),
                valor_total=float(tot.get("vNF", 0)),
                valor_icms=float(tot.get("vICMS", 0)) or None,
                valor_ipi=float(tot.get("vIPI", 0)) or None,
                data_emissao=datetime.fromisoformat(dh) if dh else datetime.now(timezone.utc),
                data_autorizacao=None,
                status=SEFAZ_STATUS_MAP.get(cstat, "autorizada"),
                protocolo=prot.get("nProt"), motivo_status=prot.get("xMotivo"),
                natureza_operacao=ide.get("natOp"), cfop=None, xml_raw=xml_str,
            )
        except Exception:
            log.exception("Erro _parse_nfe_xml")
            return None

    def _parse_cte_xml(self, xml_str: str) -> SefazDocument | None:
        try:
            data  = xmltodict.parse(xml_str)
            cte   = data.get("cteProc", data).get("CTe", {})
            inf   = cte.get("infCte", {})
            ide   = inf.get("ide", {})
            emit  = inf.get("emit", {})
            dest  = inf.get("dest", {}) or {}
            prot  = data.get("cteProc", {}).get("protCTe", {}).get("infProt", {})
            vPrest = inf.get("vPrest", {})
            chave  = inf.get("@Id", "CTe")[3:]
            dh     = ide.get("dhEmi") or ide.get("dEmi")
            return SefazDocument(
                doc_type="cte", chave_acesso=chave,
                numero=str(ide.get("nCT", "")), serie=str(ide.get("serie", "")),
                modelo=str(ide.get("mod", "57")),
                cnpj_emitente=str(emit.get("CNPJ", "")),
                razao_emitente=emit.get("xNome"), ie_emitente=emit.get("IE"),
                uf_emitente=str(ide.get("cUFIni", "")), municipio_emitente=None,
                cnpj_destinatario=dest.get("CNPJ"), cpf_destinatario=dest.get("CPF"),
                razao_destinatario=dest.get("xNome"), uf_destinatario=str(ide.get("cUFFim", "")),
                valor_total=float(vPrest.get("vTPrest", 0)),
                valor_icms=float(inf.get("imp", {}).get("ICMS", {}).get("ICMS00", {}).get("vICMS", 0) or 0) or None,
                valor_ipi=None,
                data_emissao=datetime.fromisoformat(dh) if dh else datetime.now(timezone.utc),
                data_autorizacao=None,
                status=SEFAZ_STATUS_MAP.get(prot.get("cStat", ""), "autorizada"),
                protocolo=prot.get("nProt"), motivo_status=prot.get("xMotivo"),
                natureza_operacao=ide.get("natOp"), cfop=ide.get("CFOP"), xml_raw=xml_str,
            )
        except Exception:
            log.exception("Erro _parse_cte_xml")
            return None


class NfseService:
    ENDPOINTS = {
        "3550308": "https://nfe.prefeitura.sp.gov.br/ws/lotenfe.asmx",
        "3304557": "https://notacarioca.rio.gov.br/WSNacional/nfse.asmx",
        "default": "https://nfse.prefeitura.municipio.gov.br/nfse.asmx",
    }

    def __init__(self, municipio_ibge: str | None = None, cert_pfx_bytes: bytes | None = None, cert_password: str = ""):
        self.municipio = municipio_ibge or "default"
        self.endpoint  = self.ENDPOINTS.get(self.municipio, self.ENDPOINTS["default"])
        self._cert     = cert_pfx_bytes
        self._pass     = cert_password

    async def consulta_nfse_cnpj(self, cnpj: str, pagina: int = 1) -> SefazResult:
        body = f"""<ConsultarNfseServicoPrestadoEnvio xmlns="http://www.abrasf.org.br/nfse.xsd">
  <Prestador><CpfCnpj><Cnpj>{cnpj}</Cnpj></CpfCnpj></Prestador>
  <Pagina>{pagina}</Pagina>
</ConsultarNfseServicoPrestadoEnvio>"""
        env = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Body>{body}</soapenv:Body>
</soapenv:Envelope>"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(self.endpoint, content=env.encode(),
                    headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "ConsultarNfseServicoPrestado"})
                resp.raise_for_status()
                return self._parse_nfse(resp.text)
        except Exception as exc:
            return SefazResult(success=False, error=str(exc))

    def _parse_nfse(self, raw: str) -> SefazResult:
        try:
            data  = xmltodict.parse(raw)
            lista = (data.get("soap:Envelope", {}).get("soap:Body", {})
                         .get("ConsultarNfseServicoPrestadoResposta", {})
                         .get("ListaNfse", {}).get("CompNfse", []))
            if isinstance(lista, dict): lista = [lista]
            docs = []
            for comp in lista:
                nfse  = comp.get("Nfse", {}).get("InfNfse", {})
                prest = nfse.get("PrestadorServico", {})
                tom   = nfse.get("TomadorServico", {})
                val   = nfse.get("Servico", {}).get("Valores", {})
                dh    = nfse.get("DataEmissao", "")
                docs.append(SefazDocument(
                    doc_type="nfse", chave_acesso=str(nfse.get("Numero", "")).zfill(15),
                    numero=str(nfse.get("Numero", "")), serie="1", modelo="SE",
                    cnpj_emitente=prest.get("IdentificacaoPrestador", {}).get("CpfCnpj", {}).get("Cnpj", ""),
                    razao_emitente=prest.get("RazaoSocial"), ie_emitente=None,
                    uf_emitente=None, municipio_emitente=prest.get("Endereco", {}).get("Municipio"),
                    cnpj_destinatario=tom.get("IdentificacaoTomador", {}).get("CpfCnpj", {}).get("Cnpj"),
                    cpf_destinatario=tom.get("IdentificacaoTomador", {}).get("CpfCnpj", {}).get("Cpf"),
                    razao_destinatario=tom.get("RazaoSocial"), uf_destinatario=None,
                    valor_total=float(val.get("ValorServicos", 0)), valor_icms=None, valor_ipi=None,
                    data_emissao=datetime.fromisoformat(dh) if dh else datetime.now(timezone.utc),
                    data_autorizacao=None, status="autorizada", protocolo=None, motivo_status=None,
                    natureza_operacao=nfse.get("Servico", {}).get("Discriminacao"),
                    cfop=None, xml_raw=raw, extra={"iss": float(val.get("ValorIss", 0))},
                ))
            return SefazResult(success=True, documents=docs)
        except Exception as exc:
            return SefazResult(success=False, error=str(exc))
