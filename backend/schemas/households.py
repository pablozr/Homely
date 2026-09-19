from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class HouseholdCreateRequestModel(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    timezone: str = Field(min_length=1, max_length=64)

    @field_validator("name", "timezone", mode="before")
    @classmethod
    def strip_text(cls, value):
        if not isinstance(value, str):
            return value

        return value.strip()

    @field_validator("timezone")
    @classmethod
    def require_iana_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Invalid IANA timezone") from exc

        return value


class HouseholdSummaryModel(BaseModel):
    id: UUID
    name: str
    timezone: str
    default_due_time: str
    role: str
    joined_at: str
    created_at: str


class HouseholdCreatedDataModel(BaseModel):
    household: HouseholdSummaryModel
    selected_household_id: UUID


class HouseholdCreatedResponseModel(BaseModel):
    message: str
    data: HouseholdCreatedDataModel


class HouseholdsDataModel(BaseModel):
    households: list[HouseholdSummaryModel]
    selected_household_id: UUID | None


class HouseholdsResponseModel(BaseModel):
    message: str
    data: HouseholdsDataModel


class HouseholdSelectionDataModel(BaseModel):
    selected_household_id: UUID


class HouseholdSelectionResponseModel(BaseModel):
    message: str
    data: HouseholdSelectionDataModel


class InviteModel(BaseModel):
    id: UUID
    household_id: UUID
    created_at: str
    expires_at: str


class InviteCreatedDataModel(InviteModel):
    invite_url: str


class InviteCreatedResponseModel(BaseModel):
    message: str
    data: InviteCreatedDataModel


class InvitesDataModel(BaseModel):
    invites: list[InviteModel]


class InvitesResponseModel(BaseModel):
    message: str
    data: InvitesDataModel


class InviteRevokeDataModel(BaseModel):
    invite_id: UUID
    revoked_at: str


class InviteRevokeResponseModel(BaseModel):
    message: str
    data: InviteRevokeDataModel


class InviteAcceptRequestModel(BaseModel):
    invite_token: str = Field(min_length=1, max_length=255)

    @field_validator("invite_token", mode="before")
    @classmethod
    def strip_token(cls, value):
        if not isinstance(value, str):
            return value

        return value.strip()


class MembershipModel(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    status: str
    joined_at: str


class MemberModel(MembershipModel):
    fullname: str


class MembershipsDataModel(BaseModel):
    memberships: list[MemberModel]


class MembershipsResponseModel(BaseModel):
    message: str
    data: MembershipsDataModel


class InviteAcceptDataModel(BaseModel):
    household: HouseholdSummaryModel
    membership: MembershipModel
    membership_created: bool
    selected_household_id: UUID


class InviteAcceptResponseModel(BaseModel):
    message: str
    data: InviteAcceptDataModel


class MembershipRemovedDataModel(BaseModel):
    membership_id: UUID
    removed_at: str


class MembershipRemovedResponseModel(BaseModel):
    message: str
    data: MembershipRemovedDataModel


class HouseholdLeaveDataModel(BaseModel):
    household_id: UUID
    left_at: str


class HouseholdLeaveResponseModel(BaseModel):
    message: str
    data: HouseholdLeaveDataModel


class OwnershipTransferRequestModel(BaseModel):
    target_membership_id: UUID


class OwnershipTransferDataModel(BaseModel):
    household_id: UUID
    previous_owner_membership_id: UUID
    previous_owner_role: str
    new_owner_membership_id: UUID
    new_owner_role: str


class OwnershipTransferResponseModel(BaseModel):
    message: str
    data: OwnershipTransferDataModel


def household_summary_from_row(row, role: str, joined_at) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "timezone": row["timezone"],
        "default_due_time": row["default_due_time"].isoformat(),
        "role": role,
        "joined_at": joined_at.isoformat(),
        "created_at": row["created_at"].isoformat(),
    }


def invite_from_row(row) -> dict:
    return {
        "id": str(row["id"]),
        "household_id": str(row["household_id"]),
        "created_at": row["created_at"].isoformat(),
        "expires_at": row["expires_at"].isoformat(),
    }


def membership_summary_from_row(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "role": row["role"],
        "status": row["status"],
        "joined_at": row["joined_at"].isoformat(),
    }


def member_from_row(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "fullname": row["fullname"],
        "role": row["role"],
        "status": row["status"],
        "joined_at": row["joined_at"].isoformat(),
    }
