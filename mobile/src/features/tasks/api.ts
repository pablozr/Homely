import { request } from '@/api/client';

import type { TaskCreateRequest, TaskResponse, TasksResponse, TaskUpdateRequest } from './types';

export const tasksApi = {
  createTask(
    token: string,
    householdId: string,
    body: TaskCreateRequest,
    idempotencyKey: string,
  ): Promise<TaskResponse> {
    return request<TaskResponse>(`/households/${householdId}/tasks`, {
      method: 'POST',
      body,
      token,
      headers: { 'Idempotency-Key': idempotencyKey },
    });
  },

  listTasks(token: string, householdId: string): Promise<TasksResponse> {
    return request<TasksResponse>(`/households/${householdId}/tasks`, { token });
  },

  updateTask(
    token: string,
    householdId: string,
    occurrenceId: string,
    body: TaskUpdateRequest,
  ): Promise<TaskResponse> {
    return request<TaskResponse>(`/households/${householdId}/tasks/${occurrenceId}`, {
      method: 'PATCH',
      body,
      token,
    });
  },

  cancelTask(token: string, householdId: string, occurrenceId: string): Promise<TaskResponse> {
    return request<TaskResponse>(`/households/${householdId}/tasks/${occurrenceId}/cancel`, {
      method: 'POST',
      token,
    });
  },

  completeTask(token: string, householdId: string, occurrenceId: string): Promise<TaskResponse> {
    return request<TaskResponse>(`/households/${householdId}/tasks/${occurrenceId}/complete`, {
      method: 'POST',
      token,
    });
  },

  undoTaskCompletion(
    token: string,
    householdId: string,
    occurrenceId: string,
  ): Promise<TaskResponse> {
    return request<TaskResponse>(
      `/households/${householdId}/tasks/${occurrenceId}/undo-completion`,
      {
        method: 'POST',
        token,
      },
    );
  },

  correctTaskCompletion(
    token: string,
    householdId: string,
    occurrenceId: string,
  ): Promise<TaskResponse> {
    return request<TaskResponse>(
      `/households/${householdId}/tasks/${occurrenceId}/correct-completion`,
      {
        method: 'POST',
        token,
      },
    );
  },
};
