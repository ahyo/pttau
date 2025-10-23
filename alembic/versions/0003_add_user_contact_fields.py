"""add email and phone number to user

Revision ID: 0003_add_user_contact_fields
Revises: 0002_add_catalog_and_cart
Create Date: 2024-11-06 00:45:00

"""
from alembic import op
import sqlalchemy as sa


revision = "0003_add_user_contact_fields"
down_revision = "0002_add_catalog_and_cart"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user", sa.Column("email", sa.String(length=120), nullable=True)
    )
    op.add_column(
        "user", sa.Column("phone_number", sa.String(length=30), nullable=True)
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)
    op.create_index("ix_user_phone_number", "user", ["phone_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_phone_number", table_name="user")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_column("user", "phone_number")
    op.drop_column("user", "email")

