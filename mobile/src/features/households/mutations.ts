import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { HouseholdsResponse } from './types';
import { createHousehold, type CreateHouseholdInput } from './create-household';
import { householdsQueryKey, upsertHouseholdsResponse } from './queries';
import { selectHousehold } from './select-household';

export function useCreateHousehold() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateHouseholdInput) => createHousehold(input),

    onSuccess: ({ household, selected_household_id }) => {
      queryClient.setQueryData<HouseholdsResponse>(householdsQueryKey, (current) =>
        upsertHouseholdsResponse(current, household, selected_household_id),
      );

      queryClient.invalidateQueries({ queryKey: householdsQueryKey });
    },
  });
}

export function useSelectHousehold() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (householdId: string) => selectHousehold(householdId),

    onSuccess: (selectedHouseholdId) => {
      queryClient.setQueryData<HouseholdsResponse>(householdsQueryKey, (current) =>
        current
          ? {
              ...current,
              data: { ...current.data, selected_household_id: selectedHouseholdId },
            }
          : current,
      );

      queryClient.invalidateQueries({ queryKey: householdsQueryKey });
    },
  });
}
