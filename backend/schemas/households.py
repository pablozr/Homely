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
