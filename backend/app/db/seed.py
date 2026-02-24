#!/usr/bin/env python3
"""
Script to seed initial plans into the database.
Run: python -m app.db.seed
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.models.models import Plano

DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

PLANOS_INICIAIS = [
    {
        "nome": "Starter",
        "limite_notas": 1000,
        "limite_empresas": 1,
        "valor_mensal": 97.00,
        "ativo": True,
    },
    {
        "nome": "Business",
        "limite_notas": -1,  # unlimited
        "limite_empresas": 3,
        "valor_mensal": 197.00,
        "ativo": True,
    },
    {
        "nome": "Enterprise",
        "limite_notas": -1,
        "limite_empresas": -1,
        "valor_mensal": 497.00,
        "ativo": True,
    },
]


async def seed():
    engine = create_async_engine(DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        for plano_data in PLANOS_INICIAIS:
            plano = Plano(**plano_data)
            db.add(plano)
        await db.commit()
        print(f"✅ {len(PLANOS_INICIAIS)} planos criados!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
