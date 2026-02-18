"""fix unit.id default sequence for legacy databases

Revision ID: 20260218_150000
Revises: 20260218_140000
Create Date: 2026-02-18 15:00:00.000000
"""

from alembic import op


revision = "20260218_150000"
down_revision = "20260218_140000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            seq_name text;
            max_id bigint;
        BEGIN
            SELECT pg_get_serial_sequence('unit', 'id') INTO seq_name;

            IF seq_name IS NULL THEN
                IF to_regclass('unit_id_seq') IS NULL THEN
                    EXECUTE 'CREATE SEQUENCE unit_id_seq';
                END IF;
                EXECUTE 'ALTER SEQUENCE unit_id_seq OWNED BY unit.id';
                EXECUTE 'ALTER TABLE unit ALTER COLUMN id SET DEFAULT nextval(''unit_id_seq'')';
                seq_name := 'unit_id_seq';
            END IF;

            EXECUTE 'SELECT COALESCE(MAX(id), 0) FROM unit' INTO max_id;
            EXECUTE format('SELECT setval(%L, %s, false)', seq_name, max_id + 1);
        END $$;
        """
    )


def downgrade() -> None:
    # Keep default sequence in place to avoid breaking inserts.
    pass
