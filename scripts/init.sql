-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- fuzzy search on CNPJ/razao_social

-- Useful indexes for full-text and trigram search
-- Applied after initial migration via Alembic
