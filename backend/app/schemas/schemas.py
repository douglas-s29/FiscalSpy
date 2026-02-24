from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import re


# Auth
class RegisterRequest(BaseModel):
    nome_empresa: str = Field(..., min_length=2, max_length=200)
    cnpj: str = Field(..., min_length=14, max_length=14)
    nome_usuario: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    senha: str = Field(..., min_length=8)

    @validator('cnpj')
    def validate_cnpj(cls, v):
        v = re.sub(r'\D', '', v)
        if len(v) != 14:
            raise ValueError('CNPJ deve ter 14 dígitos')
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# Empresa
class EmpresaResponse(BaseModel):
    id: str
    nome: str
    cnpj: str
    status: str
    plano_id: Optional[str]
    trial_expira_em: Optional[datetime]
    asaas_customer_id: Optional[str]
    criado_em: datetime

    class Config:
        from_attributes = True


class EmpresaUpdate(BaseModel):
    nome: Optional[str] = None


# Usuario
class UsuarioResponse(BaseModel):
    id: str
    nome: str
    email: str
    role: str
    ativo: bool
    criado_em: datetime

    class Config:
        from_attributes = True


# Plano
class PlanoResponse(BaseModel):
    id: str
    nome: str
    limite_notas: int
    limite_empresas: int
    valor_mensal: Decimal
    ativo: bool

    class Config:
        from_attributes = True


# Assinatura
class CriarAssinaturaRequest(BaseModel):
    plano_id: str
    ciclo: str = "MONTHLY"  # MONTHLY, YEARLY


class AssinaturaResponse(BaseModel):
    id: str
    empresa_id: str
    asaas_subscription_id: Optional[str]
    status: str
    proximo_vencimento: Optional[datetime]
    criado_em: datetime

    class Config:
        from_attributes = True


# Nota
class NotaResponse(BaseModel):
    id: str
    empresa_id: str
    chave: str
    modelo: str
    tipo: str
    cnpj_emitente: Optional[str]
    cnpj_destinatario: Optional[str]
    valor_total: Optional[Decimal]
    data_emissao: Optional[datetime]
    status: str
    nsu: Optional[int]
    criado_em: datetime

    class Config:
        from_attributes = True


class NotaListResponse(BaseModel):
    items: List[NotaResponse]
    total: int
    page: int
    page_size: int
    pages: int


class EstatisticasResponse(BaseModel):
    total_entrada_mes: int
    total_saida_mes: int
    total_canceladas: int
    valor_total_mensal: Decimal
    grafico_mensal: List[dict]


# SEFAZ
class SefazStatusResponse(BaseModel):
    ultimo_nsu: int
    ultima_sincronizacao: Optional[datetime]
    status_worker: str


# Webhook Asaas
class AsaasWebhookPayment(BaseModel):
    id: str
    status: str
    customer: str
    subscription: Optional[str]
    value: Optional[float]
    dueDate: Optional[str]


class AsaasWebhookEvent(BaseModel):
    event: str
    payment: Optional[AsaasWebhookPayment]
