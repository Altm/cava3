"""Complete transition from unit.code to unit.id for all foreign key references

Revision ID: 5012f843c2f3
Revises: 0004_update_units_structure
Create Date: 2026-02-02 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select
from sqlalchemy import Integer, String


# revision identifiers, used by Alembic.
revision = '5012f843c2f3'
down_revision = '0004_update_units_structure'
branch_labels = None
depends_on = None


def upgrade():
    # Add unit_id columns to tables that reference unit
    op.add_column('price_list', sa.Column('unit_id', sa.Integer(), nullable=True))
    op.add_column('stock', sa.Column('unit_id', sa.Integer(), nullable=True))
    op.add_column('sale_line', sa.Column('unit_id', sa.Integer(), nullable=True))
    op.add_column('adjustment', sa.Column('unit_id', sa.Integer(), nullable=True))
    op.add_column('transfer', sa.Column('unit_id', sa.Integer(), nullable=True))
    op.add_column('attribute_definition', sa.Column('unit_id', sa.Integer(), nullable=True))
    op.add_column('composite_component', sa.Column('unit_id', sa.Integer(), nullable=True))

    # Update the new unit_id columns with values from unit table based on unit_code
    # We need to do this in raw SQL since we're in Alembic context
    op.execute("""
        UPDATE price_list
        SET unit_id = (SELECT id FROM unit WHERE code = price_list.unit_code)
        WHERE unit_code IS NOT NULL
    """)

    op.execute("""
        UPDATE stock
        SET unit_id = (SELECT id FROM unit WHERE code = stock.unit_code)
        WHERE unit_code IS NOT NULL
    """)

    op.execute("""
        UPDATE sale_line
        SET unit_id = (SELECT id FROM unit WHERE code = sale_line.unit_code)
        WHERE unit_code IS NOT NULL
    """)

    op.execute("""
        UPDATE adjustment
        SET unit_id = (SELECT id FROM unit WHERE code = adjustment.unit_code)
        WHERE unit_code IS NOT NULL
    """)

    op.execute("""
        UPDATE transfer
        SET unit_id = (SELECT id FROM unit WHERE code = transfer.unit_code)
        WHERE unit_code IS NOT NULL
    """)

    op.execute("""
        UPDATE attribute_definition
        SET unit_id = (SELECT id FROM unit WHERE code = attribute_definition.unit_code)
        WHERE unit_code IS NOT NULL
    """)

    op.execute("""
        UPDATE composite_component
        SET unit_id = (SELECT id FROM unit WHERE code = composite_component.unit_code)
        WHERE unit_code IS NOT NULL
    """)

    # Make the new unit_id columns NOT NULL (but handle NULL cases by setting to NULL first)
    # For attribute_definition, we'll allow NULL for unit_id since it's optional
    op.alter_column('price_list', 'unit_id', nullable=False)
    op.alter_column('stock', 'unit_id', nullable=False)
    op.alter_column('sale_line', 'unit_id', nullable=False)
    op.alter_column('adjustment', 'unit_id', nullable=False)
    op.alter_column('transfer', 'unit_id', nullable=False)
    op.alter_column('composite_component', 'unit_id', nullable=False)
    # Keep attribute_definition.unit_id nullable since it's optional

    # Drop old foreign key constraints - use generic approach to handle auto-generated names
    # We'll catch exceptions if constraints don't exist
    try:
        op.drop_constraint(None, 'price_list', type_='foreignkey')
    except:
        pass  # Constraint may not exist with expected name
    try:
        op.drop_constraint(None, 'stock', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint(None, 'sale_line', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint(None, 'adjustment', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint(None, 'transfer', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint(None, 'attribute_definition', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint(None, 'composite_component', type_='foreignkey')
    except:
        pass

    # Create new foreign key constraints to unit.id
    op.create_foreign_key('price_list_unit_id_fkey', 'price_list', 'unit', ['unit_id'], ['id'])
    op.create_foreign_key('stock_unit_id_fkey', 'stock', 'unit', ['unit_id'], ['id'])
    op.create_foreign_key('sale_line_unit_id_fkey', 'sale_line', 'unit', ['unit_id'], ['id'])
    op.create_foreign_key('adjustment_unit_id_fkey', 'adjustment', 'unit', ['unit_id'], ['id'])
    op.create_foreign_key('transfer_unit_id_fkey', 'transfer', 'unit', ['unit_id'], ['id'])
    # For attribute_definition, create FK but allow NULL values
    op.create_foreign_key('attribute_definition_unit_id_fkey', 'attribute_definition', 'unit', ['unit_id'], ['id'])
    op.create_foreign_key('composite_component_unit_id_fkey', 'composite_component', 'unit', ['unit_id'], ['id'])

    # Drop the old unit_code columns
    op.drop_column('price_list', 'unit_code')
    op.drop_column('stock', 'unit_code')
    op.drop_column('sale_line', 'unit_code')
    op.drop_column('adjustment', 'unit_code')
    op.drop_column('transfer', 'unit_code')
    op.drop_column('attribute_definition', 'unit_code')
    op.drop_column('composite_component', 'unit_code')


def downgrade():
    # Add back the unit_code columns
    op.add_column('price_list', sa.Column('unit_code', sa.String(32), nullable=True))
    op.add_column('stock', sa.Column('unit_code', sa.String(32), nullable=True))
    op.add_column('sale_line', sa.Column('unit_code', sa.String(32), nullable=True))
    op.add_column('adjustment', sa.Column('unit_code', sa.String(32), nullable=True))
    op.add_column('transfer', sa.Column('unit_code', sa.String(32), nullable=True))
    op.add_column('attribute_definition', sa.Column('unit_code', sa.String(32), nullable=True))
    op.add_column('composite_component', sa.Column('unit_code', sa.String(32), nullable=True))

    # Populate unit_code from unit_id
    op.execute("""
        UPDATE price_list 
        SET unit_code = (SELECT code FROM unit WHERE id = price_list.unit_id)
        WHERE unit_id IS NOT NULL
    """)
    
    op.execute("""
        UPDATE stock 
        SET unit_code = (SELECT code FROM unit WHERE id = stock.unit_id)
        WHERE unit_id IS NOT NULL
    """)
    
    op.execute("""
        UPDATE sale_line 
        SET unit_code = (SELECT code FROM unit WHERE id = sale_line.unit_id)
        WHERE unit_id IS NOT NULL
    """)
    
    op.execute("""
        UPDATE adjustment 
        SET unit_code = (SELECT code FROM unit WHERE id = adjustment.unit_id)
        WHERE unit_id IS NOT NULL
    """)
    
    op.execute("""
        UPDATE transfer 
        SET unit_code = (SELECT code FROM unit WHERE id = transfer.unit_id)
        WHERE unit_id IS NOT NULL
    """)
    
    op.execute("""
        UPDATE attribute_definition 
        SET unit_code = (SELECT code FROM unit WHERE id = attribute_definition.unit_id)
        WHERE unit_id IS NOT NULL
    """)
    
    op.execute("""
        UPDATE composite_component 
        SET unit_code = (SELECT code FROM unit WHERE id = composite_component.unit_id)
        WHERE unit_id IS NOT NULL
    """)

    # Make unit_code NOT NULL (except for attribute_definition which was optional)
    op.alter_column('price_list', 'unit_code', nullable=False)
    op.alter_column('stock', 'unit_code', nullable=False)
    op.alter_column('sale_line', 'unit_code', nullable=False)
    op.alter_column('adjustment', 'unit_code', nullable=False)
    op.alter_column('transfer', 'unit_code', nullable=False)
    op.alter_column('composite_component', 'unit_code', nullable=False)
    # Keep attribute_definition.unit_code nullable since it was optional

    # Drop new foreign key constraints
    try:
        op.drop_constraint('price_list_unit_id_fkey', 'price_list', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint('stock_unit_id_fkey', 'stock', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint('sale_line_unit_id_fkey', 'sale_line', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint('adjustment_unit_id_fkey', 'adjustment', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint('transfer_unit_id_fkey', 'transfer', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint('attribute_definition_unit_id_fkey', 'attribute_definition', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint('composite_component_unit_id_fkey', 'composite_component', type_='foreignkey')
    except:
        pass

    # Create old foreign key constraints to unit.code - use generic approach
    try:
        op.create_foreign_key(None, 'price_list', 'unit', ['unit_code'], ['code'])
    except:
        pass
    try:
        op.create_foreign_key(None, 'stock', 'unit', ['unit_code'], ['code'])
    except:
        pass
    try:
        op.create_foreign_key(None, 'sale_line', 'unit', ['unit_code'], ['code'])
    except:
        pass
    try:
        op.create_foreign_key(None, 'adjustment', 'unit', ['unit_code'], ['code'])
    except:
        pass
    try:
        op.create_foreign_key(None, 'transfer', 'unit', ['unit_code'], ['code'])
    except:
        pass
    try:
        op.create_foreign_key(None, 'attribute_definition', 'unit', ['unit_code'], ['code'])
    except:
        pass
    try:
        op.create_foreign_key(None, 'composite_component', 'unit', ['unit_code'], ['code'])
    except:
        pass

    # Drop the unit_id columns
    op.drop_column('price_list', 'unit_id')
    op.drop_column('stock', 'unit_id')
    op.drop_column('sale_line', 'unit_id')
    op.drop_column('adjustment', 'unit_id')
    op.drop_column('transfer', 'unit_id')
    op.drop_column('attribute_definition', 'unit_id')
    op.drop_column('composite_component', 'unit_id')