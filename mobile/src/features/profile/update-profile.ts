import { useSessionStore } from '@/stores/session';
import { profileApi } from './api';
import type { ProfileUser } from './types';

export async function updateProfile(fullname: string): Promise<ProfileUser> {
  const accessToken = useSessionStore.getState().accessToken;

  if (!accessToken) {
    throw new Error('Missing access token');
  }

  const { data } = await profileApi.updateProfile(accessToken, { fullname });

  useSessionStore.getState().updateUser({
    fullname: data.user.fullname,
    profile_completed: data.user.profile_completed,
  });

  return data.user;
}
