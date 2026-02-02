"""Update existing tables to support product-dependent unit conversion system

Revision ID: 0004_update_units_structure
Revises: 0003_remove_is_composite
Create Date: 2026-02-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from decimal import Decimal


# revision identifiers, used by Alembic.
revision = '0004_update_units_structure'
down_revision = '0003_remove_is_composite'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add unit_type and is_discrete columns to existing unit table
    # Check if columns already exist
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'unit' 
        AND column_name IN ('unit_type', 'is_discrete')
    """))
    existing_columns = [row[0] for row in result.fetchall()]
    
    if 'unit_type' not in existing_columns:
        op.add_column('unit', sa.Column('unit_type', sa.String(length=20), nullable=True))
    if 'is_discrete' not in existing_columns:
        op.add_column('unit', sa.Column('is_discrete', sa.Boolean(), server_default=sa.text('true'), nullable=True))
    
    # Update existing units to have default values
    op.execute("UPDATE unit SET unit_type = COALESCE(unit_type, 'base')")
    op.execute("UPDATE unit SET is_discrete = COALESCE(is_discrete, true)")
    
    # Make columns NOT NULL
    op.alter_column('unit', 'unit_type', nullable=False)
    op.alter_column('unit', 'is_discrete', nullable=False)
    
    # 2. Create product_unit table for product-specific units
    if not table_exists('product_unit'):
        op.create_table(
            'product_unit',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('unit_id', sa.Integer(), nullable=False),
            sa.Column('ratio_to_base', sa.Numeric(precision=18, scale=6), nullable=False),
            sa.Column('discrete_step', sa.Numeric(precision=10, scale=6), nullable=True),
            sa.ForeignKeyConstraint(['product_id'], ['product.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['unit_id'], ['unit.id'], ondelete='RESTRICT'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('product_id', 'unit_id')
        )

        # Create indexes
        op.create_index('ix_product_unit_product_id', 'product_unit', ['product_id'])
        op.create_index('ix_product_unit_unit_id', 'product_unit', ['unit_id'])

    # 3. Add base_unit_id column to product table
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'product' 
        AND column_name = 'base_unit_id'
    """))
    if not result.fetchone():
        op.add_column('product', sa.Column('base_unit_id', sa.Integer(), nullable=True))

        # 4. Populate base_unit_id based on base_unit_code
        # First, ensure all units referenced in base_unit_code exist in unit table
        op.execute("""
            INSERT INTO unit (code, description, unit_type, is_discrete)
            SELECT DISTINCT p.base_unit_code, p.base_unit_code, 'base', true
            FROM product p
            WHERE p.base_unit_code IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM unit u WHERE u.code = p.base_unit_code
            )
        """)
        
        # Update base_unit_id for existing products
        op.execute("""
            UPDATE product 
            SET base_unit_id = unit.id
            FROM unit
            WHERE product.base_unit_code = unit.code
        """)
        
        # 5. Add foreign key constraint for base_unit_id
        op.create_foreign_key(
            'fk_product_base_unit_id_unit',
            'product',
            'unit',
            ['base_unit_id'],
            ['id']
        )

        # 6. Make base_unit_id NOT NULL and drop base_unit_code
        # First ensure all products have base_unit_id set
        op.execute("""
            UPDATE product 
            SET base_unit_id = (SELECT id FROM unit LIMIT 1)
            WHERE base_unit_id IS NULL AND (SELECT COUNT(*) FROM unit) > 0
        """)
        
        # Add NOT NULL constraint
        op.alter_column('product', 'base_unit_id', nullable=False)

        # 7. Migrate existing unit_conversion data to product_unit table
        # First, let's create product_unit entries for base units with ratio 1.0
        op.execute("""
            INSERT INTO product_unit (product_id, unit_id, ratio_to_base, discrete_step)
            SELECT p.id, p.base_unit_id, 1.0, NULL
            FROM product p
            WHERE p.base_unit_id IS NOT NULL
            ON CONFLICT (product_id, unit_id) DO NOTHING
        """)
        
        # Migrate existing unit_conversion data to product_unit table if table exists
        if table_exists('unit_conversion'):
            op.execute("""
                INSERT INTO product_unit (product_id, unit_id, ratio_to_base, discrete_step)
                SELECT p.id, u.id, uc.ratio, NULL
                FROM unit_conversion uc
                JOIN unit u ON u.code = uc.to_unit
                JOIN product p ON p.base_unit_code = uc.from_unit
                WHERE p.base_unit_id IS NOT NULL
                ON CONFLICT (product_id, unit_id) DO NOTHING
            """)
            
            # Also handle reverse conversions (to_unit as base)
            op.execute("""
                INSERT INTO product_unit (product_id, unit_id, ratio_to_base, discrete_step)
                SELECT p.id, u.id, 1.0/uc.ratio, NULL
                FROM unit_conversion uc
                JOIN unit u ON u.code = uc.from_unit
                JOIN product p ON p.base_unit_code = uc.to_unit
                WHERE p.base_unit_id IS NOT NULL AND uc.ratio != 0
                ON CONFLICT (product_id, unit_id) DO NOTHING
            """)

        # 8. Drop old base_unit_code column and unit_conversion table if they exist
        # Check if foreign key constraint exists before dropping
        try:
            op.drop_constraint('product_base_unit_code_fkey', 'product', type_='foreignkey')
        except:
            pass  # Constraint may not exist
            
        # Check if column exists before dropping
        result = connection.execute(sa.text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'product' 
            AND column_name = 'base_unit_code'
        """))
        if result.fetchone():
            op.drop_column('product', 'base_unit_code')
            
        if table_exists('unit_conversion'):
            op.drop_table('unit_conversion')

        # 9. Add check constraint to ensure base unit has ratio_to_base = 1.0
        # Note: PostgreSQL doesn't support conditional CHECK constraints easily
        # We'll implement this logic in the application layer instead


def downgrade():
    # Reverse the migration
    connection = op.get_bind()
    
    # 1. Recreate unit_conversion table if it doesn't exist
    if not table_exists('unit_conversion'):
        op.create_table(
            'unit_conversion',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('from_unit', sa.String(length=32), nullable=False),
            sa.Column('to_unit', sa.String(length=32), nullable=False),
            sa.Column('ratio', sa.Numeric(precision=10, scale=6), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
    
    # 3. Add back base_unit_code column if it doesn't exist
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'product' 
        AND column_name = 'base_unit_code'
    """))
    if not result.fetchone():
        op.add_column('product', sa.Column('base_unit_code', sa.String(length=32), nullable=True))
        
        # Update base_unit_code from base_unit_id
        op.execute("""
            UPDATE product 
            SET base_unit_code = unit.code
            FROM unit
            WHERE product.base_unit_id = unit.id
        """)
        
        # Add foreign key constraint for base_unit_code
        op.create_foreign_key(
            'product_base_unit_code_fkey',
            'product',
            'unit',
            ['base_unit_code'],
            ['code']
        )
        
        # Make base_unit_code NOT NULL
        op.alter_column('product', 'base_unit_code', nullable=False)
    
    # 8. Drop foreign key constraint and base_unit_id column
    try:
        op.drop_constraint('fk_product_base_unit_id_unit', 'product', type_='foreignkey')
    except:
        pass  # Constraint may not exist
        
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'product' 
        AND column_name = 'base_unit_id'
    """))
    if result.fetchone():
        op.drop_column('product', 'base_unit_id')
    
    # 9. Drop product_unit table
    if table_exists('product_unit'):
        op.drop_table('product_unit')
    
    # 10. Drop new columns from unit table
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'unit' 
        AND column_name IN ('is_discrete', 'unit_type')
    """))
    column_names = [row[0] for row in result.fetchall()]
    
    if 'is_discrete' in column_names:
        op.drop_column('unit', 'is_discrete')
    if 'unit_type' in column_names:
        op.drop_column('unit', 'unit_type')


def table_exists(table_name):
    """Check if a table exists in the database"""
    connection = op.get_bind()
    result = connection.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = :table_name
            );
        """),
        {"table_name": table_name}
    )
    return result.fetchone()[0]