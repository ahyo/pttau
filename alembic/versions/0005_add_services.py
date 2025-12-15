"""add services table

Revision ID: 0005_add_services
Revises: 0004_add_translations
Create Date: 2024-12-01 10:00:00

"""

from alembic import op
import sqlalchemy as sa


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def _has_index(table: str, index: str) -> bool:
    if not _has_table(table):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return index in {ix["name"] for ix in inspector.get_indexes(table)}


revision = "0005_add_services"
down_revision = "0004_add_translations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_table("service"):
        op.create_table(
            "service",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=150), nullable=False),
            sa.Column("title", sa.String(length=150), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("image_url", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.UniqueConstraint("slug", name="uq_service_slug"),
        )
        op.create_index("ix_service_slug", "service", ["slug"])

    if not _has_table("service_tr"):
        op.create_table(
            "service_tr",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("service_id", sa.Integer(), nullable=False),
            sa.Column("lang", sa.String(length=5), nullable=False),
            sa.Column("title", sa.String(length=150), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["service_id"], ["service.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("service_id", "lang", name="uq_service_tr"),
        )
        op.create_index("ix_service_tr_service_id", "service_tr", ["service_id"])
        op.create_index("ix_service_tr_lang", "service_tr", ["lang"])


def downgrade() -> None:
    if _has_index("service_tr", "ix_service_tr_lang"):
        op.drop_index("ix_service_tr_lang", table_name="service_tr")
    if _has_index("service_tr", "ix_service_tr_service_id"):
        op.drop_index("ix_service_tr_service_id", table_name="service_tr")
    if _has_table("service_tr"):
        op.drop_table("service_tr")

    if _has_index("service", "ix_service_slug"):
        op.drop_index("ix_service_slug", table_name="service")
    if _has_table("service"):
        op.drop_table("service")
