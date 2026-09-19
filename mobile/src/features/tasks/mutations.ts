import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useSessionStore } from '@/stores/session';

import { tasksApi } from './api';
import { tasksQueryKey } from './queries';
import type { TaskCreateRequest, TaskUpdateRequest } from './types';

function requireAccessToken(): string {
  const accessToken = useSessionStore.getState().accessToken;

  if (!accessToken) {
    throw new Error('Missing access token');
  }

  return accessToken;
}

export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { householdId: string; body: TaskCreateRequest; idempotencyKey: string }) =>
      tasksApi.createTask(
        requireAccessToken(),
        input.householdId,
        input.body,
        input.idempotencyKey,
      ),

    onSuccess: (_data, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: tasksQueryKey(householdId) });
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { householdId: string; occurrenceId: string; body: TaskUpdateRequest }) =>
      tasksApi.updateTask(requireAccessToken(), input.householdId, input.occurrenceId, input.body),

    onSuccess: (_data, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: tasksQueryKey(householdId) });
    },
  });
}

export function useCancelTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { householdId: string; occurrenceId: string }) =>
      tasksApi.cancelTask(requireAccessToken(), input.householdId, input.occurrenceId),

    onSuccess: (_data, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: tasksQueryKey(householdId) });
    },
  });
}

export function useCompleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { householdId: string; occurrenceId: string }) =>
      tasksApi.completeTask(requireAccessToken(), input.householdId, input.occurrenceId),

    onSuccess: (_data, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: tasksQueryKey(householdId) });
    },

    onError: (_error, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: tasksQueryKey(householdId) });
    },
  });
}

export function useUndoTaskCompletion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { householdId: string; occurrenceId: string }) =>
      tasksApi.undoTaskCompletion(requireAccessToken(), input.householdId, input.occurrenceId),

    onSuccess: (_data, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: tasksQueryKey(householdId) });
    },

    onError: (_error, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: tasksQueryKey(householdId) });
    },
  });
}

export function useCorrectTaskCompletion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { householdId: string; occurrenceId: string }) =>
      tasksApi.correctTaskCompletion(requireAccessToken(), input.householdId, input.occurrenceId),

    onSuccess: (_data, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: tasksQueryKey(householdId) });
    },

    onError: (_error, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: tasksQueryKey(householdId) });
    },
  });
}
