import { request } from '@/api/client';

import type { ProfileResponse, ProfileUpdateRequest } from './types';

export const profileApi = {
  getProfile(token: string): Promise<ProfileResponse> {
    return request<ProfileResponse>('/profile/me', { token });
  },

  updateProfile(token: string, body: ProfileUpdateRequest): Promise<ProfileResponse> {
    return request<ProfileResponse>('/profile/me', { method: 'PATCH', body, token });
  },
};
