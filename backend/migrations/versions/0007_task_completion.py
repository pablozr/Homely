"""Add task occurrence completion authorship and timestamp.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task_occurrences",
        sa.Column("completed_by", sa.Uuid()),
    )
    op.add_column(
        "task_occurrences",
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        """
        UPDATE task_occurrences
        SET completed_by = created_by,
            completed_at = updated_at
        WHERE status = 'DONE'
        """
    )
    op.create_foreign_key(
        "fk_task_occurrences_completed_by",
        "task_occurrences",
        "users",
        ["completed_by"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_task_occurrences_completed_pair",
        "task_occurrences",
        "(completed_at IS NULL) = (completed_by IS NULL)",
    )
    op.create_check_constraint(
        "ck_task_occurrences_completed_equivalence",
        "task_occurrences",
        "(status = 'DONE') = (completed_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_task_occurrences_completed_equivalence",
        "task_occurrences",
        type_="check",
    )
    op.drop_constraint(
        "ck_task_occurrences_completed_pair",
        "task_occurrences",
        type_="check",
    )
    op.drop_constraint(
        "fk_task_occurrences_completed_by",
        "task_occurrences",
        type_="foreignkey",
    )
    op.drop_column("task_occurrences", "completed_at")
    op.drop_column("task_occurrences", "completed_by")
