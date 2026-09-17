import { QueryClient } from '@tanstack/react-query';

export const householdsQueryKey = ['households'] as const;

export const queryClient = new QueryClient();

export function clearHouseholdCache(client: QueryClient = queryClient): void {
  client.removeQueries({ queryKey: householdsQueryKey });
}
