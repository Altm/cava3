"""rename kind column to code in location table

Revision ID: 20260206_130000
Revises: 20260206_120000
Create Date: 2026-02-06 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260206_130000'
down_revision = '20260206_120000'
branch_labels = None
depends_on = None


def upgrade():
    # Add the new code column
    op.add_column('location', sa.Column('code', sa.String(64), nullable=True))
    
    # Copy data from kind to code
    op.execute('UPDATE location SET code = kind')
    
    # Drop the old kind column
    op.drop_column('location', 'kind')


def downgrade():
    # Add back the old kind column
    op.add_column('location', sa.Column('kind', sa.String(64), nullable=True))
    
    # Copy data from code to kind
    op.execute('UPDATE location SET kind = code')
    
    # Drop the new code column
    op.drop_column('location', 'code')