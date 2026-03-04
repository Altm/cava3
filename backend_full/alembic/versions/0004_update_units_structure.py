"""Complete migration to use ID as primary key in unit table and update all foreign key references

Revision ID: 0004_update_units_structure
Revises: 0003_remove_is_composite
Create Date: 2026-02-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '0004_update_units_structure'
down_revision = '0003_remove_is_composite'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
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


def column_exists(table_name: str, column_name: str) -> bool:
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


def get_fk_constraints_to_unit(table_name: str, column_name: str) -> list[str]:
    """Get all FK constraint names that reference unit table via given column"""
    connection = op.get_bind()
    result = connection.execute(
        text("""
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class tbl ON tbl.oid = con.conrelid
            JOIN pg_class ref_tbl ON ref_tbl.oid = con.confrelid
            JOIN pg_attribute att ON att.attrelid = tbl.oid AND att.attnum = ANY(con.conkey)
            WHERE tbl.relname = :table_name
            AND ref_tbl.relname = 'unit'
            AND att.attname = :col_name
        """),
        {"table_name": table_name, "col_name": column_name}
    )
    return [row[0] for row in result.fetchall()]


def drop_fk_constraint(table_name: str, constraint_name: str) -> None:
    """Safely drop a FK constraint if it exists"""
    try:
        op.drop_constraint(constraint_name, table_name, type_='foreignkey')
    except Exception:
        pass


def upgrade():
    # ============================================================
    # Step 1: Add id column to unit table
    # ============================================================
    if not column_exists('unit', 'id'):
        op.execute("ALTER TABLE unit ADD COLUMN id SERIAL")
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

    op.alter_column('unit', 'id', nullable=False)

    # ============================================================
    # Step 2: Drop all FK constraints referencing unit.code
    # ============================================================
    fks_to_drop = [
        ('unit_conversion', 'from_unit'),
        ('unit_conversion', 'to_unit'),
        ('product', 'base_unit_code'),
        ('composite_component', 'unit_code'),
        ('stock', 'unit_code'),
        ('price_list', 'unit_code'),
        ('sale_line', 'unit_code'),
        ('adjustment', 'unit_code'),
        ('transfer', 'unit_code'),
        ('attribute_definition', 'unit_code'),
    ]

    for table_name, col_name in fks_to_drop:
        if table_exists(table_name) and column_exists(table_name, col_name):
            constraints = get_fk_constraints_to_unit(table_name, col_name)
            for constraint_name in constraints:
                drop_fk_constraint(table_name, constraint_name)

    # ============================================================
    # Step 3: Add unit_type and is_discrete columns to unit table
    # ============================================================
    if not column_exists('unit', 'unit_type'):
        op.add_column('unit', sa.Column('unit_type', sa.String(length=20), nullable=True))
    if not column_exists('unit', 'is_discrete'):
        op.add_column('unit', sa.Column('is_discrete', sa.Boolean(), server_default=sa.text('true'), nullable=True))

    op.execute("UPDATE unit SET unit_type = COALESCE(unit_type, 'base')")
    op.execute("UPDATE unit SET is_discrete = COALESCE(is_discrete, true)")

    op.alter_column('unit', 'unit_type', nullable=False)
    op.alter_column('unit', 'is_discrete', nullable=False)

    # ============================================================
    # Step 4: Change PRIMARY KEY from code to id
    # ============================================================
    # Drop old PK with CASCADE to remove dependent FKs
    op.execute("ALTER TABLE unit DROP CONSTRAINT IF EXISTS unit_pkey CASCADE")
    
    # Drop any other PK that might exist
    result = op.get_bind().execute(text("""
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class tbl ON tbl.oid = con.conrelid
        WHERE tbl.relname = 'unit' AND con.contype = 'p'
    """))
    for row in result.fetchall():
        op.execute(f"ALTER TABLE unit DROP CONSTRAINT IF EXISTS {row[0]} CASCADE")

    op.create_primary_key('pk_unit', 'unit', ['id'])

    # ============================================================
    # Step 5: Create product_unit table
    # ============================================================
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
        op.create_index('ix_product_unit_product_id', 'product_unit', ['product_id'])
        op.create_index('ix_product_unit_unit_id', 'product_unit', ['unit_id'])

    # ============================================================
    # Step 6: Migrate product.base_unit_code -> base_unit_id
    # ============================================================
    if column_exists('product', 'base_unit_id'):
        # Already migrated
        pass
    else:
        op.add_column('product', sa.Column('base_unit_id', sa.Integer(), nullable=True))

        # Ensure all referenced units exist
        op.execute("""
            INSERT INTO unit (code, description, unit_type, is_discrete)
            SELECT DISTINCT p.base_unit_code, p.base_unit_code, 'base', true
            FROM product p
            WHERE p.base_unit_code IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM unit u WHERE u.code = p.base_unit_code)
        """)

        op.execute("""
            UPDATE product
            SET base_unit_id = unit.id
            FROM unit
            WHERE product.base_unit_code = unit.code
        """)

        op.alter_column('product', 'base_unit_id', nullable=False)

        op.create_foreign_key(
            'fk_product_base_unit_id_unit',
            'product', 'unit',
            ['base_unit_id'], ['id']
        )

        op.drop_column('product', 'base_unit_code')

    # ============================================================
    # Step 7: Migrate other tables: unit_code -> unit_id
    # ============================================================
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
        if table_exists(table_name) and column_exists(table_name, col_name):
            new_col_name = col_name.replace('_code', '_id')
            op.add_column(table_name, sa.Column(new_col_name, sa.Integer(), nullable=True))

            op.execute(f"""
                UPDATE {table_name}
                SET {new_col_name} = unit.id
                FROM unit
                WHERE {table_name}.{col_name} = unit.code
            """)

            op.alter_column(table_name, new_col_name, nullable=False)

            fk_name = f'fk_{table_name}_{new_col_name}_unit'
            op.create_foreign_key(fk_name, table_name, 'unit', [new_col_name], ['id'])

            op.drop_column(table_name, col_name)

    # ============================================================
    # Step 8: Migrate unit_conversion -> product_unit
    # ============================================================
    op.execute("""
        INSERT INTO product_unit (product_id, unit_id, ratio_to_base, discrete_step)
        SELECT p.id, p.base_unit_id, 1.0, NULL
        FROM product p
        WHERE p.base_unit_id IS NOT NULL
        ON CONFLICT (product_id, unit_id) DO NOTHING
    """)

    if table_exists('unit_conversion'):
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

        op.execute("""
            INSERT INTO product_unit (product_id, unit_id, ratio_to_base, discrete_step)
            SELECT p.id, u_from.id, 1.0/NULLIF(uc.ratio, 0), NULL
            FROM unit_conversion uc
            JOIN unit u_from ON u_from.code = uc.from_unit
            JOIN unit u_to ON u_to.code = uc.to_unit
            JOIN product p ON p.base_unit_id = u_to.id
            WHERE u_from.id IS NOT NULL AND uc.ratio != 0
            ON CONFLICT (product_id, unit_id) DO NOTHING
        """)

        op.drop_table('unit_conversion')

    # ============================================================
    # Step 9: Add trigger-based constraint for base unit ratio
    # (CHECK constraint with subquery is not supported in PostgreSQL)
    # ============================================================
    # Skip complex constraint - will be enforced at application level


def downgrade():
    """Downgrade is not implemented for this migration."""
    pass
