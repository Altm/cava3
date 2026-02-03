"""Create product_meta table

Revision ID: 20260203_000000
Revises: 20260202_234500
Create Date: 2026-02-03 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260203_000000'
down_revision: Union[str, None] = '20260202_234500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create product_meta table
    op.create_table(
        'product_meta',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('product.id', ondelete='CASCADE'), nullable=False),
        sa.Column('old_id', sa.Integer(), nullable=True),
        sa.Column('handle', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('vendor', sa.Text(), nullable=True),
        sa.Column('type', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('published', sa.Boolean(), nullable=True),
        sa.Column('variant_barcode', sa.Text(), nullable=True),
        sa.Column('seo_title', sa.Text(), nullable=True),
        sa.Column('seo_description', sa.Text(), nullable=True),
        sa.Column('google_shopping', sa.Text(), nullable=True),
        sa.Column('image', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id'),
        sa.UniqueConstraint('old_id')
    )


def downgrade() -> None:
    # Drop product_meta table
    op.drop_table('product_meta')