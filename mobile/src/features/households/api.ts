import { request } from '@/api/client';

import type {
  HouseholdCreateRequest,
  HouseholdCreatedResponse,
  HouseholdLeaveResponse,
  HouseholdSelectionResponse,
  HouseholdsResponse,
  InviteAcceptRequest,
  InviteAcceptResponse,
  InviteCreatedResponse,
  InviteRevokeResponse,
  InvitesResponse,
  MembershipRemovedResponse,
  MembershipsResponse,
  OwnershipTransferRequest,
  OwnershipTransferResponse,
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

  acceptInvite(token: string, body: InviteAcceptRequest): Promise<InviteAcceptResponse> {
    return request<InviteAcceptResponse>('/households/invites/accept', {
      method: 'POST',
      body,
      token,
    });
  },

  createInvite(
    token: string,
    householdId: string,
    idempotencyKey: string,
  ): Promise<InviteCreatedResponse> {
    return request<InviteCreatedResponse>(`/households/${householdId}/invites`, {
      method: 'POST',
      token,
      headers: { 'Idempotency-Key': idempotencyKey },
    });
  },

  listInvites(token: string, householdId: string): Promise<InvitesResponse> {
    return request<InvitesResponse>(`/households/${householdId}/invites`, { token });
  },

  revokeInvite(
    token: string,
    householdId: string,
    inviteId: string,
  ): Promise<InviteRevokeResponse> {
    return request<InviteRevokeResponse>(`/households/${householdId}/invites/${inviteId}/revoke`, {
      method: 'POST',
      token,
    });
  },

  listMembers(token: string, householdId: string): Promise<MembershipsResponse> {
    return request<MembershipsResponse>(`/households/${householdId}/members`, { token });
  },

  removeMember(
    token: string,
    householdId: string,
    membershipId: string,
  ): Promise<MembershipRemovedResponse> {
    return request<MembershipRemovedResponse>(
      `/households/${householdId}/members/${membershipId}/remove`,
      { method: 'POST', token },
    );
  },

  leaveHousehold(token: string, householdId: string): Promise<HouseholdLeaveResponse> {
    return request<HouseholdLeaveResponse>(`/households/${householdId}/leave`, {
      method: 'POST',
      token,
    });
  },

  transferOwnership(
    token: string,
    householdId: string,
    body: OwnershipTransferRequest,
  ): Promise<OwnershipTransferResponse> {
    return request<OwnershipTransferResponse>(`/households/${householdId}/ownership-transfer`, {
      method: 'POST',
      body,
      token,
    });
  },
};
