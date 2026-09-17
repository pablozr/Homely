import { useActiveHouseholdStore } from '@/stores/active-household';
import { useSessionStore } from '@/stores/session';
import { householdsApi } from './api';

export async function selectHousehold(householdId: string): Promise<string> {
  const accessToken = useSessionStore.getState().accessToken;

  if (!accessToken) {
    throw new Error('Missing access token');
  }

  const { data } = await householdsApi.selectHousehold(accessToken, householdId);

  useActiveHouseholdStore.getState().setActiveHouseholdId(data.selected_household_id);

  return data.selected_household_id;
}
