"""add product images gallery

Revision ID: 0007_add_product_images
Revises: 0006_add_brand_and_product_brand
Create Date: 2024-12-01 12:00:00

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


revision = "0007_add_product_images"
down_revision = "0006_add_brand_and_product_brand"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_table("product_image"):
        op.create_table(
            "product_image",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("image_url", sa.String(length=255), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_product_image_product_id", "product_image", ["product_id"])


def downgrade() -> None:
    if _has_index("product_image", "ix_product_image_product_id"):
        op.drop_index("ix_product_image_product_id", table_name="product_image")
    if _has_table("product_image"):
        op.drop_table("product_image")
