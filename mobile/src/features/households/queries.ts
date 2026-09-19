import { useQuery } from '@tanstack/react-query';

import { householdsQueryKey } from '@/lib/query-client';
import { useSessionStore } from '@/stores/session';
import { householdsApi } from './api';
import type { HouseholdSummary, HouseholdsData, HouseholdsResponse } from './types';

export { householdsQueryKey };

export function householdMembersQueryKey(householdId: string) {
  return ['households', householdId, 'members'] as const;
}

export function householdInvitesQueryKey(householdId: string) {
  return ['households', householdId, 'invites'] as const;
}

export function useHouseholds() {
  const accessToken = useSessionStore((state) => state.accessToken);

  return useQuery({
    queryKey: householdsQueryKey,
    queryFn: () => {
      if (!accessToken) {
        throw new Error('Missing access token');
      }

      return householdsApi.listHouseholds(accessToken);
    },

    enabled: accessToken !== null,
  });
}

export function useHouseholdMembers(householdId: string) {
  const accessToken = useSessionStore((state) => state.accessToken);

  return useQuery({
    queryKey: householdMembersQueryKey(householdId),
    queryFn: () => {
      if (!accessToken) {
        throw new Error('Missing access token');
      }

      return householdsApi.listMembers(accessToken, householdId);
    },

    enabled: accessToken !== null && householdId.length > 0,
  });
}

export function useHouseholdInvites(householdId: string) {
  const accessToken = useSessionStore((state) => state.accessToken);

  return useQuery({
    queryKey: householdInvitesQueryKey(householdId),
    queryFn: () => {
      if (!accessToken) {
        throw new Error('Missing access token');
      }

      return householdsApi.listInvites(accessToken, householdId);
    },

    enabled: accessToken !== null && householdId.length > 0,
  });
}

export function resolveActiveHouseholdId(data: HouseholdsData): string | null {
  if (data.households.length === 0) {
    return null;
  }

  if (data.households.length === 1) {
    return data.households[0].id;
  }

  const selected = data.selected_household_id;

  if (selected !== null && data.households.some((household) => household.id === selected)) {
    return selected;
  }

  return data.households[0].id;
}

export function mergeHousehold(
  data: HouseholdsData | undefined,
  household: HouseholdSummary,
  selectedHouseholdId: string,
): HouseholdsData {
  const households = data ? [...data.households] : [];
  const index = households.findIndex((current) => current.id === household.id);

  if (index === -1) {
    households.push(household);
  } else {
    households[index] = household;
  }

  return { households, selected_household_id: selectedHouseholdId };
}

export function upsertHouseholdsResponse(
  current: HouseholdsResponse | undefined,
  household: HouseholdSummary,
  selectedHouseholdId: string,
): HouseholdsResponse {
  return {
    message: current?.message ?? '',
    data: mergeHousehold(current?.data, household, selectedHouseholdId),
  };
}
