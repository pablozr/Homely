import { request } from '@/api/client';

import type {
  HouseholdCreateRequest,
  HouseholdCreatedResponse,
  HouseholdSelectionResponse,
  HouseholdsResponse,
} from './types';

export const householdsApi = {
  createHousehold(
    token: string,
    body: HouseholdCreateRequest,
    idempotencyKey: string,
  ): Promise<HouseholdCreatedResponse> {
    return request<HouseholdCreatedResponse>('/households', {
      method: 'POST',
      body,
      token,
      headers: { 'Idempotency-Key': idempotencyKey },
    });
  },

  listHouseholds(token: string): Promise<HouseholdsResponse> {
    return request<HouseholdsResponse>('/households', { token });
  },

  selectHousehold(token: string, householdId: string): Promise<HouseholdSelectionResponse> {
    return request<HouseholdSelectionResponse>(`/households/${householdId}/selection`, {
      method: 'PATCH',
      token,
    });
  },
};
