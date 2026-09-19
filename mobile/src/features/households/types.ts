import type { components } from '@/api/types.generated';

export type HouseholdCreateRequest = components['schemas']['HouseholdCreateRequestModel'];
export type HouseholdSummary = components['schemas']['HouseholdSummaryModel'];
export type HouseholdCreatedData = components['schemas']['HouseholdCreatedDataModel'];
export type HouseholdsData = components['schemas']['HouseholdsDataModel'];
export type HouseholdsResponse = components['schemas']['HouseholdsResponseModel'];
export type HouseholdCreatedResponse = components['schemas']['HouseholdCreatedResponseModel'];
export type HouseholdSelectionResponse = components['schemas']['HouseholdSelectionResponseModel'];

export type InviteAcceptRequest = components['schemas']['InviteAcceptRequestModel'];
export type InviteAcceptData = components['schemas']['InviteAcceptDataModel'];
export type InviteAcceptResponse = components['schemas']['InviteAcceptResponseModel'];
export type InviteCreatedData = components['schemas']['InviteCreatedDataModel'];
export type InviteCreatedResponse = components['schemas']['InviteCreatedResponseModel'];
export type InviteSummary = components['schemas']['InviteModel'];
export type InvitesData = components['schemas']['InvitesDataModel'];
export type InvitesResponse = components['schemas']['InvitesResponseModel'];
export type InviteRevokeResponse = components['schemas']['InviteRevokeResponseModel'];

export type MemberSummary = components['schemas']['MemberModel'];
export type MembershipsData = components['schemas']['MembershipsDataModel'];
export type MembershipsResponse = components['schemas']['MembershipsResponseModel'];
export type MembershipRemovedResponse = components['schemas']['MembershipRemovedResponseModel'];

export type HouseholdLeaveResponse = components['schemas']['HouseholdLeaveResponseModel'];
export type OwnershipTransferRequest = components['schemas']['OwnershipTransferRequestModel'];
export type OwnershipTransferResponse = components['schemas']['OwnershipTransferResponseModel'];
