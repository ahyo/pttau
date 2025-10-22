"""Baseline schema marker

Revision ID: 0001_baseline
Revises: 
Create Date: 2024-11-06 00:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing production schema baseline. New deployments should stamp this revision.
    pass


def downgrade() -> None:
    # Baseline has no operations to reverse.
    pass
