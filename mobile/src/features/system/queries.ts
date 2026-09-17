import { useQuery } from '@tanstack/react-query';

import { systemApi } from './api';

export function useApiHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: systemApi.health,
  });
}
