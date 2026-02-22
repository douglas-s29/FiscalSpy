"""
FiscalSpy — Pydantic schemas (request / response)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    org_name:  str       = Field(..., min_length=2, max_length=255)
    org_cnpj:  str | None = None
    full_name: str       = Field(..., min_length=2, max_length=255)
    email:     EmailStr
    password:  str       = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int


class RefreshRequest(BaseModel):
    refresh_token: str


class OrgOut(OrmBase):
    id:          UUID
    name:        str
    slug:        str
    cnpj:        str | None
    plan:        str
    docs_limit:  int
    is_active:   bool
    created_at:  datetime


class OrgUpdate(BaseModel):
    name:  str | None = None
    cnpj:  str | None = None


class UserOut(OrmBase):
    id:              UUID
    organization_id: UUID
    email:           str
    full_name:       str
    role:            str
    is_active:       bool
    is_verified:     bool
    last_login_at:   datetime | None
    created_at:      datetime


class UserInvite(BaseModel):
    email:     EmailStr
    full_name: str
    role:      str = "member"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role:      str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password:     str = Field(..., min_length=8)


class MonitorCreate(BaseModel):
    cnpj:             str  = Field(..., pattern=r"^\d{14}$")
    description:      str | None = None
    monitor_nfe:      bool = True
    monitor_cte:      bool = True
    monitor_nfse:     bool = False
    as_emitente:      bool = True
    as_destinatario:  bool = True
    as_transportador: bool = False


class MonitorOut(OrmBase):
    id:               UUID
    cnpj:             str
    razao_social:     str | None
    description:      str | None
    monitor_nfe:      bool
    monitor_cte:      bool
    monitor_nfse:     bool
    as_emitente:      bool
    as_destinatario:  bool
    as_transportador: bool
    is_active:        bool
    last_sync_at:     datetime | None
    sync_error:       str | None
    created_at:       datetime


class MonitorUpdate(BaseModel):
    description:      str | None = None
    monitor_nfe:      bool | None = None
    monitor_cte:      bool | None = None
    monitor_nfse:     bool | None = None
    as_emitente:      bool | None = None
    as_destinatario:  bool | None = None
    as_transportador: bool | None = None
    is_active:        bool | None = None


class DocumentOut(OrmBase):
    id:                UUID
    doc_type:          str
    chave_acesso:      str
    numero:            str
    serie:             str
    cnpj_emitente:     str
    razao_emitente:    str | None
    uf_emitente:       str | None
    cnpj_destinatario: str | None
    razao_destinatario:str | None
    uf_destinatario:   str | None
    valor_total:       Decimal
    data_emissao:      datetime
    data_autorizacao:  datetime | None
    data_cancelamento: datetime | None
    status:            str
    protocolo:         str | None
    motivo_status:     str | None
    manifestacao:      str | None
    manifestacao_at:   datetime | None
    natureza_operacao: str | None
    cfop:              str | None
    created_at:        datetime


class DocumentListOut(BaseModel):
    total:     int
    page:      int
    page_size: int
    items:     list[DocumentOut]


class DocumentFilter(BaseModel):
    doc_type:   str | None = None
    status:     str | None = None
    uf:         str | None = None
    cnpj:       str | None = None
    data_inicio:datetime | None = None
    data_fim:   datetime | None = None
    valor_min:  Decimal | None = None
    valor_max:  Decimal | None = None
    page:       int = Field(1, ge=1)
    page_size:  int = Field(25, ge=1, le=100)


class ManifestacaoRequest(BaseModel):
    document_id:  UUID
    tipo:         str
    justificativa:str | None = None


class WebhookCreate(BaseModel):
    name:   str = Field(..., min_length=2, max_length=100)
    url:    str = Field(..., pattern=r"^https?://")
    events: list[str]


class WebhookOut(OrmBase):
    id:              UUID
    name:            str
    url:             str
    events:          list[str]
    is_active:       bool
    failure_count:   int
    last_success_at: datetime | None
    last_failure_at: datetime | None
    created_at:      datetime


class WebhookUpdate(BaseModel):
    name:      str | None = None
    url:       str | None = None
    events:    list[str] | None = None
    is_active: bool | None = None


class WebhookDeliveryOut(OrmBase):
    id:            UUID
    event:         str
    status:        str
    attempt:       int
    response_code: int | None
    error_message: str | None
    created_at:    datetime
    delivered_at:  datetime | None


class AlertCreate(BaseModel):
    name:            str = Field(..., min_length=2)
    monitor_id:      UUID | None = None
    condition:       str
    condition_value: str | None = None
    channel:         str
    destination:     str


class AlertOut(OrmBase):
    id:              UUID
    name:            str
    condition:       str
    condition_value: str | None
    channel:         str
    destination:     str
    is_active:       bool
    last_fired_at:   datetime | None
    fire_count:      int
    created_at:      datetime


class AlertUpdate(BaseModel):
    name:            str | None = None
    condition:       str | None = None
    condition_value: str | None = None
    channel:         str | None = None
    destination:     str | None = None
    is_active:       bool | None = None


class ChaveConsultaRequest(BaseModel):
    chave_acesso: str = Field(..., min_length=44, max_length=44)


class CNPJConsultaRequest(BaseModel):
    cnpj:        str  = Field(..., pattern=r"^\d{14}$")
    doc_type:    str | None = None
    data_inicio: datetime | None = None
    data_fim:    datetime | None = None


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status:   str
    version:  str
    database: str
    redis:    str
