"""rename unit_cost column to base_cost in product table

Revision ID: 20260206_120000
Revises: 20260203_000000_create_product_shopify_meta_table
Create Date: 2026-02-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260206_120000'
down_revision = '20260203_000000'
branch_labels = None
depends_on = None


def upgrade():
    # Add the new base_cost column
    op.add_column('product', sa.Column('base_cost', sa.Numeric(10, 2), nullable=True))

    # Copy data from unit_cost to base_cost
    op.execute('UPDATE product SET base_cost = unit_cost')

    # Drop the old unit_cost column
    op.drop_column('product', 'unit_cost')


def downgrade():
    # Add back the old unit_cost column
    op.add_column('product', sa.Column('unit_cost', sa.Numeric(10, 2), nullable=True))

    # Copy data from base_cost to unit_cost
    op.execute('UPDATE product SET unit_cost = base_cost')

    # Drop the new base_cost column
    op.drop_column('product', 'base_cost')