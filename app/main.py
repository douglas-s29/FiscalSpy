"""
FiscalSpy — FastAPI Application
"""

import logging
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.documents import router as docs_router
from app.api.v1.routes.resources import (
    monitors_router,
    webhooks_router,
    alerts_router,
)
from app.api.v1.routes.sefaz_config import router as sefaz_config_router
from app.db.session import engine

# ── Sentry ───────────────────────────────────────────
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2)

# ── Logging ──────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if not settings.is_production else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

# ── App ──────────────────────────────────────────────
app = FastAPI(
    title       = "FiscalSpy API",
    description = "Plataforma de Inteligência Fiscal — NF-e, CT-e, NFS-e",
    version     = "1.0.0",
    docs_url    = "/api/docs",
    redoc_url   = "/api/redoc",
    openapi_url = "/api/openapi.json",
)

# ── CORS ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.cors_origins_list,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── API Routers ───────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth_router,         prefix=PREFIX)
app.include_router(docs_router,         prefix=PREFIX)
app.include_router(monitors_router,     prefix=PREFIX)
app.include_router(webhooks_router,     prefix=PREFIX)
app.include_router(alerts_router,       prefix=PREFIX)
app.include_router(sefaz_config_router, prefix=PREFIX)

# ── Health ────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    from redis.asyncio import from_url as redis_from_url
    db_ok = redis_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        log.error("DB health check failed: %s", exc)
    try:
        r = redis_from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception as exc:
        log.error("Redis health check failed: %s", exc)
    ok = db_ok and redis_ok
    return JSONResponse(
        status_code=status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "healthy" if ok else "degraded", "version": "1.0.0",
                 "database": "ok" if db_ok else "error", "redis": "ok" if redis_ok else "error"},
    )

# ── Static files (frontend) ───────────────────────────
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(request: Request, full_path: str = ""):
    # Don't intercept API or health routes
    if full_path.startswith("api/") or full_path == "health":
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse(status_code=404, content={"detail": "Frontend not found"})

# ── Global exception handler ─────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    if request.url.path.startswith("/api"):
        log.exception("Unhandled exception: %s %s", request.method, request.url)
        return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor"})
    raise exc

# ── Startup / shutdown ───────────────────────────────
@app.on_event("startup")
async def startup():
    import asyncio
    log.info("🚀 FiscalSpy API starting — env=%s", settings.app_env)
    for _ in range(10):
        proc = await asyncio.create_subprocess_exec(
            "alembic", "upgrade", "head",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0:
            log.info("✅ Migrations aplicadas com sucesso")
            break
        log.warning("⏳ Aguardando banco... %s", stderr.decode()[:200])
        await asyncio.sleep(2)
    else:
        err = stderr.decode()
        log.error("❌ Falha ao aplicar migrations: %s", err)
        raise RuntimeError(f"Falha ao aplicar migrations na inicialização: {err}")

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
    log.info("FiscalSpy API stopped")
