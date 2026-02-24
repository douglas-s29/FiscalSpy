"""Script para criar/atualizar tabelas no banco sem Alembic migration."""
import asyncio
from app.db.database import engine
from app.models.models import Base
from sqlalchemy import text


async def create_tables():
    async with engine.begin() as conn:
        # Cria todas as tabelas que não existem
        await conn.run_sync(Base.metadata.create_all)
        
        # Adiciona colunas novas se não existirem (migration manual segura)
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
        
        print("✅ Banco de dados atualizado com sucesso!")


if __name__ == "__main__":
    asyncio.run(create_tables())
