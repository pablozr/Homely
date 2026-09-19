import { create } from 'zustand';

export type PendingInviteStatus = 'idle' | 'accepted' | 'terminal' | 'retry';

type PendingInviteState = {
  token: string | null;
  status: PendingInviteStatus;

  setToken: (token: string | null) => void;
  setStatus: (status: PendingInviteStatus) => void;
  clear: () => void;
};

export const usePendingInviteStore = create<PendingInviteState>((set) => ({
  token: null,
  status: 'idle',

  setToken: (token) => set({ token, status: 'idle' }),

  setStatus: (status) => set({ status }),

  clear: () => set({ token: null, status: 'idle' }),
}));
