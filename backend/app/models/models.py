from sqlalchemy import (
    Column, String, Integer, ForeignKey, Boolean, DateTime, Text,
    Numeric, BigInteger, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class EmpresaStatus(str, enum.Enum):
    trial = "trial"
    ativo = "ativo"
    bloqueado = "bloqueado"
    inadimplente = "inadimplente"


class UserRole(str, enum.Enum):
    admin = "admin"
    operador = "operador"


class NotaModelo(str, enum.Enum):
    NFe = "NFe"
    CTe = "CTe"


class NotaTipo(str, enum.Enum):
    entrada = "entrada"
    saida = "saida"


class NotaStatus(str, enum.Enum):
    autorizada = "autorizada"
    cancelada = "cancelada"
    denegada = "denegada"


class AssinaturaStatus(str, enum.Enum):
    ativa = "ativa"
    vencida = "vencida"
    cancelada = "cancelada"
    pendente = "pendente"


class Plano(Base):
    __tablename__ = "planos"

    id = Column(String, primary_key=True, default=gen_uuid)
    nome = Column(String(100), nullable=False)
    limite_notas = Column(Integer, nullable=False, default=1000)
    limite_empresas = Column(Integer, nullable=False, default=1)
    valor_mensal = Column(Numeric(10, 2), nullable=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    empresas = relationship("Empresa", back_populates="plano")


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(String, primary_key=True, default=gen_uuid)
    nome = Column(String(200), nullable=False)
    cnpj = Column(String(14), unique=True, nullable=False)
    certificado_path = Column(String(500), nullable=True)
    senha_certificado_criptografada = Column(Text, nullable=True)
    certificado_titular = Column(String(300), nullable=True)
    certificado_validade = Column(DateTime(timezone=True), nullable=True)
    plano_id = Column(String, ForeignKey("planos.id"), nullable=True)
    status = Column(SAEnum(EmpresaStatus), default=EmpresaStatus.trial)
    asaas_customer_id = Column(String(100), nullable=True)
    trial_expira_em = Column(DateTime(timezone=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    plano = relationship("Plano", back_populates="empresas")
    usuarios = relationship("Usuario", back_populates="empresa")
    notas = relationship("Nota", back_populates="empresa")
    controle_nsu = relationship("ControleNSU", back_populates="empresa", uselist=False)
    assinaturas = relationship("Assinatura", back_populates="empresa")
    logs = relationship("LogAuditoria", back_populates="empresa")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(String, primary_key=True, default=gen_uuid)
    empresa_id = Column(String, ForeignKey("empresas.id"), nullable=False)
    nome = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False)
    senha_hash = Column(String(500), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.operador)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa", back_populates="usuarios")
    logs = relationship("LogAuditoria", back_populates="usuario")


class Nota(Base):
    __tablename__ = "notas"

    id = Column(String, primary_key=True, default=gen_uuid)
    empresa_id = Column(String, ForeignKey("empresas.id"), nullable=False)
    chave = Column(String(44), nullable=False)
    modelo = Column(SAEnum(NotaModelo), nullable=False)
    tipo = Column(SAEnum(NotaTipo), nullable=False)
    cnpj_emitente = Column(String(14), nullable=True)
    cnpj_destinatario = Column(String(14), nullable=True)
    valor_total = Column(Numeric(15, 2), nullable=True)
    data_emissao = Column(DateTime(timezone=True), nullable=True)
    status = Column(SAEnum(NotaStatus), default=NotaStatus.autorizada)
    xml_path = Column(String(500), nullable=True)
    nsu = Column(BigInteger, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa", back_populates="notas")


class ControleNSU(Base):
    __tablename__ = "controle_nsu"

    empresa_id = Column(String, ForeignKey("empresas.id"), primary_key=True)
    ultimo_nsu = Column(BigInteger, default=0)
    ultima_sincronizacao = Column(DateTime(timezone=True), nullable=True)
    atualizado_em = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    empresa = relationship("Empresa", back_populates="controle_nsu")


class Assinatura(Base):
    __tablename__ = "assinaturas"

    id = Column(String, primary_key=True, default=gen_uuid)
    empresa_id = Column(String, ForeignKey("empresas.id"), nullable=False)
    asaas_subscription_id = Column(String(100), nullable=True)
    status = Column(SAEnum(AssinaturaStatus), default=AssinaturaStatus.pendente)
    proximo_vencimento = Column(DateTime(timezone=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa", back_populates="assinaturas")


class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id = Column(String, primary_key=True, default=gen_uuid)
    empresa_id = Column(String, ForeignKey("empresas.id"), nullable=True)
    usuario_id = Column(String, ForeignKey("usuarios.id"), nullable=True)
    acao = Column(String(500), nullable=False)
    ip = Column(String(50), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

    empresa = relationship("Empresa", back_populates="logs")
    usuario = relationship("Usuario", back_populates="logs")
