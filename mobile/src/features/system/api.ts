import { request } from '@/api/client';
import type { operations } from '@/api/types.generated';

type HealthResponse =
  operations['health_check_health_get']['responses'][200]['content']['application/json'];

export const systemApi = {
  health(): Promise<HealthResponse> {
    return request<HealthResponse>('/health');
  },
};
