# FiscalSpy — Backend

Plataforma SaaS de Inteligência Fiscal. Consulta, monitora e gerencia NF-e, CT-e e NFS-e em tempo real via webservices SEFAZ.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Framework | FastAPI 0.115 (async) |
| Banco de dados | PostgreSQL 16 + SQLAlchemy 2 (asyncpg) |
| Cache / Fila | Redis 7 + ARQ |
| Scheduler | APScheduler 3 |
| Migrations | Alembic |
| Auth | JWT (access + refresh token rotation) |
| SEFAZ | Webservices SOAP (HTTPS + multi-modal) |
| Containers | Docker Compose |

## Estrutura

```
fiscalspy/
├── app/
│   ├── api/v1/routes/
│   │   ├── auth.py            # Register, Login, Refresh, Logout
│   │   ├── documents.py       # Consulta, manifestação, export
│   │   ├── resources.py       # Monitors, Webhooks, Alerts
│   │   └── sefaz_config.py    # Configuração multi-modal SEFAZ
│   ├── core/
│   │   ├── config.py          # Pydantic Settings
│   │   └── security.py        # JWT, bcrypt, HMAC, deps
│   ├── db/session.py          # Async engine + session
│   ├── models/models.py       # Todos os modelos SQLAlchemy
│   ├── schemas/schemas.py     # Todos os Pydantic schemas
│   ├── services/
│   │   ├── sefaz.py           # Integração SOAP SEFAZ (NF-e, CT-e, NFS-e)
│   │   ├── document.py        # Upsert, alertas, listagem
│   │   └── webhook.py         # Dispatch + delivery com retry
│   ├── static/index.html      # Frontend SPA (dark/light mode)
│   ├── workers/
│   │   ├── main.py            # ARQ tasks (sync, webhooks, email)
│   │   └── scheduler.py       # APScheduler (cron jobs)
│   └── main.py                # FastAPI app entry point
├── migrations/versions/001_initial.py  # Schema completo
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Início rápido

```bash
cp .env.example .env
# Edite .env com suas configurações
# Gere uma SECRET_KEY segura:
openssl rand -hex 32

docker compose up -d
```

Acesse:
- `http://localhost:8000` → Frontend SPA
- `http://localhost:8000/api/docs` → Swagger UI
- `http://localhost:8000/health` → Health check

## Autenticação SEFAZ — 3 modos

### 🟢 Acesso Público (MEI / sem certificado)
- Consulta NF-e por **chave de acesso** (44 dígitos)
- Funciona para qualquer CNPJ, inclusive MEI
- Sem configuração necessária

### 🔵 Código de Acesso e-CAC
- Para **MEI e Microempresas** sem certificado digital
- Gere o código em [cav.receita.fazenda.gov.br](https://cav.receita.fazenda.gov.br)
- Habilita busca automática de documentos por CNPJ

> **Nota:** O código de acesso e-CAC é gerado no portal da Receita Federal. Não confundir com certificado A1.

### 🟣 Certificado Digital A1 (.pfx)
- Acesso completo: DFe, manifestação, CT-e, NFS-e
- Configure em **Configurações SEFAZ** → Certificado Digital A1

## API — Endpoints principais

### Auth
| POST | `/api/v1/auth/register` | Cria organização + usuário |
| POST | `/api/v1/auth/login` | Login → tokens |
| POST | `/api/v1/auth/refresh` | Renova access token |
| GET  | `/api/v1/auth/me` | Dados do usuário logado |

### Documentos
| GET  | `/api/v1/documents` | Lista com filtros |
| POST | `/api/v1/documents/consulta/chave` | Consulta por chave SEFAZ |
| POST | `/api/v1/documents/consulta/cnpj` | Consulta por CNPJ |
| POST | `/api/v1/documents/manifestacao` | Envia manifestação |

### Configuração SEFAZ
| GET  | `/api/v1/sefaz/config` | Configuração atual |
| POST | `/api/v1/sefaz/config` | Salva modo de autenticação |
| POST | `/api/v1/sefaz/testar` | Testa conexão |
| POST | `/api/v1/sefaz/sync` | Sync manual de CNPJ |

### Monitores / Webhooks / Alertas
| CRUD | `/api/v1/monitors` | Monitores de CNPJ |
| CRUD | `/api/v1/webhooks` | Endpoints webhook |
| CRUD | `/api/v1/alerts` | Regras de alerta |

## Webhook — Segurança HMAC-SHA256

```
X-FiscalSpy-Signature: sha256=<hex>
X-FiscalSpy-Event: documento.novo
X-FiscalSpy-Delivery: <uuid>
```

Eventos: `documento.novo`, `documento.cancelado`, `documento.denegado`, `manifestacao.enviada`, `alerta.disparado`

## Banco de Dados

Migrations gerenciadas via Alembic. A migration `001_initial` inclui todas as colunas:
- `fiscal_documents`: `valor_pis`, `valor_cofins`, `valor_iss`, `data_cancelamento`

Aplicadas automaticamente no startup da API.

```bash
# Manual (dentro do container)
docker exec fiscalspy_api alembic upgrade head
```

## Multi-tenancy

Isolamento completo por `organization_id`. Papéis: `owner` → `admin` → `member` → `viewer`.

## Variáveis de ambiente

```env
SECRET_KEY=            # 64 chars hex — OBRIGATÓRIO
DATABASE_URL=          # postgresql+asyncpg://...
REDIS_URL=             # redis://:senha@redis:6379/0
SEFAZ_AMBIENTE=        # homologacao | producao
SEFAZ_CERT_PATH=       # /app/certs/empresa.pfx (opcional)
SMTP_USER=             # para envio de alertas por email
```
