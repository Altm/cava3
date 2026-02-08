"""rename composite_component table to product_composite

Revision ID: 20260206_140000
Revises: 20260206_130000
Create Date: 2026-02-06 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260206_140000'
down_revision = '20260206_130000'
branch_labels = None
depends_on = None


def upgrade():
    # Rename the table from composite_component to product_composite
    op.rename_table('composite_component', 'product_composite')


def downgrade():
    # Rename the table back from product_composite to composite_component
    op.rename_table('product_composite', 'composite_component')