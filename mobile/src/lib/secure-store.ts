import * as SecureStore from 'expo-secure-store';

import {
  createPendingInvite,
  parsePendingInvite,
  type PendingInvite,
  type PendingInviteStore,
} from '@/lib/pending-invite';

const REFRESH_TOKEN_KEY = 'homely.refresh_token';
const PENDING_INVITE_KEY = 'homely.pending_invite';

export type TokenStore = {
  get(): Promise<string | null>;
  set(refreshToken: string): Promise<void>;
  clear(): Promise<void>;
};

export const refreshTokenStorage: TokenStore = {
  get() {
    return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  },

  set(refreshToken) {
    return SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
  },

  clear() {
    return SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  },
};

export const pendingInviteStorage: PendingInviteStore = {
  async get(now?: number): Promise<PendingInvite | null> {
    const raw = await SecureStore.getItemAsync(PENDING_INVITE_KEY);
    const invite = parsePendingInvite(raw, now);

    if (raw !== null && invite === null) {
      await SecureStore.deleteItemAsync(PENDING_INVITE_KEY);
    }

    return invite;
  },

  async save(token: string, now?: number): Promise<PendingInvite> {
    const invite = createPendingInvite(token, now);
    await SecureStore.setItemAsync(PENDING_INVITE_KEY, JSON.stringify(invite));

    return invite;
  },

  clear() {
    return SecureStore.deleteItemAsync(PENDING_INVITE_KEY);
  },
};
