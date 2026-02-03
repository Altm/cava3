"""Rename attribute_definition_id column to product_attribute_id in product_attribute_value table

Revision ID: 20260202_234500
Revises: 20260202_233000
Create Date: 2026-02-02 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260202_234500'
down_revision: Union[str, None] = '20260202_233000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, drop the unique constraint that references the old column name
    # Find the exact name of the constraint
    from sqlalchemy import text
    connection = op.get_bind()

    # Query to find the unique constraint name
    result = connection.execute(text("""
        SELECT tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'product_attribute_value'
        AND tc.constraint_type = 'UNIQUE'
        AND ccu.column_name = 'attribute_definition_id'
    """))

    rows = result.fetchall()
    for row in rows:
        constraint_name = row[0]
        try:
            op.drop_constraint(constraint_name, 'product_attribute_value', type_='unique')
        except:
            pass  # Continue if constraint doesn't exist with expected name

    # Next, drop the foreign key constraint
    # Find the exact name of the foreign key constraint
    result = connection.execute(text("""
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class tbl ON tbl.oid = con.conrelid
        JOIN pg_class ref_tbl ON ref_tbl.oid = con.confrelid
        WHERE tbl.relname = 'product_attribute_value'
        AND ref_tbl.relname = 'product_attribute'
    """))

    rows = result.fetchall()
    for row in rows:
        constraint_name = row[0]
        try:
            op.drop_constraint(constraint_name, 'product_attribute_value', type_='foreignkey')
        except:
            pass  # Continue if constraint doesn't exist with expected name

    # Rename the column
    op.alter_column('product_attribute_value', 'attribute_definition_id', new_column_name='product_attribute_id')
    
    # Recreate the foreign key constraint with the new column name
    op.create_foreign_key(
        'fk_product_attr_val_prod_attr_id',
        'product_attribute_value',
        'product_attribute',
        ['product_attribute_id'],
        ['id']
    )
    
    # Recreate the unique constraint with the new column name
    op.create_unique_constraint(
        'uq_product_attr_val_prod_attr',
        'product_attribute_value',
        ['product_id', 'product_attribute_id']
    )


def downgrade() -> None:
    # Drop the unique constraint with the new column name
    # Find the exact name of the constraint
    from sqlalchemy import text
    connection = op.get_bind()
    
    # Query to find the unique constraint name
    result = connection.execute(text("""
        SELECT tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_name = 'product_attribute_value'
        AND tc.constraint_type = 'UNIQUE'
        AND ccu.column_name = 'product_attribute_id'
    """))
    
    rows = result.fetchall()
    for row in rows:
        constraint_name = row[0]
        try:
            op.drop_constraint(constraint_name, 'product_attribute_value', type_='unique')
        except:
            pass  # Continue if constraint doesn't exist with expected name

    # Drop the foreign key constraint with the new column name
    result = connection.execute(text("""
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class tbl ON tbl.oid = con.conrelid
        JOIN pg_class ref_tbl ON ref_tbl.oid = con.confrelid
        WHERE tbl.relname = 'product_attribute_value'
        AND ref_tbl.relname = 'product_attribute'
    """))
    
    rows = result.fetchall()
    for row in rows:
        constraint_name = row[0]
        try:
            op.drop_constraint(constraint_name, 'product_attribute_value', type_='foreignkey')
        except:
            pass  # Continue if constraint doesn't exist with expected name

    # Rename the column back
    op.alter_column('product_attribute_value', 'product_attribute_id', new_column_name='attribute_definition_id')
    
    # Recreate the foreign key constraint with the old column name
    op.create_foreign_key(
        'fk_product_attr_val_attr_def_id',
        'product_attribute_value',
        'product_attribute',
        ['attribute_definition_id'],
        ['id']
    )
    
    # Recreate the unique constraint with the old column name
    op.create_unique_constraint(
        'uq_product_attr_value',
        'product_attribute_value',
        ['product_id', 'attribute_definition_id']
    )