"""Add sort_order column to product_attribute table

Revision ID: 20260202_233000
Revises: 20260202_230000
Create Date: 2026-02-02 23:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260202_233000'
down_revision: Union[str, None] = '20260202_230000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sort_order column to product_attribute table with default value
    op.add_column('product_attribute', sa.Column('sort_order', sa.Integer(), nullable=False, default=1, server_default='1'))

    # Update existing records to have a default sort order based on their id if needed
    # This will assign sequential numbers starting from 1 (optional, depends on business logic)
    # For now, we'll keep the default value of 1 for all existing records


def downgrade() -> None:
    # Drop the sort_order column
    op.drop_column('product_attribute', 'sort_order')