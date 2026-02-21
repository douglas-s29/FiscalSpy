"""
FiscalSpy — SQLAlchemy models (String enums, ForeignKeys corretos)
"""
import uuid
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


def uuid_pk():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

def now_utc():
    return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

def updated_at():
    return Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Organization(Base):
    __tablename__ = "organizations"
    id                 = uuid_pk()
    name               = Column(String(255), nullable=False)
    slug               = Column(String(100), unique=True, nullable=False, index=True)
    cnpj               = Column(String(18), unique=True, nullable=True)
    plan               = Column(String(20), default="free", nullable=False)
    docs_limit         = Column(Integer, default=500, nullable=False)
    is_active          = Column(Boolean, default=True, nullable=False)
    cert_pfx_encrypted = Column(Text, nullable=True)
    cert_password_hash = Column(String(255), nullable=True)
    cert_expires_at    = Column(DateTime(timezone=True), nullable=True)
    extra              = Column(JSONB, nullable=True, default=dict)
    created_at         = now_utc()
    updated_at         = updated_at()

    users      = relationship("User",           back_populates="organization", lazy="select")
    monitors   = relationship("CNPJMonitor",    back_populates="organization", lazy="select")
    documents  = relationship("FiscalDocument", back_populates="organization", lazy="select")
    webhooks   = relationship("Webhook",        back_populates="organization", lazy="select")
    alerts     = relationship("Alert",          back_populates="organization", lazy="select")


class User(Base):
    __tablename__ = "users"
    id              = uuid_pk()
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    full_name       = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(20), default="member", nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    is_verified     = Column(Boolean, default=False, nullable=False)
    last_login_at   = Column(DateTime(timezone=True), nullable=True)
    created_at      = now_utc()
    updated_at      = updated_at()

    organization = relationship("Organization", back_populates="users")


class CNPJMonitor(Base):
    __tablename__ = "cnpj_monitors"
    __table_args__ = (UniqueConstraint("organization_id", "cnpj", name="uq_org_cnpj"),)
    id               = uuid_pk()
    organization_id  = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    cnpj             = Column(String(18), nullable=False, index=True)
    razao_social     = Column(String(255), nullable=True)
    description      = Column(String(255), nullable=True)
    monitor_nfe      = Column(Boolean, default=True)
    monitor_cte      = Column(Boolean, default=True)
    monitor_nfse     = Column(Boolean, default=False)
    as_emitente      = Column(Boolean, default=True)
    as_destinatario  = Column(Boolean, default=True)
    as_transportador = Column(Boolean, default=False)
    is_active        = Column(Boolean, default=True)
    last_sync_at     = Column(DateTime(timezone=True), nullable=True)
    sync_error       = Column(Text, nullable=True)
    created_at       = now_utc()
    updated_at       = updated_at()

    organization = relationship("Organization", back_populates="monitors")
    alerts       = relationship("Alert", back_populates="monitor", lazy="select")


class FiscalDocument(Base):
    __tablename__ = "fiscal_documents"
    __table_args__ = (UniqueConstraint("organization_id", "chave_acesso", name="uq_org_chave"),)
    id                 = uuid_pk()
    organization_id    = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_type           = Column(String(10), nullable=False, index=True)
    chave_acesso       = Column(String(44), nullable=False, index=True)
    numero             = Column(String(20), nullable=False)
    serie              = Column(String(5), nullable=False)
    modelo             = Column(String(2), nullable=False)
    cnpj_emitente      = Column(String(18), nullable=False, index=True)
    razao_emitente     = Column(String(255), nullable=True)
    ie_emitente        = Column(String(30), nullable=True)
    uf_emitente        = Column(String(2), nullable=True)
    municipio_emitente = Column(String(100), nullable=True)
    cnpj_destinatario  = Column(String(18), nullable=True, index=True)
    cpf_destinatario   = Column(String(14), nullable=True)
    razao_destinatario = Column(String(255), nullable=True)
    uf_destinatario    = Column(String(2), nullable=True)
    valor_total        = Column(Numeric(15, 2), nullable=False)
    valor_icms         = Column(Numeric(15, 2), nullable=True)
    valor_ipi          = Column(Numeric(15, 2), nullable=True)
    valor_pis          = Column(Numeric(15, 2), nullable=True)
    valor_cofins       = Column(Numeric(15, 2), nullable=True)
    valor_iss          = Column(Numeric(15, 2), nullable=True)
    data_emissao       = Column(DateTime(timezone=True), nullable=False, index=True)
    data_autorizacao   = Column(DateTime(timezone=True), nullable=True)
    data_cancelamento  = Column(DateTime(timezone=True), nullable=True)
    status             = Column(String(20), nullable=False, index=True)
    protocolo          = Column(String(20), nullable=True)
    motivo_status      = Column(String(255), nullable=True)
    manifestacao       = Column(String(10), nullable=True)
    manifestacao_at    = Column(DateTime(timezone=True), nullable=True)
    natureza_operacao  = Column(String(100), nullable=True)
    cfop               = Column(String(10), nullable=True)
    xml_raw            = Column(Text, nullable=True)
    extra              = Column(JSONB, nullable=True)
    created_at         = now_utc()
    updated_at         = updated_at()

    organization   = relationship("Organization", back_populates="documents")
    webhook_events = relationship("WebhookDelivery", back_populates="document", lazy="select")


class Webhook(Base):
    __tablename__ = "webhooks"
    id              = uuid_pk()
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name            = Column(String(100), nullable=False)
    url             = Column(String(500), nullable=False)
    secret          = Column(String(64), nullable=False)
    events          = Column(JSONB, nullable=False, default=list)
    is_active       = Column(Boolean, default=True)
    failure_count   = Column(Integer, default=0)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    created_at      = now_utc()
    updated_at      = updated_at()

    organization = relationship("Organization", back_populates="webhooks")
    deliveries   = relationship("WebhookDelivery", back_populates="webhook", lazy="select")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    id             = uuid_pk()
    webhook_id     = Column(UUID(as_uuid=True), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id    = Column(UUID(as_uuid=True), ForeignKey("fiscal_documents.id", ondelete="SET NULL"), nullable=True)
    event          = Column(String(50), nullable=False)
    payload        = Column(JSONB, nullable=False)
    status         = Column(String(20), default="pending", nullable=False, index=True)
    attempt        = Column(Integer, default=0)
    next_retry_at  = Column(DateTime(timezone=True), nullable=True)
    response_code  = Column(Integer, nullable=True)
    response_body  = Column(Text, nullable=True)
    error_message  = Column(Text, nullable=True)
    created_at     = now_utc()
    delivered_at   = Column(DateTime(timezone=True), nullable=True)

    webhook  = relationship("Webhook",        back_populates="deliveries")
    document = relationship("FiscalDocument", back_populates="webhook_events")


class Alert(Base):
    __tablename__ = "alerts"
    id              = uuid_pk()
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    monitor_id      = Column(UUID(as_uuid=True), ForeignKey("cnpj_monitors.id", ondelete="CASCADE"), nullable=True)
    name            = Column(String(100), nullable=False)
    condition       = Column(String(30), nullable=False)
    condition_value = Column(String(255), nullable=True)
    channel         = Column(String(20), nullable=False)
    destination     = Column(String(500), nullable=False)
    is_active       = Column(Boolean, default=True)
    last_fired_at   = Column(DateTime(timezone=True), nullable=True)
    fire_count      = Column(Integer, default=0)
    created_at      = now_utc()
    updated_at      = updated_at()

    organization = relationship("Organization", back_populates="alerts")
    monitor      = relationship("CNPJMonitor",  back_populates="alerts")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id         = uuid_pk()
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, default=False)
    created_at = now_utc()

    user = relationship("User")
