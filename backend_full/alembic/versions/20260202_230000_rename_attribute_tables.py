"""Rename attribute_definition table to product_attribute and remove old product_attribute table

Revision ID: 20260202_230000
Revises: 5012f843c2f3
Create Date: 2026-02-02 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '20260202_230000'
down_revision: Union[str, None] = '5012f843c2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: First, we need to handle the foreign key constraint in product_attribute_value table
    # that references the attribute_definition table
    # Drop the foreign key constraint that references attribute_definition
    # Find and drop the specific constraint by name
    connection = op.get_bind()
    result = connection.execute(text("""
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class tbl ON tbl.oid = con.conrelid
        JOIN pg_class ref_tbl ON ref_tbl.oid = con.confrelid
        WHERE tbl.relname = 'product_attribute_value'
        AND ref_tbl.relname = 'attribute_definition'
    """))

    for row in result:
        constraint_name = row[0]
        try:
            op.drop_constraint(constraint_name, 'product_attribute_value', type_='foreignkey')
        except:
            pass  # Continue if constraint doesn't exist with expected name

    # Step 2: Drop the deprecated product_attribute table (the old one with product_id, name, value)
    # We need to make sure no other tables reference it
    op.drop_table("product_attribute")

    # Step 3: Rename attribute_definition table to product_attribute
    # Now rename the table
    op.execute('ALTER TABLE attribute_definition RENAME TO product_attribute')

    # Rename the primary key constraint if it exists
    try:
        op.execute('ALTER TABLE product_attribute RENAME CONSTRAINT attribute_definition_pkey TO product_attribute_pkey')
    except:
        pass  # Continue if constraint doesn't exist with expected name

    # Rename the unique constraint
    try:
        op.execute('ALTER TABLE product_attribute RENAME CONSTRAINT uq_attrdef_producttype_code TO uq_productattr_producttype_code')
    except:
        pass  # Continue if constraint doesn't exist with expected name

    # Step 4: Recreate the foreign key constraint in product_attribute_value to reference the renamed table
    op.create_foreign_key(
        'fk_product_attr_val_attr_def_id',
        'product_attribute_value',
        'product_attribute',
        ['attribute_definition_id'],
        ['id']
    )


def downgrade() -> None:
    # Reverse the changes
    # Step 1: Drop the foreign key constraint that points to product_attribute
    try:
        op.drop_constraint('fk_product_attr_val_attr_def_id', 'product_attribute_value', type_='foreignkey')
    except:
        pass  # Continue if constraint doesn't exist with expected name

    # Step 2: Rename the table back to attribute_definition
    op.execute('ALTER TABLE product_attribute RENAME TO attribute_definition')

    # Rename constraints back
    try:
        op.execute('ALTER TABLE attribute_definition RENAME CONSTRAINT product_attribute_pkey TO attribute_definition_pkey')
    except:
        pass  # Continue if constraint doesn't exist with expected name

    try:
        op.execute('ALTER TABLE attribute_definition RENAME CONSTRAINT uq_productattr_producttype_code TO uq_attrdef_producttype_code')
    except:
        pass  # Continue if constraint doesn't exist with expected name

    # Step 3: Recreate the old product_attribute table (the deprecated one with product_id, name, value)
    op.create_table(
        'product_attribute',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('product.id'), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.UniqueConstraint('product_id', 'name', name='uq_product_attribute'),
    )

    # Step 4: Find and drop the constraint that references the new table structure
    # Then recreate the original constraint that pointed to attribute_definition
    connection = op.get_bind()
    result = connection.execute(text("""
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class tbl ON tbl.oid = con.conrelid
        JOIN pg_class ref_tbl ON ref_tbl.oid = con.confrelid
        WHERE tbl.relname = 'product_attribute_value'
        AND ref_tbl.relname = 'product_attribute'
    """))

    for row in result:
        constraint_name = row[0]
        try:
            op.drop_constraint(constraint_name, 'product_attribute_value', type_='foreignkey')
        except:
            pass  # Continue if constraint doesn't exist with expected name

    # Recreate the original foreign key constraint to attribute_definition
    op.create_foreign_key(
        'fk_product_attr_val_attr_def_id_original',
        'product_attribute_value',
        'attribute_definition',
        ['attribute_definition_id'],
        ['id']
    )