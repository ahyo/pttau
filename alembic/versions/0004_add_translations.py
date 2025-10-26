"""add translation tables for site content

Revision ID: 0004_add_translations
Revises: 0003_add_user_contact_fields
Create Date: 2024-11-06 02:00:00

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


revision = "0004_add_translations"
down_revision = "0003_add_user_contact_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_table("menu_item_tr"):
        op.create_table(
            "menu_item_tr",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("menu_item_id", sa.Integer(), nullable=False),
            sa.Column("lang", sa.String(length=5), nullable=False),
            sa.Column("label", sa.String(length=100), nullable=False),
            sa.ForeignKeyConstraint(["menu_item_id"], ["menu_item.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("menu_item_id", "lang", name="uq_menu_item_tr"),
        )
        op.create_index("ix_menu_item_tr_menu_item_id", "menu_item_tr", ["menu_item_id"])

    if not _has_table("page_tr"):
        op.create_table(
            "page_tr",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("page_id", sa.Integer(), nullable=False),
            sa.Column("lang", sa.String(length=5), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("excerpt", sa.Text(), nullable=True),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("meta_title", sa.String(length=255), nullable=True),
            sa.Column("meta_desc", sa.String(length=255), nullable=True),
            sa.ForeignKeyConstraint(["page_id"], ["page.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("page_id", "lang", name="uq_page_tr"),
        )
        op.create_index("ix_page_tr_page_id", "page_tr", ["page_id"])

    if not _has_table("carousel_item_tr"):
        op.create_table(
            "carousel_item_tr",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("carousel_item_id", sa.Integer(), nullable=False),
            sa.Column("lang", sa.String(length=5), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("subtitle", sa.Text(), nullable=True),
            sa.Column("cta_text", sa.String(length=100), nullable=True),
            sa.ForeignKeyConstraint(["carousel_item_id"], ["carousel_item.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("carousel_item_id", "lang", name="uq_carousel_item_tr"),
        )
        op.create_index(
            "ix_carousel_item_tr_carousel_item_id",
            "carousel_item_tr",
            ["carousel_item_id"],
        )

    if not _has_table("product_tr"):
        op.create_table(
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
        op.create_index("ix_product_tr_product_id", "product_tr", ["product_id"])
        op.create_index("ix_product_tr_lang", "product_tr", ["lang"])

    if not _has_table("footer_section_tr"):
        op.create_table(
            "footer_section_tr",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("section_id", sa.Integer(), nullable=False),
            sa.Column("lang", sa.String(length=5), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.ForeignKeyConstraint(["section_id"], ["footer_section.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("section_id", "lang", name="uq_footer_section_tr"),
        )
        op.create_index(
            "ix_footer_section_tr_section_id",
            "footer_section_tr",
            ["section_id"],
        )

    if not _has_table("footer_link_tr"):
        op.create_table(
            "footer_link_tr",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("link_id", sa.Integer(), nullable=False),
            sa.Column("lang", sa.String(length=5), nullable=False),
            sa.Column("html_content", sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(["link_id"], ["footer_link.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("link_id", "lang", name="uq_footer_link_tr"),
        )
        op.create_index("ix_footer_link_tr_link_id", "footer_link_tr", ["link_id"])


def downgrade() -> None:
    if _has_index("footer_link_tr", "ix_footer_link_tr_link_id"):
        op.drop_index("ix_footer_link_tr_link_id", table_name="footer_link_tr")
    if _has_table("footer_link_tr"):
        op.drop_table("footer_link_tr")

    if _has_index("footer_section_tr", "ix_footer_section_tr_section_id"):
        op.drop_index("ix_footer_section_tr_section_id", table_name="footer_section_tr")
    if _has_table("footer_section_tr"):
        op.drop_table("footer_section_tr")

    if _has_index("carousel_item_tr", "ix_carousel_item_tr_carousel_item_id"):
        op.drop_index(
            "ix_carousel_item_tr_carousel_item_id",
            table_name="carousel_item_tr",
        )
    if _has_table("carousel_item_tr"):
        op.drop_table("carousel_item_tr")

    if _has_index("page_tr", "ix_page_tr_page_id"):
        op.drop_index("ix_page_tr_page_id", table_name="page_tr")
    if _has_table("page_tr"):
        op.drop_table("page_tr")

    if _has_index("product_tr", "ix_product_tr_lang"):
        op.drop_index("ix_product_tr_lang", table_name="product_tr")
    if _has_index("product_tr", "ix_product_tr_product_id"):
        op.drop_index("ix_product_tr_product_id", table_name="product_tr")
    if _has_table("product_tr"):
        op.drop_table("product_tr")

    if _has_index("menu_item_tr", "ix_menu_item_tr_menu_item_id"):
        op.drop_index("ix_menu_item_tr_menu_item_id", table_name="menu_item_tr")
    if _has_table("menu_item_tr"):
        op.drop_table("menu_item_tr")
