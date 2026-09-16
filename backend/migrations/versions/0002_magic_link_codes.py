"""Add magic link codes and allow passwordless users.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "password", existing_type=sa.String(length=255), nullable=True)
    op.create_table(
        "magic_link_codes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("requested_ip", sa.String(length=45)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("code_hash", name="uq_magic_link_codes_code_hash"),
    )
    op.create_index(
        "ix_magic_link_codes_email_created_at",
        "magic_link_codes",
        ["email", "created_at"],
    )
    op.create_table(
        "magic_link_exchange_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("requested_ip", sa.String(length=45), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_magic_link_exchange_attempts_ip_created_at",
        "magic_link_exchange_attempts",
        ["requested_ip", "created_at"],
    )
    op.create_index(
        "ix_magic_link_codes_requested_ip_created_at",
        "magic_link_codes",
        ["requested_ip", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_magic_link_exchange_attempts_ip_created_at",
        table_name="magic_link_exchange_attempts",
    )
    op.drop_table("magic_link_exchange_attempts")
    op.drop_index(
        "ix_magic_link_codes_requested_ip_created_at", table_name="magic_link_codes"
    )
    op.drop_index("ix_magic_link_codes_email_created_at", table_name="magic_link_codes")
    op.drop_table("magic_link_codes")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM users WHERE password IS NULL) THEN
                RAISE EXCEPTION 'Cannot downgrade while passwordless users exist';
            END IF;
        END $$;
        """
    )
    op.alter_column("users", "password", existing_type=sa.String(length=255), nullable=False)
