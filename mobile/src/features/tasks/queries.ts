import { useQuery } from '@tanstack/react-query';

import { useSessionStore } from '@/stores/session';

import { tasksApi } from './api';

export function tasksQueryKey(householdId: string) {
  return ['households', householdId, 'tasks', 'pending'] as const;
}

export function usePendingTasks(householdId: string) {
  const accessToken = useSessionStore((state) => state.accessToken);

  return useQuery({
    queryKey: tasksQueryKey(householdId),
    queryFn: () => {
      if (!accessToken) {
        throw new Error('Missing access token');
      }

      return tasksApi.listTasks(accessToken, householdId);
    },

    enabled: accessToken !== null && householdId.length > 0,
  });
}
