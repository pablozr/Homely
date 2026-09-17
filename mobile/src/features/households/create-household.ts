import { useActiveHouseholdStore } from '@/stores/active-household';
import { useSessionStore } from '@/stores/session';
import { householdsApi } from './api';
import type { HouseholdCreatedData } from './types';

export type CreateHouseholdInput = {
  name: string;
  timezone: string;
  idempotencyKey: string;
};

export async function createHousehold(input: CreateHouseholdInput): Promise<HouseholdCreatedData> {
  const accessToken = useSessionStore.getState().accessToken;

  if (!accessToken) {
    throw new Error('Missing access token');
  }

  const { data } = await householdsApi.createHousehold(
    accessToken,
    { name: input.name, timezone: input.timezone },
    input.idempotencyKey,
  );

  useActiveHouseholdStore.getState().setActiveHouseholdId(data.selected_household_id);

  return data;
}
