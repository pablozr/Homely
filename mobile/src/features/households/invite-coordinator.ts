import { householdsQueryKey, queryClient } from '@/lib/query-client';
import { pendingInviteStorage } from '@/lib/secure-store';
import { runAfterSessionOperations } from '@/features/auth/session';
import { usePendingInviteStore } from '@/stores/pending-invite';
import { useSessionStore } from '@/stores/session';
import { acceptInvite, attemptPendingInvite, type InviteAcceptanceResult } from './accept-invite';

function applyResult(result: InviteAcceptanceResult): void {
  if (result.status === 'idle') {
    usePendingInviteStore.getState().clear();
    return;
  }

  const store = usePendingInviteStore.getState();
  const isCurrent = store.token === result.token;

  if (result.status === 'accepted') {
    if (isCurrent) {
      store.clear();
      store.setStatus('accepted');
    }

    queryClient.invalidateQueries({ queryKey: householdsQueryKey });
    return;
  }

  if (result.status === 'terminal') {
    if (isCurrent) {
      store.clear();
      store.setStatus('terminal');
    }

    return;
  }

  if (isCurrent) {
    store.setStatus('retry');
  }
}

export async function acceptPendingInvite(): Promise<InviteAcceptanceResult> {
  if (useSessionStore.getState().status !== 'authenticated') {
    return { status: 'idle' };
  }

  const result = await attemptPendingInvite(pendingInviteStorage, { accept: acceptInvite });
  applyResult(result);

  return result;
}

export function runPendingInviteAcceptance(): Promise<InviteAcceptanceResult> {
  return runAfterSessionOperations(acceptPendingInvite);
}

export async function storePendingInvite(token: string): Promise<void> {
  await pendingInviteStorage.save(token);
  usePendingInviteStore.getState().setToken(token);
}

export async function submitInviteToken(token: string): Promise<InviteAcceptanceResult> {
  await storePendingInvite(token);

  if (useSessionStore.getState().status !== 'authenticated') {
    return { status: 'idle' };
  }

  return runPendingInviteAcceptance();
}

export async function hydratePendingInvite(): Promise<void> {
  const pending = await pendingInviteStorage.get();
  usePendingInviteStore.getState().setToken(pending?.token ?? null);
}
