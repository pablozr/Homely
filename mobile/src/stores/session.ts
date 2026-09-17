import { create } from 'zustand';

import type { AuthUser } from '@/features/auth/types';

export type SessionStatus = 'restoring' | 'unauthenticated' | 'authenticated';

type SessionState = {
  status: SessionStatus;
  accessToken: string | null;
  user: AuthUser | null;

  setRestoring: () => void;
  setSession: (session: { user: AuthUser; accessToken: string }) => void;
  updateUser: (user: Partial<AuthUser>) => void;
  clearSession: () => void;
};

export const useSessionStore = create<SessionState>((set) => ({
  status: 'restoring',
  accessToken: null,
  user: null,

  setRestoring: () => set({ status: 'restoring', accessToken: null, user: null }),

  setSession: ({ user, accessToken }) => set({ status: 'authenticated', accessToken, user }),

  updateUser: (user) =>
    set((state) => (state.user === null ? state : { user: { ...state.user, ...user } })),

  clearSession: () => set({ status: 'unauthenticated', accessToken: null, user: null }),
}));
