"""add calculator registry with versions

Revision ID: 20260218_130000
Revises: 20260218_120000
Create Date: 2026-02-18 13:00:00.000000
"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa


revision = "20260218_130000"
down_revision = "20260218_120000"
branch_labels = None
depends_on = None


def _legacy_code(file_name: str, class_name: str) -> str:
    base = f"legacy_{file_name}_{class_name}".lower()
    normalized = re.sub(r"[^a-z0-9_]+", "_", base).strip("_")
    return normalized[:120] if normalized else "legacy_calculator"


def upgrade() -> None:
    op.create_table(
        "price_calculator",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False, comment="Stable calculator code"),
        sa.Column("name", sa.String(length=255), nullable=False, comment="Display name"),
        sa.Column("description", sa.Text(), nullable=True, comment="Calculator description"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_price_calculator_code"),
    )

    op.create_table(
        "price_calculator_version",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("calculator_id", sa.Integer(), nullable=False, comment="Calculator registry entry"),
        sa.Column("version", sa.String(length=64), nullable=False, comment="Semantic/functional version"),
        sa.Column("file_path", sa.String(length=255), nullable=False, comment="Python module file path"),
        sa.Column("class_name", sa.String(length=255), nullable=False, comment="Python calculator class"),
        sa.Column("source_hash", sa.String(length=128), nullable=False, comment="SHA256 hash of source file"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("changelog", sa.Text(), nullable=True, comment="Version changelog"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["calculator_id"], ["price_calculator.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("calculator_id", "version", name="uq_price_calculator_version_unique"),
    )
    op.create_index(
        "ix_price_calculator_version_calculator_active",
        "price_calculator_version",
        ["calculator_id", "is_active"],
    )

    op.add_column(
        "price_list_revision",
        sa.Column(
            "calculator_version_id",
            sa.Integer(),
            nullable=True,
            comment="Resolved calculator version id for mode=calculator",
        ),
    )
    op.add_column(
        "price_list_revision",
        sa.Column(
            "calculator_name_snapshot",
            sa.String(length=255),
            nullable=True,
            comment="Calculator display name at calculation time",
        ),
    )
    op.add_column(
        "price_list_revision",
        sa.Column(
            "calculator_version_snapshot",
            sa.String(length=64),
            nullable=True,
            comment="Calculator version at calculation time",
        ),
    )
    op.add_column(
        "price_list_revision",
        sa.Column(
            "calculator_source_hash_snapshot",
            sa.String(length=128),
            nullable=True,
            comment="Calculator source hash at calculation time",
        ),
    )
    op.create_foreign_key(
        "fk_price_list_revision_calculator_version_id",
        "price_list_revision",
        "price_calculator_version",
        ["calculator_version_id"],
        ["id"],
    )
    op.create_index("ix_price_list_revision_calculator_version_id", "price_list_revision", ["calculator_version_id"])

    bind = op.get_bind()
    price_list_revision = sa.table(
        "price_list_revision",
        sa.column("id", sa.Integer()),
        sa.column("mode", sa.String()),
        sa.column("calculator_file", sa.String()),
        sa.column("calculator_class", sa.String()),
        sa.column("calculator_version_id", sa.Integer()),
    )
    price_calculator = sa.table(
        "price_calculator",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    price_calculator_version = sa.table(
        "price_calculator_version",
        sa.column("id", sa.Integer()),
        sa.column("calculator_id", sa.Integer()),
        sa.column("version", sa.String()),
        sa.column("file_path", sa.String()),
        sa.column("class_name", sa.String()),
        sa.column("source_hash", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("changelog", sa.Text()),
    )

    legacy_rows = bind.execute(
        sa.select(
            price_list_revision.c.calculator_file,
            price_list_revision.c.calculator_class,
        )
        .where(
            price_list_revision.c.mode == "calculator",
            price_list_revision.c.calculator_file.is_not(None),
            price_list_revision.c.calculator_class.is_not(None),
        )
        .distinct()
    ).all()

    used_codes: set[str] = set()
    for file_name, class_name in legacy_rows:
        if not file_name or not class_name:
            continue
        base_code = _legacy_code(file_name, class_name)
        code = base_code
        index = 1
        while code in used_codes or bind.execute(
            sa.select(price_calculator.c.id).where(price_calculator.c.code == code)
        ).scalar_one_or_none():
            index += 1
            code = f"{base_code}_{index}"
        used_codes.add(code)

        calc_id = bind.execute(
            sa.insert(price_calculator)
            .values(
                code=code,
                name=str(class_name),
                description=f"Legacy calculator migrated from {file_name}:{class_name}",
                is_active=True,
            )
            .returning(price_calculator.c.id)
        ).scalar_one()

        version_id = bind.execute(
            sa.insert(price_calculator_version)
            .values(
                calculator_id=calc_id,
                version="legacy",
                file_path=str(file_name),
                class_name=str(class_name),
                source_hash="legacy",
                is_active=True,
                changelog="Migrated from pre-versioned calculator configuration",
            )
            .returning(price_calculator_version.c.id)
        ).scalar_one()

        bind.execute(
            sa.text(
                """
                UPDATE price_list_revision
                SET calculator_version_id = :version_id,
                    calculator_name_snapshot = :calc_name,
                    calculator_version_snapshot = 'legacy',
                    calculator_source_hash_snapshot = 'legacy'
                WHERE mode = 'calculator'
                  AND calculator_file = :file_name
                  AND calculator_class = :class_name
                  AND calculator_version_id IS NULL
                """
            ),
            {
                "version_id": version_id,
                "calc_name": str(class_name),
                "file_name": str(file_name),
                "class_name": str(class_name),
            },
        )


def downgrade() -> None:
    op.drop_index("ix_price_list_revision_calculator_version_id", table_name="price_list_revision")
    op.drop_constraint("fk_price_list_revision_calculator_version_id", "price_list_revision", type_="foreignkey")
    op.drop_column("price_list_revision", "calculator_source_hash_snapshot")
    op.drop_column("price_list_revision", "calculator_version_snapshot")
    op.drop_column("price_list_revision", "calculator_name_snapshot")
    op.drop_column("price_list_revision", "calculator_version_id")

    op.drop_index("ix_price_calculator_version_calculator_active", table_name="price_calculator_version")
    op.drop_table("price_calculator_version")
    op.drop_table("price_calculator")
