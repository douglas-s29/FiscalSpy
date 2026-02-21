"""initial schema

Revision ID: 001_initial
Create Date: 2025-01-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # organizations
    op.create_table(
        "organizations",
        sa.Column("id",                  UUID(as_uuid=True), primary_key=True),
        sa.Column("name",                sa.String(255), nullable=False),
        sa.Column("slug",                sa.String(100), unique=True, nullable=False),
        sa.Column("cnpj",                sa.String(18), unique=True, nullable=True),
        sa.Column("plan",                sa.String(20), nullable=False, server_default="free"),
        sa.Column("docs_limit",          sa.Integer(), nullable=False, server_default="500"),
        sa.Column("is_active",           sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("cert_pfx_encrypted",  sa.Text(), nullable=True),
        sa.Column("cert_password_hash",  sa.String(255), nullable=True),
        sa.Column("cert_expires_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra",              postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",          sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # users
    op.create_table(
        "users",
        sa.Column("id",               UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id",  UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email",            sa.String(255), unique=True, nullable=False),
        sa.Column("full_name",        sa.String(255), nullable=False),
        sa.Column("hashed_password",  sa.String(255), nullable=False),
        sa.Column("role",             sa.String(20), nullable=False, server_default="member"),
        sa.Column("is_active",        sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified",      sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_login_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email",           "users", ["email"])
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    # cnpj_monitors
    op.create_table(
        "cnpj_monitors",
        sa.Column("id",               UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id",  UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cnpj",             sa.String(18), nullable=False),
        sa.Column("razao_social",     sa.String(255), nullable=True),
        sa.Column("description",      sa.String(255), nullable=True),
        sa.Column("monitor_nfe",      sa.Boolean(), server_default="true"),
        sa.Column("monitor_cte",      sa.Boolean(), server_default="true"),
        sa.Column("monitor_nfse",     sa.Boolean(), server_default="false"),
        sa.Column("as_emitente",      sa.Boolean(), server_default="true"),
        sa.Column("as_destinatario",  sa.Boolean(), server_default="true"),
        sa.Column("as_transportador", sa.Boolean(), server_default="false"),
        sa.Column("is_active",        sa.Boolean(), server_default="true"),
        sa.Column("last_sync_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_error",       sa.Text(), nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "cnpj", name="uq_org_cnpj"),
    )

    # fiscal_documents
    op.create_table(
        "fiscal_documents",
        sa.Column("id",                UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id",   UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type",          sa.String(10), nullable=False),
        sa.Column("chave_acesso",      sa.String(44), nullable=False),
        sa.Column("numero",            sa.String(20), nullable=False),
        sa.Column("serie",             sa.String(5), nullable=False),
        sa.Column("modelo",            sa.String(2), nullable=False),
        sa.Column("cnpj_emitente",     sa.String(18), nullable=False),
        sa.Column("razao_emitente",    sa.String(255), nullable=True),
        sa.Column("ie_emitente",       sa.String(30), nullable=True),
        sa.Column("uf_emitente",       sa.String(2), nullable=True),
        sa.Column("municipio_emitente",sa.String(100), nullable=True),
        sa.Column("cnpj_destinatario", sa.String(18), nullable=True),
        sa.Column("cpf_destinatario",  sa.String(14), nullable=True),
        sa.Column("razao_destinatario",sa.String(255), nullable=True),
        sa.Column("uf_destinatario",   sa.String(2), nullable=True),
        sa.Column("valor_total",       sa.Numeric(15, 2), nullable=False),
        sa.Column("valor_icms",        sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_ipi",         sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_pis",         sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_cofins",      sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_iss",         sa.Numeric(15, 2), nullable=True),
        sa.Column("data_emissao",      sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_autorizacao",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_cancelamento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status",            sa.String(20), nullable=False),
        sa.Column("protocolo",         sa.String(20), nullable=True),
        sa.Column("motivo_status",     sa.String(255), nullable=True),
        sa.Column("manifestacao",      sa.String(10), nullable=True),
        sa.Column("manifestacao_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("natureza_operacao", sa.String(100), nullable=True),
        sa.Column("cfop",              sa.String(10), nullable=True),
        sa.Column("xml_raw",           sa.Text(), nullable=True),
        sa.Column("extra",             JSONB(), nullable=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",        sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "chave_acesso", name="uq_org_chave"),
    )
    op.create_index("ix_fiscal_documents_org",    "fiscal_documents", ["organization_id"])
    op.create_index("ix_fiscal_documents_chave",  "fiscal_documents", ["chave_acesso"])
    op.create_index("ix_fiscal_documents_emissao","fiscal_documents", ["data_emissao"])
    op.create_index("ix_fiscal_documents_status", "fiscal_documents", ["status"])

    # webhooks
    op.create_table(
        "webhooks",
        sa.Column("id",              UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name",            sa.String(100), nullable=False),
        sa.Column("url",             sa.String(500), nullable=False),
        sa.Column("secret",          sa.String(64), nullable=False),
        sa.Column("events",          JSONB(), nullable=False),
        sa.Column("is_active",       sa.Boolean(), server_default="true"),
        sa.Column("failure_count",   sa.Integer(), server_default="0"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # webhook_deliveries
    op.create_table(
        "webhook_deliveries",
        sa.Column("id",            UUID(as_uuid=True), primary_key=True),
        sa.Column("webhook_id",    UUID(as_uuid=True), sa.ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id",   UUID(as_uuid=True), sa.ForeignKey("fiscal_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event",         sa.String(50), nullable=False),
        sa.Column("payload",       JSONB(), nullable=False),
        sa.Column("status",        sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt",       sa.Integer(), server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("delivered_at",  sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_webhook_deliveries_status", "webhook_deliveries", ["status"])

    # alerts
    op.create_table(
        "alerts",
        sa.Column("id",               UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id",  UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("monitor_id",       UUID(as_uuid=True), sa.ForeignKey("cnpj_monitors.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name",             sa.String(100), nullable=False),
        sa.Column("condition",        sa.String(30), nullable=False),
        sa.Column("condition_value",  sa.String(255), nullable=True),
        sa.Column("channel",          sa.String(20), nullable=False),
        sa.Column("destination",      sa.String(500), nullable=False),
        sa.Column("is_active",        sa.Boolean(), server_default="true"),
        sa.Column("last_fired_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("fire_count",       sa.Integer(), server_default="0"),
        sa.Column("created_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",     UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash",  sa.String(255), unique=True, nullable=False),
        sa.Column("expires_at",  sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked",     sa.Boolean(), server_default="false"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("alerts")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhooks")
    op.drop_table("fiscal_documents")
    op.drop_table("cnpj_monitors")
    op.drop_table("users")
    op.drop_table("organizations")
