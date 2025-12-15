"""add brand table and product.brand_id

Revision ID: 0006_add_brand_and_product_brand
Revises: 0005_add_services
Create Date: 2024-12-01 11:00:00

"""

from alembic import op
import sqlalchemy as sa


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in {col["name"] for col in inspector.get_columns(table)}


def _has_index(table: str, index: str) -> bool:
    if not _has_table(table):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return index in {ix["name"] for ix in inspector.get_indexes(table)}


revision = "0006_add_brand_and_product_brand"
down_revision = "0005_add_services"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_table("brand"):
        op.create_table(
            "brand",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=150), nullable=False),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.UniqueConstraint("slug", name="uq_brand_slug"),
        )
        op.create_index("ix_brand_slug", "brand", ["slug"])

    if _has_table("product") and not _has_column("product", "brand_id"):
        op.add_column("product", sa.Column("brand_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_product_brand",
            "product",
            "brand",
            ["brand_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_product_brand_id", "product", ["brand_id"])


def downgrade() -> None:
    if _has_index("product", "ix_product_brand_id"):
        op.drop_index("ix_product_brand_id", table_name="product")
    with op.batch_alter_table("product") as batch:
        try:
            batch.drop_constraint("fk_product_brand", type_="foreignkey")
        except Exception:
            pass
        if _has_column("product", "brand_id"):
            batch.drop_column("brand_id")

    if _has_index("brand", "ix_brand_slug"):
        op.drop_index("ix_brand_slug", table_name="brand")
    if _has_table("brand"):
        op.drop_table("brand")
