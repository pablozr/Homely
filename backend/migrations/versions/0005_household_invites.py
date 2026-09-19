"""Add household invites, acceptance attempts and single active owner guard.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "household_invites",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_by", sa.Uuid()),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("accepted_by", sa.Uuid()),
        sa.Column("accepted_membership_id", sa.Uuid()),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_household_invites_token_hash",
        ),
        sa.CheckConstraint(
            "length(token_hash) = 64",
            name="ck_household_invites_token_hash_length",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_household_invites_expires_after_created",
        ),
        sa.CheckConstraint(
            "(revoked_at IS NULL) = (revoked_by IS NULL)",
            name="ck_household_invites_revoked_pair",
        ),
        sa.CheckConstraint(
            "(accepted_at IS NULL) = (accepted_by IS NULL)"
            " AND (accepted_by IS NULL) = (accepted_membership_id IS NULL)",
            name="ck_household_invites_accepted_triplet",
        ),
        sa.CheckConstraint(
            "NOT (accepted_at IS NOT NULL AND revoked_at IS NOT NULL)",
            name="ck_household_invites_not_accepted_and_revoked",
        ),
        sa.ForeignKeyConstraint(
            ["household_id"],
            ["households.id"],
            name="fk_household_invites_household_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_household_invites_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by"],
            ["users.id"],
            name="fk_household_invites_revoked_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by"],
            ["users.id"],
            name="fk_household_invites_accepted_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_membership_id"],
            ["household_members.id"],
            name="fk_household_invites_accepted_membership_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_household_invites_outstanding",
        "household_invites",
        ["household_id", "created_at"],
        postgresql_where=sa.text("revoked_at IS NULL AND accepted_at IS NULL"),
    )

    op.create_table(
        "household_invite_accept_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("requested_ip", sa.String(length=45)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_household_invite_accept_attempts_user_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_household_invite_accept_attempts_user_created_at",
        "household_invite_accept_attempts",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_household_invite_accept_attempts_ip_created_at",
        "household_invite_accept_attempts",
        ["requested_ip", "created_at"],
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM households h
                LEFT JOIN household_members hm
                  ON hm.household_id = h.id
                 AND hm.role = 'OWNER'
                 AND hm.status = 'ACTIVE'
                GROUP BY h.id
                HAVING count(hm.id) <> 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot enforce a single active owner: existing households violate the invariant';
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_household_require_single_active_owner()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            target_household uuid;
            active_owners integer;
        BEGIN
            IF TG_TABLE_NAME = 'households' THEN
                target_household := NEW.id;
            ELSE
                target_household := COALESCE(NEW.household_id, OLD.household_id);
            END IF;

            SELECT count(*)
            INTO active_owners
            FROM household_members
            WHERE household_id = target_household
              AND role = 'OWNER'
              AND status = 'ACTIVE';

            IF active_owners <> 1 THEN
                RAISE EXCEPTION
                    'household % must have exactly one active owner',
                    target_household
                    USING ERRCODE = 'check_violation';
            END IF;

            RETURN NULL;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_household_members_require_single_active_owner
        AFTER INSERT OR UPDATE OR DELETE ON household_members
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION fn_household_require_single_active_owner();
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_households_require_single_active_owner
        AFTER INSERT OR DELETE ON households
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION fn_household_require_single_active_owner();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_households_require_single_active_owner ON households"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_household_members_require_single_active_owner"
        " ON household_members"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_household_require_single_active_owner()")

    op.drop_index(
        "ix_household_invite_accept_attempts_ip_created_at",
        table_name="household_invite_accept_attempts",
    )
    op.drop_index(
        "ix_household_invite_accept_attempts_user_created_at",
        table_name="household_invite_accept_attempts",
    )
    op.drop_table("household_invite_accept_attempts")

    op.drop_index(
        "ix_household_invites_outstanding",
        table_name="household_invites",
    )
    op.drop_table("household_invites")
