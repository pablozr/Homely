import { useQuery } from '@tanstack/react-query';

import { api } from '@/api/client';

export function useApiHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.health,
  });
}
