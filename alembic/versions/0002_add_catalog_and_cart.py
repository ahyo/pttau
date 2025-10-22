"""add product, cart tables and adjust user defaults

Revision ID: 0002_add_catalog_and_cart
Revises: 0001_baseline
Create Date: 2024-11-06 00:15:00

"""
from alembic import op
import sqlalchemy as sa


revision = "0002_add_catalog_and_cart"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    product = op.create_table(
        "product",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column(
            "price",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.Column("stock", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("image_url", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("slug", name="uq_product_slug"),
    )

    product_tr = op.create_table(
        "product_tr",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("lang", sa.String(length=5), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("short_description", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("product_id", "lang", name="uq_product_tr"),
    )

    cart = op.create_table(
        "cart",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
    )

    cart_item = op.create_table(
        "cart_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "unit_price",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
        sa.ForeignKeyConstraint(["cart_id"], ["cart.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("cart_id", "product_id", name="uq_cart_item_product"),
    )

    op.create_index("ix_product_slug", "product", ["slug"], unique=True)
    op.create_index("ix_product_tr_lang", "product_tr", ["lang"])
    op.create_index("ix_product_tr_product_id", "product_tr", ["product_id"])
    op.create_index("ix_cart_user_id", "cart", ["user_id"])
    op.create_index("ix_cart_status", "cart", ["status"])
    op.create_index("ix_cart_item_cart_id", "cart_item", ["cart_id"])
    op.create_index("ix_cart_item_product_id", "cart_item", ["product_id"])

    op.alter_column(
        "user",
        "is_admin",
        existing_type=sa.Boolean(),
        server_default=sa.text("0"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "user",
        "is_admin",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )
    op.drop_index("ix_cart_item_product_id", table_name="cart_item")
    op.drop_index("ix_cart_item_cart_id", table_name="cart_item")
    op.drop_index("ix_cart_status", table_name="cart")
    op.drop_index("ix_cart_user_id", table_name="cart")
    op.drop_index("ix_product_tr_product_id", table_name="product_tr")
    op.drop_index("ix_product_tr_lang", table_name="product_tr")
    op.drop_index("ix_product_slug", table_name="product")
    op.drop_table("cart_item")
    op.drop_table("cart")
    op.drop_table("product_tr")
    op.drop_table("product")
