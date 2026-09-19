import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import asyncpg

from core.config.config import settings
from core.logger.logger import logger
from core.security.security import derive_invite_token, hash_invite_token
from schemas.households import (
    household_summary_from_row,
    invite_from_row,
    membership_summary_from_row,
)
from services.households import households_service


OPERATION_CREATE_INVITE = "household_invites.create"
CREATE_INVITE_MESSAGE = "Invite created"
INVITES_MESSAGE = "Invites retrieved"
REVOKE_INVITE_MESSAGE = "Invite revoked"
ACCEPT_INVITE_MESSAGE = "Invite accepted"
INVITE_UNAVAILABLE_MESSAGE = "Invite unavailable"
ACCEPT_RATE_LIMIT_MESSAGE = "Too many invite acceptance attempts"
INVITE_PAYLOAD_FINGERPRINT = sha256(b"household_invites.create").hexdigest()


def invite_url(token: str) -> str:
    return f"{settings.INVITE_DEEP_LINK_BASE}?invite_token={token}"


def unavailable_response() -> dict:
    return {
        "status": False,
        "status_code": 409,
        "message": INVITE_UNAVAILABLE_MESSAGE,
        "data": {},
    }


async def create_invite(
    conn: asyncpg.Connection,
    user_id,
    household_id,
    idempotency_key: str,
) -> dict:
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                f"{OPERATION_CREATE_INVITE}:{household_id}:{idempotency_key}",
            )

            record = await conn.fetchrow(
                """
                SELECT fingerprint, resource_id, response_status, response_data, expires_at
                FROM idempotency_records
                WHERE user_id = $1
                  AND household_id = $2
                  AND operation = $3
                  AND idempotency_key = $4
                """,
                user_id,
                household_id,
                OPERATION_CREATE_INVITE,
                idempotency_key,
            )

            if record and record["expires_at"] > datetime.now(timezone.utc):
                if record["fingerprint"] != INVITE_PAYLOAD_FINGERPRINT:
                    return {
                        "status": False,
                        "status_code": 409,
                        "message": "Idempotency key was reused with a different request",
                        "data": {},
                    }

                data = json.loads(record["response_data"])
                if record["resource_id"] is not None:
                    data["invite_url"] = invite_url(
                        derive_invite_token(record["resource_id"])
                    )

                return {
                    "status": True,
                    "status_code": record["response_status"],
                    "message": CREATE_INVITE_MESSAGE,
                    "data": data,
                }

            _context, error = await households_service.lock_active_membership(
                conn, household_id, user_id, required_role="OWNER"
            )
            if error:
                return error

            invite_id = uuid4()
            token = derive_invite_token(invite_id)
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=settings.INVITE_EXPIRE_DAYS
            )

            invite = await conn.fetchrow(
                """
                INSERT INTO household_invites (
                    id,
                    household_id,
                    token_hash,
                    created_by,
                    expires_at
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, household_id, created_at, expires_at
                """,
                invite_id,
                household_id,
                hash_invite_token(token),
                user_id,
                expires_at,
            )

            await conn.execute(
                """
                INSERT INTO activity_events (
                    id,
                    household_id,
                    actor_user_id,
                    entity_type,
                    entity_id,
                    event_type,
                    metadata
                )
                VALUES ($1, $2, $3, 'household_invite', $4, 'INVITE_CREATED', $5::jsonb)
                """,
                uuid4(),
                household_id,
                user_id,
                invite_id,
                json.dumps({"invite_id": str(invite_id)}, separators=(",", ":")),
            )

            stored_data = invite_from_row(invite)
            response_data = {**stored_data, "invite_url": invite_url(token)}

            await conn.execute(
                """
                INSERT INTO idempotency_records (
                    id,
                    user_id,
                    household_id,
                    operation,
                    idempotency_key,
                    fingerprint,
                    payload,
                    resource_id,
                    response_status,
                    response_data,
                    expires_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, '{}'::jsonb, $7, 201, $8::jsonb, $9)
                ON CONFLICT ON CONSTRAINT uq_idempotency_records_scope
                DO UPDATE SET
                    fingerprint = EXCLUDED.fingerprint,
                    payload = EXCLUDED.payload,
                    resource_id = EXCLUDED.resource_id,
                    response_status = EXCLUDED.response_status,
                    response_data = EXCLUDED.response_data,
                    created_at = now(),
                    expires_at = EXCLUDED.expires_at
                """,
                uuid4(),
                user_id,
                household_id,
                OPERATION_CREATE_INVITE,
                idempotency_key,
                INVITE_PAYLOAD_FINGERPRINT,
                invite_id,
                json.dumps(stored_data, separators=(",", ":")),
                datetime.now(timezone.utc) + households_service.IDEMPOTENCY_TTL,
            )

            return {
                "status": True,
                "status_code": 201,
                "message": CREATE_INVITE_MESSAGE,
                "data": response_data,
            }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }


async def list_invites(conn: asyncpg.Connection, household_id) -> dict:
    try:
        rows = await conn.fetch(
            """
            SELECT id, household_id, created_at, expires_at
            FROM household_invites
            WHERE household_id = $1
              AND revoked_at IS NULL
              AND accepted_at IS NULL
              AND expires_at > now()
            ORDER BY created_at DESC, id
            """,
            household_id,
        )

        return {
            "status": True,
            "status_code": 200,
            "message": INVITES_MESSAGE,
            "data": {"invites": [invite_from_row(row) for row in rows]},
        }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }


async def revoke_invite(
    conn: asyncpg.Connection,
    user_id,
    household_id,
    invite_id,
) -> dict:
    try:
        async with conn.transaction():
            _context, error = await households_service.lock_active_membership(
                conn, household_id, user_id, required_role="OWNER"
            )
            if error:
                return error

            invite = await conn.fetchrow(
                """
                SELECT id, accepted_at, revoked_at
                FROM household_invites
                WHERE id = $1 AND household_id = $2
                FOR UPDATE
                """,
                invite_id,
                household_id,
            )

            if not invite:
                return {
                    "status": False,
                    "status_code": 404,
                    "message": "Invite not found",
                    "data": {},
                }

            if invite["accepted_at"] is not None:
                return {
                    "status": False,
                    "status_code": 409,
                    "message": "Invite already accepted",
                    "data": {},
                }

            if invite["revoked_at"] is not None:
                return {
                    "status": True,
                    "status_code": 200,
                    "message": REVOKE_INVITE_MESSAGE,
                    "data": {
                        "invite_id": invite_id,
                        "revoked_at": invite["revoked_at"].isoformat(),
                    },
                }

            revoked_at = await conn.fetchval(
                """
                UPDATE household_invites
                SET revoked_at = now(), revoked_by = $3
                WHERE id = $1 AND household_id = $2
                RETURNING revoked_at
                """,
                invite_id,
                household_id,
                user_id,
            )
            await conn.execute(
                """
                INSERT INTO activity_events (
                    id,
                    household_id,
                    actor_user_id,
                    entity_type,
                    entity_id,
                    event_type,
                    metadata
                )
                VALUES ($1, $2, $3, 'household_invite', $4, 'INVITE_REVOKED', $5::jsonb)
                """,
                uuid4(),
                household_id,
                user_id,
                invite_id,
                json.dumps({"invite_id": str(invite_id)}, separators=(",", ":")),
            )

            return {
                "status": True,
                "status_code": 200,
                "message": REVOKE_INVITE_MESSAGE,
                "data": {
                    "invite_id": invite_id,
                    "revoked_at": revoked_at.isoformat(),
                },
            }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }


async def accept_invite(
    conn: asyncpg.Connection,
    user_id,
    data,
    client_ip: str | None,
) -> dict:
    try:
        now = datetime.now(timezone.utc)
        token_hash = hash_invite_token(data.invite_token)
        user_window_start = now - timedelta(
            minutes=settings.INVITE_ACCEPT_USER_RATE_WINDOW_MINUTES
        )
        ip_window_start = now - timedelta(
            minutes=settings.INVITE_ACCEPT_IP_RATE_WINDOW_MINUTES
        )

        async with conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                f"invite-accept-user:{user_id}",
            )
            if client_ip:
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                    f"invite-accept-ip:{client_ip}",
                )

            user_attempts = await conn.fetchval(
                """
                SELECT count(*)
                FROM household_invite_accept_attempts
                WHERE user_id = $1 AND created_at > $2
                """,
                user_id,
                user_window_start,
            )
            if user_attempts >= settings.INVITE_ACCEPT_USER_RATE_LIMIT:
                return {
                    "status": False,
                    "status_code": 429,
                    "message": ACCEPT_RATE_LIMIT_MESSAGE,
                    "data": {},
                }

            if client_ip:
                ip_attempts = await conn.fetchval(
                    """
                    SELECT count(*)
                    FROM household_invite_accept_attempts
                    WHERE requested_ip = $1 AND created_at > $2
                    """,
                    client_ip,
                    ip_window_start,
                )
                if ip_attempts >= settings.INVITE_ACCEPT_IP_RATE_LIMIT:
                    return {
                        "status": False,
                        "status_code": 429,
                        "message": ACCEPT_RATE_LIMIT_MESSAGE,
                        "data": {},
                    }

            await conn.execute(
                """
                INSERT INTO household_invite_accept_attempts (id, user_id, requested_ip)
                VALUES ($1, $2, $3)
                """,
                uuid4(),
                user_id,
                client_ip,
            )

            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
                f"invite:{token_hash}",
            )

            invite = await conn.fetchrow(
                """
                SELECT id,
                       household_id,
                       expires_at,
                       revoked_at,
                       accepted_at,
                       accepted_by,
                       accepted_membership_id
                FROM household_invites
                WHERE token_hash = $1
                FOR UPDATE
                """,
                token_hash,
            )

            if not invite:
                return {
                    "status": False,
                    "status_code": 404,
                    "message": INVITE_UNAVAILABLE_MESSAGE,
                    "data": {},
                }

            if invite["revoked_at"] is not None or invite["expires_at"] <= now:
                return unavailable_response()

            if invite["accepted_at"] is not None:
                if invite["accepted_by"] != user_id:
                    return unavailable_response()

                membership = await conn.fetchrow(
                    """
                    SELECT id, user_id, role, status, joined_at
                    FROM household_members
                    WHERE id = $1 AND household_id = $2 AND status = 'ACTIVE'
                    """,
                    invite["accepted_membership_id"],
                    invite["household_id"],
                )
                household = await conn.fetchrow(
                    """
                    SELECT id, name, timezone, default_due_time, created_at, deactivated_at
                    FROM households
                    WHERE id = $1
                    """,
                    invite["household_id"],
                )
                if (
                    not membership
                    or not household
                    or household["deactivated_at"] is not None
                ):
                    return unavailable_response()

                await conn.execute(
                    "UPDATE users SET last_household_id = $2 WHERE id = $1",
                    user_id,
                    household["id"],
                )

                return {
                    "status": True,
                    "status_code": 200,
                    "message": ACCEPT_INVITE_MESSAGE,
                    "data": {
                        "household": household_summary_from_row(
                            household, membership["role"], membership["joined_at"]
                        ),
                        "membership": membership_summary_from_row(membership),
                        "membership_created": False,
                        "selected_household_id": household["id"],
                    },
                }

            household = await conn.fetchrow(
                """
                SELECT id, name, timezone, default_due_time, created_at, deactivated_at
                FROM households
                WHERE id = $1
                """,
                invite["household_id"],
            )
            if not household or household["deactivated_at"] is not None:
                return unavailable_response()

            membership = await conn.fetchrow(
                """
                SELECT id, user_id, role, status, joined_at
                FROM household_members
                WHERE household_id = $1 AND user_id = $2 AND status = 'ACTIVE'
                FOR UPDATE
                """,
                household["id"],
                user_id,
            )

            membership_created = False
            if membership is None:
                membership = await conn.fetchrow(
                    """
                    INSERT INTO household_members (id, household_id, user_id, role, status)
                    VALUES ($1, $2, $3, 'MEMBER', 'ACTIVE')
                    RETURNING id, user_id, role, status, joined_at
                    """,
                    uuid4(),
                    household["id"],
                    user_id,
                )
                membership_created = True

            await conn.execute(
                """
                UPDATE household_invites
                SET accepted_at = now(),
                    accepted_by = $2,
                    accepted_membership_id = $3
                WHERE id = $1
                """,
                invite["id"],
                user_id,
                membership["id"],
            )
            await conn.execute(
                "UPDATE users SET last_household_id = $2 WHERE id = $1",
                user_id,
                household["id"],
            )
            await conn.execute(
                """
                INSERT INTO activity_events (
                    id,
                    household_id,
                    actor_user_id,
                    entity_type,
                    entity_id,
                    event_type,
                    metadata
                )
                VALUES ($1, $2, $3, 'household_invite', $4, 'INVITE_ACCEPTED', $5::jsonb)
                """,
                uuid4(),
                household["id"],
                user_id,
                invite["id"],
                json.dumps(
                    {
                        "invite_id": str(invite["id"]),
                        "membership_id": str(membership["id"]),
                    },
                    separators=(",", ":"),
                ),
            )
            if membership_created:
                await conn.execute(
                    """
                    INSERT INTO activity_events (
                        id,
                        household_id,
                        actor_user_id,
                        entity_type,
                        entity_id,
                        event_type,
                        metadata
                    )
                    VALUES ($1, $2, $3, 'household_member', $4, 'MEMBER_JOINED', $5::jsonb)
                    """,
                    uuid4(),
                    household["id"],
                    user_id,
                    membership["id"],
                    json.dumps(
                        {
                            "membership_id": str(membership["id"]),
                            "invite_id": str(invite["id"]),
                        },
                        separators=(",", ":"),
                    ),
                )

            return {
                "status": True,
                "status_code": 201 if membership_created else 200,
                "message": ACCEPT_INVITE_MESSAGE,
                "data": {
                    "household": household_summary_from_row(
                        household, membership["role"], membership["joined_at"]
                    ),
                    "membership": membership_summary_from_row(membership),
                    "membership_created": membership_created,
                    "selected_household_id": household["id"],
                },
            }
    except Exception as exc:
        logger.exception(exc)
        return {
            "status": False,
            "status_code": 500,
            "message": "Internal server error",
            "data": {},
        }
