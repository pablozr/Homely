import { ApiError } from '@/api/client';
import type { PendingInviteStore } from '@/lib/pending-invite';
import { useActiveHouseholdStore } from '@/stores/active-household';
import { useSessionStore } from '@/stores/session';
import { householdsApi } from './api';
import type { InviteAcceptData } from './types';

export async function acceptInvite(token: string): Promise<InviteAcceptData> {
  const accessToken = useSessionStore.getState().accessToken;

  if (!accessToken) {
    throw new Error('Missing access token');
  }

  const { data } = await householdsApi.acceptInvite(accessToken, { invite_token: token });

  useActiveHouseholdStore.getState().setActiveHouseholdId(data.selected_household_id);

  return data;
}

export function isTerminalInviteError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 409);
}

export type InviteAcceptanceResult =
  | { status: 'idle' }
  | { status: 'accepted'; data: InviteAcceptData; token: string }
  | { status: 'terminal'; token: string }
  | { status: 'retry'; token: string };

export type InviteAcceptanceDeps = {
  accept: (token: string) => Promise<InviteAcceptData>;
  now?: number;
};

async function clearProcessedInvite(
  store: PendingInviteStore,
  token: string,
  now?: number,
): Promise<void> {
  const current = await store.get(now);

  if (current !== null && current.token === token) {
    await store.clear();
  }
}

export async function attemptPendingInvite(
  store: PendingInviteStore,
  deps: InviteAcceptanceDeps,
): Promise<InviteAcceptanceResult> {
  const pending = await store.get(deps.now);
  const token = pending?.token ?? null;

  if (token === null) {
    return { status: 'idle' };
  }

  try {
    const data = await deps.accept(token);
    await clearProcessedInvite(store, token, deps.now);

    return { status: 'accepted', data, token };
  } catch (error) {
    if (isTerminalInviteError(error)) {
      await clearProcessedInvite(store, token, deps.now);

      return { status: 'terminal', token };
    }

    return { status: 'retry', token };
  }
}
