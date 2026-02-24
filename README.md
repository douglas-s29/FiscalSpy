# 🔍 FiscalSpy

**SaaS de Monitoramento Fiscal Inteligente** — Capture automaticamente todas as NF-e e CT-e via SEFAZ.

---

## 📋 Visão Geral

FiscalSpy é um SaaS multi-tenant completo que permite que empresas monitorem automaticamente todas as notas fiscais emitidas contra ou por seus CNPJs, com integração direta à SEFAZ via protocolo DistribuicaoDFe.

### Stack Tecnológica

| Camada | Tecnologia |
|--------|------------|
| Backend | FastAPI + Python 3.11 |
| Frontend | React + Vite + Tailwind CSS |
| Banco de Dados | PostgreSQL 15 |
| Cache / Queue | Redis 7 |
| Worker | Celery + Celery Beat |
| Proxy | Nginx |
| Migrations | Alembic |
| Pagamentos | Asaas |
| Containerização | Docker + Docker Compose |

---

## 🚀 Início Rápido (Desenvolvimento)

### Pré-requisitos
- Docker 24+
- Docker Compose 2.0+

### 1. Clone e configure

```bash
git clone <repo>
cd fiscalspy

# Copie o arquivo de variáveis
cp .env.example .env

# Edite as variáveis obrigatórias
nano .env
```

### 2. Variáveis obrigatórias no `.env`

```env
# Gere uma chave segura:
SECRET_KEY=$(openssl rand -hex 32)
AES_KEY=$(openssl rand -hex 16)

# Configure o Asaas (sandbox para dev)
ASAAS_API_KEY=sua_chave_asaas
ASAAS_WEBHOOK_TOKEN=token_webhook_secreto
```

### 3. Subir os containers

```bash
docker-compose up -d
```

### 4. Aguardar e verificar

```bash
# Verificar status dos containers
docker-compose ps

# Ver logs
docker-compose logs -f backend

# Acessar a aplicação
# Frontend: http://localhost:80
# API: http://localhost:80/api
# Docs: http://localhost:80/api/docs
```

### 5. Seed inicial (planos)

```bash
docker-compose exec backend python -m app.db.seed
```

---

## 🗄️ Banco de Dados

### Migrations

```bash
# Gerar nova migration
docker-compose exec backend alembic revision --autogenerate -m "descricao"

# Aplicar migrations
docker-compose exec backend alembic upgrade head

# Reverter
docker-compose exec backend alembic downgrade -1
```

---

## 🌐 Endpoints da API

### Autenticação
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/register` | Cadastro (cria empresa + usuário admin) |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/refresh` | Refresh token |
| POST | `/api/auth/logout` | Logout |

### Empresa
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/empresa/me` | Dados da empresa |
| PUT | `/api/empresa/update` | Atualizar empresa |
| POST | `/api/empresa/upload-certificado` | Upload certificado A1 |

### Notas
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/notas` | Listar (com filtros e paginação) |
| GET | `/api/notas/{id}` | Detalhes |
| GET | `/api/notas/download/{id}` | Download XML individual |
| GET | `/api/notas/estatisticas` | Dashboard de stats |
| GET | `/api/notas/exportar` | Export Excel |
| GET | `/api/notas/download-lote` | ZIP com todos XMLs |

### SEFAZ
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/sefaz/sincronizar` | Sincronizar manualmente |
| GET | `/api/sefaz/status` | Status da integração |

### Planos & Assinatura
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/planos` | Listar planos |
| POST | `/api/assinatura/criar` | Criar assinatura |
| GET | `/api/assinatura/status` | Status da assinatura |
| POST | `/api/asaas/webhook` | Webhook Asaas |

---

## 💳 Integração Asaas

### Configurar webhook no painel Asaas:
- URL: `https://seudominio.com/api/asaas/webhook`
- Adicionar header: `asaas-access-token: SEU_WEBHOOK_TOKEN`

### Eventos tratados:
- `PAYMENT_CONFIRMED` / `PAYMENT_RECEIVED` → Ativa empresa
- `PAYMENT_OVERDUE` → Marca como inadimplente
- `PAYMENT_DELETED` / `SUBSCRIPTION_DELETED` → Bloqueia empresa

---

## 🔐 Segurança

- **JWT** com access (1h) e refresh tokens (30d)
- **AES-256-CBC** para criptografia de senhas de certificados
- **bcrypt** para hash de senhas de usuário
- **Rate limiting** via slowapi
- **CORS** configurado
- **Validação de webhook** por token secreto
- Middleware de verificação de status da empresa (trial/inadimplente/bloqueado)

---

## ⚙️ Worker (Celery)

O worker executa a cada **5 minutos** para todas as empresas ativas:

1. Busca o último NSU da empresa
2. Consulta a SEFAZ (DistribuicaoDFe)
3. Decodifica base64 + descomprime gzip
4. Faz parse do XML NF-e/CT-e
5. Salva no banco e no storage de XML
6. Atualiza o controle de NSU

```bash
# Ver logs do worker
docker-compose logs -f worker

# Testar sincronização manual
docker-compose exec backend python -c "
from app.workers.tasks import sincronizar_todas_empresas
sincronizar_todas_empresas.delay()
"
```

---

## 🚢 Produção

### 1. Configurar `.env.prod` com variáveis de produção

### 2. Configurar HTTPS (Let's Encrypt)

```bash
# Editar nginx/conf.d/default.conf para seu domínio
# Obter certificado
docker-compose -f docker-compose.prod.yml run --rm certbot \
  certonly --webroot -w /var/www/certbot \
  -d seudominio.com \
  --email seuemail@dominio.com --agree-tos
```

### 3. Deploy

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### 4. Seed em produção

```bash
docker-compose -f docker-compose.prod.yml exec backend python -m app.db.seed
```

---

## 📁 Estrutura do Projeto

```
fiscalspy/
├── backend/
│   ├── app/
│   │   ├── api/routes/         # Rotas FastAPI
│   │   ├── core/               # Config, security, deps
│   │   ├── db/                 # Database, seed
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # SEFAZ, Asaas services
│   │   └── workers/            # Celery tasks
│   ├── migrations/             # Alembic migrations
│   ├── storage/                # XML e certificados (volume)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/         # Layout, UI components
│       ├── pages/              # Dashboard, Notas, etc.
│       ├── services/           # Axios API client
│       └── store/              # Zustand state
├── nginx/                      # Configurações Nginx
├── worker/                     # Dockerfile do worker
├── docker-compose.yml          # Dev
├── docker-compose.prod.yml     # Produção
└── .env                        # Variáveis de ambiente
```

---

## 🤝 Contribuindo

PRs são bem-vindos! Por favor siga o padrão de código existente.

---

## 📄 Licença

Proprietário — FiscalSpy © 2025
