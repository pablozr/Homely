import re
from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator


DUE_LOCAL_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
DUE_LOCAL_FORMAT = "%Y-%m-%dT%H:%M"


def validate_due_local_value(value: str | None) -> str | None:
    if value is None:
        return value

    if not isinstance(value, str) or not DUE_LOCAL_PATTERN.fullmatch(value):
        raise ValueError("due_local must use the local format YYYY-MM-DDTHH:mm without offset")

    try:
        datetime.strptime(value, DUE_LOCAL_FORMAT)
    except ValueError as exc:
        raise ValueError("due_local must be a valid local date and time") from exc

    return value


class TaskCreateRequestModel(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    assignee_membership_id: UUID | None = None
    due_local: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value):
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("due_local")
    @classmethod
    def require_civil_due_local(cls, value: str | None) -> str | None:
        return validate_due_local_value(value)


class TaskUpdateRequestModel(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    assignee_membership_id: UUID | None = None
    due_local: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value):
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator("due_local")
    @classmethod
    def require_civil_due_local(cls, value: str | None) -> str | None:
        return validate_due_local_value(value)

    @model_validator(mode="after")
    def require_single_change_and_valid_title(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if "title" in self.model_fields_set:
            if self.title is None:
                raise ValueError("title cannot be null")
            if not self.title:
                raise ValueError("title cannot be blank")

        return self


class TaskAssigneeModel(BaseModel):
    membership_id: UUID
    user_id: UUID
    fullname: str


class TaskModel(BaseModel):
    id: UUID
    occurrence_id: UUID
    task_id: UUID
    household_id: UUID
    title: str
    status: str
    assignee: TaskAssigneeModel | None
    due_at: str | None
    due_timezone: str | None
    due_local: str | None
    is_overdue: bool
    created_by: UUID
    created_at: str
    updated_at: str
    cancelled_at: str | None
    cancelled_by: UUID | None
    completed_by: UUID | None
    completed_at: str | None


class TaskEnvelopeModel(BaseModel):
    task: TaskModel


class TaskResponseModel(BaseModel):
    message: str
    data: TaskEnvelopeModel


class TasksDataModel(BaseModel):
    tasks: list[TaskModel]


class TasksResponseModel(BaseModel):
    message: str
    data: TasksDataModel


def due_local_from_utc(due_at: datetime, timezone_name: str) -> str:
    return due_at.astimezone(ZoneInfo(timezone_name)).strftime(DUE_LOCAL_FORMAT)


def task_is_overdue(status: str, due_at: datetime | None, now: datetime) -> bool:
    return status == "PENDING" and due_at is not None and due_at < now


def task_from_row(row, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    due_at = row["due_at"]
    due_timezone = row["due_timezone"]

    assignee = None
    if row["assignee_membership_id"] is not None:
        assignee = {
            "membership_id": str(row["assignee_membership_id"]),
            "user_id": str(row["assignee_user_id"]),
            "fullname": row["assignee_fullname"],
        }

    return {
        "id": str(row["occurrence_id"]),
        "occurrence_id": str(row["occurrence_id"]),
        "task_id": str(row["task_id"]),
        "household_id": str(row["household_id"]),
        "title": row["title"],
        "status": row["status"],
        "assignee": assignee,
        "due_at": due_at.isoformat() if due_at is not None else None,
        "due_timezone": due_timezone,
        "due_local": (
            due_local_from_utc(due_at, due_timezone)
            if due_at is not None
            else None
        ),
        "is_overdue": task_is_overdue(row["status"], due_at, now),
        "created_by": str(row["created_by"]),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
        "cancelled_at": (
            row["cancelled_at"].isoformat()
            if row["cancelled_at"] is not None
            else None
        ),
        "cancelled_by": (
            str(row["cancelled_by"]) if row["cancelled_by"] is not None else None
        ),
        "completed_by": (
            str(row["completed_by"]) if row["completed_by"] is not None else None
        ),
        "completed_at": (
            row["completed_at"].isoformat()
            if row["completed_at"] is not None
            else None
        ),
    }


def refresh_task_derived(task: dict) -> dict:
    due_at = datetime.fromisoformat(task["due_at"]) if task["due_at"] else None
    due_timezone = task["due_timezone"]

    task["due_local"] = (
        due_local_from_utc(due_at, due_timezone) if due_at is not None else None
    )
    task["is_overdue"] = task_is_overdue(
        task["status"], due_at, datetime.now(timezone.utc)
    )

    return task
