import { create } from 'zustand';

import type { AuthUser } from '@/api/client';

export type SessionStatus = 'restoring' | 'unauthenticated' | 'authenticated';

type SessionState = {
  status: SessionStatus;
  accessToken: string | null;
  user: AuthUser | null;
  setRestoring: () => void;
  setSession: (session: { user: AuthUser; accessToken: string }) => void;
  clearSession: () => void;
};

export const useSessionStore = create<SessionState>((set) => ({
  status: 'restoring',
  accessToken: null,
  user: null,
  setRestoring: () => set({ status: 'restoring', accessToken: null, user: null }),
  setSession: ({ user, accessToken }) => set({ status: 'authenticated', accessToken, user }),
  clearSession: () => set({ status: 'unauthenticated', accessToken: null, user: null }),
}));
