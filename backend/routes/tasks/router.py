from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends

from core.postgresql.postgresql import postgresql
from core.responses import default_response
from dependencies import households
from schemas.tasks import (
    TaskCreateRequestModel,
    TaskResponseModel,
    TaskUpdateRequestModel,
    TasksResponseModel,
)
from services.tasks import tasks_service


router = APIRouter()


@router.post(
    "/{household_id}/tasks",
    status_code=201,
    response_model=TaskResponseModel,
)
async def create_task(
    data: TaskCreateRequestModel,
    idempotency_key: str = Depends(households.require_idempotency_key),
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        tasks_service.create_task,
        conn,
        membership["user_id"],
        membership["household_id"],
        data,
        idempotency_key,
    )


@router.get("/{household_id}/tasks", response_model=TasksResponseModel)
async def list_tasks(
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        tasks_service.list_tasks,
        conn,
        membership["household_id"],
    )


@router.patch(
    "/{household_id}/tasks/{occurrence_id}",
    response_model=TaskResponseModel,
)
async def update_task(
    occurrence_id: UUID,
    data: TaskUpdateRequestModel,
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        tasks_service.update_task,
        conn,
        membership["user_id"],
        membership["household_id"],
        occurrence_id,
        data,
    )


@router.post(
    "/{household_id}/tasks/{occurrence_id}/cancel",
    response_model=TaskResponseModel,
)
async def cancel_task(
    occurrence_id: UUID,
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        tasks_service.cancel_task,
        conn,
        membership["user_id"],
        membership["household_id"],
        occurrence_id,
    )


@router.post(
    "/{household_id}/tasks/{occurrence_id}/complete",
    response_model=TaskResponseModel,
)
async def complete_task(
    occurrence_id: UUID,
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        tasks_service.complete_task,
        conn,
        membership["user_id"],
        membership["household_id"],
        occurrence_id,
    )


@router.post(
    "/{household_id}/tasks/{occurrence_id}/undo-completion",
    response_model=TaskResponseModel,
)
async def undo_task_completion(
    occurrence_id: UUID,
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        tasks_service.undo_task_completion,
        conn,
        membership["user_id"],
        membership["household_id"],
        occurrence_id,
    )


@router.post(
    "/{household_id}/tasks/{occurrence_id}/correct-completion",
    response_model=TaskResponseModel,
)
async def correct_task_completion(
    occurrence_id: UUID,
    membership: dict = Depends(households.require_active_membership),
    conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    return await default_response(
        tasks_service.correct_task_completion,
        conn,
        membership["user_id"],
        membership["household_id"],
        occurrence_id,
    )
