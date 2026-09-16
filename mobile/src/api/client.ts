import { API_URL } from './config';
import type { operations } from './types.generated';

type HealthResponse = operations['health_check_health_get']['responses'][200]['content']['application/json'];

async function request(path: string) {
  const response = await fetch(`${API_URL}${path}`);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<unknown>;
}

export const api = {
  async health(): Promise<HealthResponse> {
    return request('/health') as Promise<HealthResponse>;
  },
};
