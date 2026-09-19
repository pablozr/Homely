"""Create tasks and task occurrences for standalone household tasks.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_household_members_id_household_id",
        "household_members",
        ["id", "household_id"],
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_tasks_title_not_blank",
        ),
        sa.UniqueConstraint(
            "id",
            "household_id",
            name="uq_tasks_id_household_id",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_tasks_household_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_tasks_created_by",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_tasks_household_id", "tasks", ["household_id"])

    op.create_table(
        "task_occurrences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("assignee_membership_id", sa.Uuid()),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("due_timezone", sa.String(length=64)),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_by", sa.Uuid()),
        sa.CheckConstraint(
            "status IN ('PENDING', 'DONE', 'SKIPPED', 'CANCELLED')",
            name="ck_task_occurrences_status",
        ),
        sa.CheckConstraint(
            "(due_at IS NULL) = (due_timezone IS NULL)",
            name="ck_task_occurrences_due_pair",
        ),
        sa.CheckConstraint(
            "(cancelled_at IS NULL) = (cancelled_by IS NULL)",
            name="ck_task_occurrences_cancelled_pair",
        ),
        sa.CheckConstraint(
            "(status = 'CANCELLED') = (cancelled_at IS NOT NULL)",
            name="ck_task_occurrences_cancelled_equivalence",
        ),
        sa.ForeignKeyConstraint(
            ["task_id", "household_id"],
            ["tasks.id", "tasks.household_id"],
            name="fk_task_occurrences_task_household",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assignee_membership_id", "household_id"],
            ["household_members.id", "household_members.household_id"],
            name="fk_task_occurrences_assignee_household",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_task_occurrences_household_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_task_occurrences_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by"],
            ["users.id"],
            name="fk_task_occurrences_cancelled_by",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_task_occurrences_household_id",
        "task_occurrences",
        ["household_id"],
    )
    op.create_index(
        "ix_task_occurrences_task_id",
        "task_occurrences",
        ["task_id"],
    )
    op.create_index(
        "ix_task_occurrences_assignee_membership_id",
        "task_occurrences",
        ["assignee_membership_id"],
    )
    op.create_index(
        "ix_task_occurrences_household_pending",
        "task_occurrences",
        ["household_id", "due_at", "created_at", "id"],
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_task_occurrences_household_pending",
        table_name="task_occurrences",
    )
    op.drop_index(
        "ix_task_occurrences_assignee_membership_id",
        table_name="task_occurrences",
    )
    op.drop_index("ix_task_occurrences_task_id", table_name="task_occurrences")
    op.drop_index(
        "ix_task_occurrences_household_id", table_name="task_occurrences"
    )
    op.drop_table("task_occurrences")

    op.drop_index("ix_tasks_household_id", table_name="tasks")
    op.drop_table("tasks")

    op.drop_constraint(
        "uq_household_members_id_household_id",
        "household_members",
        type_="unique",
    )
