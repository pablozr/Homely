from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from core.postgresql.postgresql import postgresql
from core.responses import default_response
from dependencies import auth, households
from schemas.households import (
    HouseholdCreateRequestModel,
    HouseholdCreatedResponseModel,
    HouseholdLeaveResponseModel,
    HouseholdSelectionResponseModel,
    HouseholdsResponseModel,
    InviteAcceptRequestModel,
    InviteAcceptResponseModel,
    InviteCreatedResponseModel,
    InviteRevokeResponseModel,
    InvitesResponseModel,
    MembershipRemovedResponseModel,
    MembershipsResponseModel,
    OwnershipTransferRequestModel,
    OwnershipTransferResponseModel,
)
from services.households import households_service, invites_service, memberships_service


router = APIRouter()


def sanitized_validation_detail(errors) -> list[dict]:
    return [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in errors
    ]


class InviteAcceptRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def redact_invite_token(request):
            try:
                return await original(request)
            except RequestValidationError as exc:
                return JSONResponse(
                    status_code=422,
                    content={"detail": sanitized_validation_detail(exc.errors())},
                )

        return redact_invite_token


@router.post("", status_code=201, response_model=HouseholdCreatedResponseModel)
async def create_household(
    data: HouseholdCreateRequestModel,
    idempotency_key: str = Depends(households.require_idempotency_key),
    user: dict = Depends(auth.validate_token_wrapper),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        households_service.create_household,
        conn,
        user["id"],
        data,
        idempotency_key,
    )


@router.get("", response_model=HouseholdsResponseModel)
async def list_households(
    user: dict = Depends(auth.validate_token_wrapper),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        households_service.list_households,
        conn,
        user["id"],
    )


@router.patch("/{household_id}/selection", response_model=HouseholdSelectionResponseModel)
async def select_household(
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        households_service.select_household,
        conn,
        membership["user_id"],
        membership["household_id"],
    )


async def accept_invite(
    data: InviteAcceptRequestModel,
    request: Request,
    user: dict = Depends(auth.validate_token_wrapper),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        invites_service.accept_invite,
        conn,
        user["id"],
        data,
        client_ip=request.client.host if request.client else None,
    )


router.add_api_route(
    "/invites/accept",
    accept_invite,
    methods=["POST"],
    response_model=InviteAcceptResponseModel,
    route_class_override=InviteAcceptRoute,
)


@router.post(
    "/{household_id}/invites",
    status_code=201,
    response_model=InviteCreatedResponseModel,
)
async def create_invite(
    membership: dict = Depends(households.require_owner_membership),
    idempotency_key: str = Depends(households.require_idempotency_key),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        invites_service.create_invite,
        conn,
        membership["user_id"],
        membership["household_id"],
        idempotency_key,
    )


@router.get("/{household_id}/invites", response_model=InvitesResponseModel)
async def list_invites(
    membership: dict = Depends(households.require_owner_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        invites_service.list_invites,
        conn,
        membership["household_id"],
    )


@router.post(
    "/{household_id}/invites/{invite_id}/revoke",
    response_model=InviteRevokeResponseModel,
)
async def revoke_invite(
    invite_id: UUID,
    membership: dict = Depends(households.require_owner_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        invites_service.revoke_invite,
        conn,
        membership["user_id"],
        membership["household_id"],
        invite_id,
    )


@router.get("/{household_id}/members", response_model=MembershipsResponseModel)
async def list_members(
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        memberships_service.list_members,
        conn,
        membership["household_id"],
    )


@router.post(
    "/{household_id}/members/{membership_id}/remove",
    response_model=MembershipRemovedResponseModel,
)
async def remove_member(
    membership_id: UUID,
    membership: dict = Depends(households.require_owner_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        memberships_service.remove_member,
        conn,
        membership["user_id"],
        membership["household_id"],
        membership_id,
    )


@router.post("/{household_id}/leave", response_model=HouseholdLeaveResponseModel)
async def leave_household(
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        memberships_service.leave_household,
        conn,
        membership["user_id"],
        membership["household_id"],
    )


@router.post(
    "/{household_id}/ownership-transfer",
    response_model=OwnershipTransferResponseModel,
)
async def transfer_ownership(
    data: OwnershipTransferRequestModel,
    membership: dict = Depends(households.require_owner_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        memberships_service.transfer_ownership,
        conn,
        membership["user_id"],
        membership["household_id"],
        data.target_membership_id,
    )
