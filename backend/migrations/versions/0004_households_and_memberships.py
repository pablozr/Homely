"""Create households, memberships, activity events and idempotency records.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "households",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column(
            "default_due_time",
            sa.Time(),
            nullable=False,
            server_default=sa.text("'20:00:00'"),
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deactivated_at", sa.DateTime(timezone=True)),
        sa.Column("deactivated_by", sa.Uuid()),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_households_name_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_households_created_by_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["deactivated_by"],
            ["users.id"],
            name="fk_households_deactivated_by_users",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_households_created_by", "households", ["created_by"])

    op.create_table(
        "household_members",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("left_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "role IN ('OWNER', 'MEMBER')",
            name="ck_household_members_role",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_household_members_status",
        ),
        sa.CheckConstraint(
            "(status = 'ACTIVE' AND left_at IS NULL)"
            " OR (status = 'INACTIVE' AND left_at IS NOT NULL)",
            name="ck_household_members_status_left_at",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_household_members_household_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_household_members_user_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_household_members_user_id", "household_members", ["user_id"]
    )
    op.create_index(
        "ix_household_members_household_id", "household_members", ["household_id"]
    )
    op.create_index(
        "uq_household_members_active_household_user",
        "household_members",
        ["household_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_household_members_active_owner",
        "household_members",
        ["household_id"],
        unique=True,
        postgresql_where=sa.text("role = 'OWNER' AND status = 'ACTIVE'"),
    )

    op.add_column("users", sa.Column("last_household_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_users_last_household_id_households",
        "users",
        "households",
        ["last_household_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "activity_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid()),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_activity_events_household_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_activity_events_actor_user_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_activity_events_household_occurred_at",
        "activity_events",
        ["household_id", "occurred_at"],
    )
    op.create_index(
        "ix_activity_events_entity",
        "activity_events",
        ["entity_type", "entity_id"],
    )

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid()),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("resource_id", sa.Uuid()),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_idempotency_records_user_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_idempotency_records_household_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "user_id",
            "household_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_records_scope",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "ix_idempotency_records_expires_at",
        "idempotency_records",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_idempotency_records_expires_at", table_name="idempotency_records"
    )
    op.drop_table("idempotency_records")

    op.drop_index(
        "ix_activity_events_entity", table_name="activity_events"
    )
    op.drop_index(
        "ix_activity_events_household_occurred_at", table_name="activity_events"
    )
    op.drop_table("activity_events")

    op.drop_index(
        "uq_household_members_active_owner", table_name="household_members"
    )
    op.drop_index(
        "uq_household_members_active_household_user", table_name="household_members"
    )
    op.drop_index(
        "ix_household_members_household_id", table_name="household_members"
    )
    op.drop_index("ix_household_members_user_id", table_name="household_members")
    op.drop_table("household_members")

    op.drop_constraint(
        "fk_users_last_household_id_households", "users", type_="foreignkey"
    )
    op.drop_column("users", "last_household_id")

    op.drop_index("ix_households_created_by", table_name="households")
    op.drop_table("households")
