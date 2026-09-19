import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useActiveHouseholdStore } from '@/stores/active-household';
import { useSessionStore } from '@/stores/session';
import { householdsApi } from './api';
import { runPendingInviteAcceptance, submitInviteToken } from './invite-coordinator';
import { createHousehold, type CreateHouseholdInput } from './create-household';
import {
  householdInvitesQueryKey,
  householdMembersQueryKey,
  householdsQueryKey,
  upsertHouseholdsResponse,
} from './queries';
import { selectHousehold } from './select-household';
import type { HouseholdsResponse } from './types';

function requireAccessToken(): string {
  const accessToken = useSessionStore.getState().accessToken;

  if (!accessToken) {
    throw new Error('Missing access token');
  }

  return accessToken;
}

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

export function useAcceptPendingInvite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => runPendingInviteAcceptance(),

    onSuccess: (result) => {
      if (result.status === 'accepted') {
        queryClient.invalidateQueries({ queryKey: householdsQueryKey });
      }
    },
  });
}

export function useSubmitInviteToken() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (token: string) => submitInviteToken(token),

    onSuccess: (result) => {
      if (result.status === 'accepted') {
        queryClient.invalidateQueries({ queryKey: householdsQueryKey });
      }
    },
  });
}

export function useCreateInvite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { householdId: string; idempotencyKey: string }) =>
      householdsApi.createInvite(requireAccessToken(), input.householdId, input.idempotencyKey),

    onSuccess: (_data, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: householdInvitesQueryKey(householdId) });
    },
  });
}

export function useRevokeInvite() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { householdId: string; inviteId: string }) =>
      householdsApi.revokeInvite(requireAccessToken(), input.householdId, input.inviteId),

    onSuccess: (_data, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: householdInvitesQueryKey(householdId) });
    },
  });
}

export function useRemoveMember() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { householdId: string; membershipId: string }) =>
      householdsApi.removeMember(requireAccessToken(), input.householdId, input.membershipId),

    onSuccess: (_data, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: householdMembersQueryKey(householdId) });
    },
  });
}

export function useTransferOwnership() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { householdId: string; targetMembershipId: string }) =>
      householdsApi.transferOwnership(requireAccessToken(), input.householdId, {
        target_membership_id: input.targetMembershipId,
      }),

    onSuccess: (_data, { householdId }) => {
      queryClient.invalidateQueries({ queryKey: householdMembersQueryKey(householdId) });
      queryClient.invalidateQueries({ queryKey: householdsQueryKey });
    },
  });
}

export function useLeaveHousehold() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (householdId: string) =>
      householdsApi.leaveHousehold(requireAccessToken(), householdId),

    onSuccess: (_data, householdId) => {
      useActiveHouseholdStore.getState().clearActiveHousehold();
      queryClient.invalidateQueries({ queryKey: householdsQueryKey });
      queryClient.removeQueries({ queryKey: householdMembersQueryKey(householdId) });
      queryClient.removeQueries({ queryKey: householdInvitesQueryKey(householdId) });
    },
  });
}
