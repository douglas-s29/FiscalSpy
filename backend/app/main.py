import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.routes import auth, empresa, notas, planos, sefaz, asaas
from app.db.database import engine
from app.models.models import Base
from sqlalchemy import text


async def init_db():
    """Cria tabelas e garante novas colunas."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Adiciona colunas novas com segurança
        new_cols = [
            ("empresas", "certificado_titular", "VARCHAR(300)"),
            ("empresas", "certificado_validade", "TIMESTAMP WITH TIME ZONE"),
        ]
        for table, col, col_type in new_cols:
            try:
                await conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}"
                ))
            except Exception:
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="FiscalSpy API",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,    prefix="/auth",    tags=["auth"])
app.include_router(empresa.router, prefix="/empresa", tags=["empresa"])
app.include_router(notas.router,   prefix="/notas",   tags=["notas"])
app.include_router(planos.router,  prefix="/planos",  tags=["planos"])
app.include_router(sefaz.router,   prefix="/sefaz",   tags=["sefaz"])
app.include_router(asaas.router,   prefix="/asaas",   tags=["asaas"])


@app.get("/health")
async def health():
    return {"status": "ok"}
