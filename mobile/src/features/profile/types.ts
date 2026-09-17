import type { components } from '@/api/types.generated';

export type ProfileUpdateRequest = components['schemas']['ProfileUpdateRequestModel'];

export type ProfileUser = {
  id: string;
  fullname: string;
  initials: string;
  role: string;
  profile_completed: boolean;
  created_at: string | null;
};

export type ProfileResponse = {
  message: string;
  data: { user: ProfileUser };
};
