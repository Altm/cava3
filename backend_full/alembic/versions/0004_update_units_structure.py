"""Complete migration to use ID as primary key in unit table and update all foreign key references

Revision ID: 0004_update_units_structure
Revises: 0003_remove_is_composite
Create Date: 2026-02-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from decimal import Decimal


# revision identifiers, used by Alembic.
revision = '0004_update_units_structure'
down_revision = '0003_remove_is_composite'
branch_labels = None
depends_on = None


def table_exists(table_name):
    """Check if a table exists in the database"""
    connection = op.get_bind()
    result = connection.execute(
        text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = :table_name
            );
        """),
        {"table_name": table_name}
    )
    return result.fetchone()[0]


def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    connection = op.get_bind()
    result = connection.execute(
        text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = :table_name 
                AND column_name = :column_name
            );
        """),
        {"table_name": table_name, "column_name": column_name}
    )
    return result.fetchone()[0]


def upgrade():
    # Step 1: Add id column to unit table if it doesn't exist
    if not column_exists('unit', 'id'):
        # Add id column as SERIAL (auto-incrementing integer)
        op.execute("ALTER TABLE unit ADD COLUMN id SERIAL")
        
        # Populate id values based on existing codes to maintain referential integrity
        op.execute("""
            UPDATE unit 
            SET id = subquery.new_id
            FROM (
                SELECT code, ROW_NUMBER() OVER (ORDER BY code) AS new_id
                FROM unit
            ) AS subquery
            WHERE unit.code = subquery.code
        """)
    else:
        # If id column exists, make sure it's populated
        op.execute("""
            UPDATE unit 
            SET id = subquery.new_id
            FROM (
                SELECT code, ROW_NUMBER() OVER (ORDER BY code) AS new_id
                FROM unit
                WHERE id IS NULL
            ) AS subquery
            WHERE unit.code = subquery.code AND unit.id IS NULL
        """)
    
    # Make id NOT NULL
    op.alter_column('unit', 'id', nullable=False)
    
    # Step 2: Temporarily drop all foreign key constraints that reference unit.code
    # We need to collect all FK constraints that reference unit table
    # This is a comprehensive list based on the schema
    fks_to_drop = [
        # Format: (table_name, column_name, constraint_name)
        ('unit_conversion', 'from_unit', 'unitconversion_from_unit_fkey'),
        ('unit_conversion', 'to_unit', 'unitconversion_to_unit_fkey'),
        ('product', 'base_unit_code', 'product_base_unit_code_fkey'),
        ('composite_component', 'unit_code', 'compositecomponent_unit_code_fkey'),
        ('stock', 'unit_code', 'stock_unit_code_fkey'),
        ('price_list', 'unit_code', 'pricelist_unit_code_fkey'),
        ('sale_line', 'unit_code', 'saleline_unit_code_fkey'),
        ('adjustment', 'unit_code', 'adjustment_unit_code_fkey'),
        ('transfer', 'unit_code', 'transfer_unit_code_fkey'),
        ('attribute_definition', 'unit_code', 'attribute_definition_unit_code_fkey'),
    ]

    for table_name, col_name, constraint_name in fks_to_drop:
        if column_exists(table_name, col_name):
            try:
                op.drop_constraint(constraint_name, table_name, type_='foreignkey')
            except Exception:
                # Constraint might not exist or have different name, try alternative names
                try:
                    # Try to find the actual constraint name
                    result = op.get_bind().execute(text("""
                        SELECT con.conname
                        FROM pg_constraint con
                        JOIN pg_class tbl ON tbl.oid = con.conrelid
                        JOIN pg_class ref_tbl ON ref_tbl.oid = con.confrelid
                        JOIN pg_attribute att ON att.attrelid = tbl.oid AND att.attnum = ANY(con.conkey)
                        WHERE tbl.relname = :table_name
                        AND ref_tbl.relname = 'unit'
                        AND att.attname = :col_name
                    """), {"table_name": table_name, "col_name": col_name})
                    constraint_rows = result.fetchall()
                    for row in constraint_rows:
                        try:
                            op.drop_constraint(row[0], table_name, type_='foreignkey')
                        except Exception:
                            pass  # Continue if constraint doesn't exist
                except Exception:
                    # If we can't find or drop the constraint, continue
                    pass
    
    # Step 3: Add unit_type and is_discrete columns to unit table
    if not column_exists('unit', 'unit_type'):
        op.add_column('unit', sa.Column('unit_type', sa.String(length=20), nullable=True))
    if not column_exists('unit', 'is_discrete'):
        op.add_column('unit', sa.Column('is_discrete', sa.Boolean(), server_default=sa.text('true'), nullable=True))
    
    # Update existing units to have default values
    op.execute("UPDATE unit SET unit_type = COALESCE(unit_type, 'base')")
    op.execute("UPDATE unit SET is_discrete = COALESCE(is_discrete, true)")
    
    # Make columns NOT NULL
    op.alter_column('unit', 'unit_type', nullable=False)
    op.alter_column('unit', 'is_discrete', nullable=False)
    
    # Step 4: Create product_unit table for product-specific units
    if not table_exists('product_unit'):
        op.create_table(
            'product_unit',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('unit_id', sa.Integer(), nullable=False),  # Now referencing unit.id
            sa.Column('ratio_to_base', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('discrete_step', sa.Numeric(precision=10, scale=6), nullable=True),
            sa.ForeignKeyConstraint(['product_id'], ['product.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['unit_id'], ['unit.id'], ondelete='RESTRICT'),  # Reference unit.id
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('product_id', 'unit_id')
        )

        # Create indexes
        op.create_index('ix_product_unit_product_id', 'product_unit', ['product_id'])
        op.create_index('ix_product_unit_unit_id', 'product_unit', ['unit_id'])

    # Step 5: Add base_unit_id column to product table (references unit.id)
    connection = op.get_bind()
    result = connection.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'product'
        AND column_name = 'base_unit_id'
    """))
    base_unit_id_exists = result.fetchone() is not None

    if not base_unit_id_exists:
        op.add_column('product', sa.Column('base_unit_id', sa.Integer(), nullable=True))
        
        # Create mapping from existing base_unit_code to new unit.id
        # First, ensure all referenced units exist in unit table
        op.execute("""
            INSERT INTO unit (code, description, unit_type, is_discrete)
            SELECT DISTINCT p.base_unit_code, p.base_unit_code, 'base', true
            FROM product p
            WHERE p.base_unit_code IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM unit u WHERE u.code = p.base_unit_code
            )
        """)
        
        # Update base_unit_id by joining with unit table on code (temporary mapping)
        op.execute("""
            UPDATE product 
            SET base_unit_id = unit.id
            FROM unit
            WHERE product.base_unit_code = unit.code
        """)
        
        # Make base_unit_id NOT NULL
        op.alter_column('product', 'base_unit_id', nullable=False)
        
        # Add foreign key constraint to unit.id
        op.create_foreign_key(
            'fk_product_base_unit_id_unit',
            'product',
            'unit',
            ['base_unit_id'],
            ['id']  # Reference unit.id
        )
        
        # Drop the old base_unit_code column
        op.drop_column('product', 'base_unit_code')
    
    # Step 6: Update other tables to use unit_id instead of unit_code
    # Process each table that has a unit_code column
    tables_with_unit_code = [
        ('composite_component', 'unit_code'),
        ('stock', 'unit_code'),
        ('price_list', 'unit_code'),
        ('sale_line', 'unit_code'),
        ('adjustment', 'unit_code'),
        ('transfer', 'unit_code'),
        ('attribute_definition', 'unit_code'),
    ]
    
    for table_name, col_name in tables_with_unit_code:
        if column_exists(table_name, col_name):
            # Add unit_id column
            new_col_name = col_name.replace('_code', '_id')
            op.add_column(table_name, sa.Column(new_col_name, sa.Integer(), nullable=True))
            
            # Update unit_id based on existing unit_code
            op.execute(f"""
                UPDATE {table_name}
                SET {new_col_name} = unit.id
                FROM unit
                WHERE {table_name}.{col_name} = unit.code
            """)
            
            # Make new column NOT NULL
            op.alter_column(table_name, new_col_name, nullable=False)
            
            # Add foreign key constraint to unit.id
            fk_constraint_name = f'fk_{table_name}_{new_col_name}_unit'
            op.create_foreign_key(
                fk_constraint_name,
                table_name,
                'unit',
                [new_col_name],
                ['id']
            )
            
            # Drop the old unit_code column
            op.drop_column(table_name, col_name)
    
    # Step 7: Change primary key of unit table from code to id
    # First, drop the existing primary key constraint on code
    try:
        op.drop_constraint('unit_pkey', 'unit', type_='primary')
    except Exception:
        # Try to find the actual primary key name
        result = op.get_bind().execute(text("""
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class tbl ON tbl.oid = con.conrelid
            WHERE tbl.relname = 'unit'
            AND con.contype = 'p'
        """))
        pk_rows = result.fetchall()
        for row in pk_rows:
            op.drop_constraint(row[0], 'unit', type_='primary')
    
    # Create new primary key on id column
    op.create_primary_key('pk_unit', 'unit', ['id'])
    
    # Step 8: Migrate existing unit_conversion data to product_unit table
    # Create base mappings first
    op.execute("""
        INSERT INTO product_unit (product_id, unit_id, ratio_to_base, discrete_step)
        SELECT p.id, p.base_unit_id, 1.0, NULL
        FROM product p
        WHERE p.base_unit_id IS NOT NULL
        ON CONFLICT (product_id, unit_id) DO NOTHING
    """)
    
    # Migrate existing unit_conversion data to product_unit table
    if table_exists('unit_conversion'):
        # Create product-unit mappings based on existing global conversions
        op.execute("""
            INSERT INTO product_unit (product_id, unit_id, ratio_to_base, discrete_step)
            SELECT p.id, u_to.id, uc.ratio, NULL
            FROM unit_conversion uc
            JOIN unit u_from ON u_from.code = uc.from_unit
            JOIN unit u_to ON u_to.code = uc.to_unit
            JOIN product p ON p.base_unit_id = u_from.id
            WHERE u_to.id IS NOT NULL
            ON CONFLICT (product_id, unit_id) DO NOTHING
        """)
        
        # Also handle reverse conversions
        op.execute("""
            INSERT INTO product_unit (product_id, unit_id, ratio_to_base, discrete_step)
            SELECT p.id, u_from.id, 1.0/uc.ratio, NULL
            FROM unit_conversion uc
            JOIN unit u_from ON u_from.code = uc.from_unit
            JOIN unit u_to ON u_to.code = uc.to_unit
            JOIN product p ON p.base_unit_id = u_to.id
            WHERE u_from.id IS NOT NULL AND uc.ratio != 0
            ON CONFLICT (product_id, unit_id) DO NOTHING
        """)
        
        # Drop the old unit_conversion table since we're replacing it
        op.drop_table('unit_conversion')

    # Step 9: Add check constraint to ensure base unit has ratio_to_base = 1.0
    op.execute("""
        ALTER TABLE product_unit 
        ADD CONSTRAINT chk_base_unit_ratio 
        CHECK (
            CASE 
                WHEN EXISTS (
                    SELECT 1 FROM product p 
                    WHERE p.id = product_unit.product_id AND p.base_unit_id = product_unit.unit_id
                ) THEN product_unit.ratio_to_base = 1.0
                ELSE TRUE
            END
        )
    """)


def downgrade():
    # Reverse the migration - this is complex and would require careful handling
    # of all the changes made above
    pass