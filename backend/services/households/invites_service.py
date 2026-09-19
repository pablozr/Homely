import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import asyncpg

from core.config.config import settings
from core.logger.logger import logger
from core.security.security import derive_invite_token, hash_invite_token
from repositories.households import households_repository, invites_repository
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
            await invites_repository.acquire_advisory_lock(
                conn,
                f"{OPERATION_CREATE_INVITE}:{household_id}:{idempotency_key}",
            )

            record = await invites_repository.find_create_invite_idempotency_record(
                conn,
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

            invite = await invites_repository.insert_invite(
                conn,
                invite_id,
                household_id,
                hash_invite_token(token),
                user_id,
                expires_at,
            )

            await invites_repository.insert_invite_created_event(
                conn,
                uuid4(),
                household_id,
                user_id,
                invite_id,
                json.dumps({"invite_id": str(invite_id)}, separators=(",", ":")),
            )

            stored_data = invite_from_row(invite)
            response_data = {**stored_data, "invite_url": invite_url(token)}

            await invites_repository.upsert_invite_idempotency_record(
                conn,
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
        rows = await invites_repository.list_active_invites(conn, household_id)

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

            invite = await invites_repository.lock_invite(
                conn,
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

            revoked_at = await invites_repository.revoke_invite(
                conn,
                invite_id,
                household_id,
                user_id,
            )
            await invites_repository.insert_invite_revoked_event(
                conn,
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
            await invites_repository.acquire_advisory_lock(
                conn,
                f"invite-accept-user:{user_id}",
            )
            if client_ip:
                await invites_repository.acquire_advisory_lock(
                    conn,
                    f"invite-accept-ip:{client_ip}",
                )

            user_attempts = await invites_repository.count_user_accept_attempts(
                conn,
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
                ip_attempts = await invites_repository.count_ip_accept_attempts(
                    conn,
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

            await invites_repository.insert_accept_attempt(
                conn,
                uuid4(),
                user_id,
                client_ip,
            )

            await invites_repository.acquire_advisory_lock(
                conn,
                f"invite:{token_hash}",
            )

            invite = await invites_repository.lock_invite_by_token(conn, token_hash)

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

                membership = await invites_repository.find_active_membership_by_id(
                    conn,
                    invite["accepted_membership_id"],
                    invite["household_id"],
                )
                household = await invites_repository.find_household(
                    conn,
                    invite["household_id"],
                )
                if (
                    not membership
                    or not household
                    or household["deactivated_at"] is not None
                ):
                    return unavailable_response()

                await households_repository.update_user_last_household(
                    conn,
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

            household = await invites_repository.find_household(
                conn,
                invite["household_id"],
            )
            if not household or household["deactivated_at"] is not None:
                return unavailable_response()

            membership = await invites_repository.find_active_membership_for_update(
                conn,
                household["id"],
                user_id,
            )

            membership_created = False
            if membership is None:
                membership = await invites_repository.insert_active_membership(
                    conn,
                    uuid4(),
                    household["id"],
                    user_id,
                )
                membership_created = True

            await invites_repository.mark_invite_accepted(
                conn,
                invite["id"],
                user_id,
                membership["id"],
            )
            await households_repository.update_user_last_household(
                conn,
                user_id,
                household["id"],
            )
            await invites_repository.insert_invite_accepted_event(
                conn,
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
                await invites_repository.insert_member_joined_event(
                    conn,
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
