"""Remove is_composite column from product table

Revision ID: 0003_remove_is_composite
Revises: 0002_simple_catalog
Create Date: 2026-01-29 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '0003_remove_is_composite'
down_revision: Union[str, None] = '0002_simple_catalog'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the is_composite column from the product table
    # The is_composite property will be derived from the associated product type
    op.drop_column('product', 'is_composite')


def downgrade() -> None:
    # Recreate the is_composite column in the product table for rollback
    op.add_column('product',
        sa.Column('is_composite', sa.Boolean, default=False, comment='Composite flag for recipes')
    )