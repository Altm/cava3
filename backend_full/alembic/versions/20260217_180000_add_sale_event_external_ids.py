"""add external sale_id and user_id to sale_event

Revision ID: 20260217_180000
Revises: 20260217_120000
Create Date: 2026-02-17 18:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260217_180000"
down_revision = "20260217_120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sale_event",
        sa.Column(
            "sale_id",
            sa.BigInteger(),
            nullable=True,
            comment="External sale identifier from request",
        ),
    )
    op.add_column(
        "sale_event",
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=True,
            comment="External operator/user identifier from request",
        ),
    )


def downgrade() -> None:
    op.drop_column("sale_event", "user_id")
    op.drop_column("sale_event", "sale_id")
