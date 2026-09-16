import { api } from '@/api/client';
import type { TokenStore } from '@/lib/secure-store';
import { useSessionStore } from '@/stores/session';

let sessionOperation = Promise.resolve();

function runSessionOperation(operation: () => Promise<void>): Promise<void> {
  const nextOperation = sessionOperation.then(operation, operation);
  sessionOperation = nextOperation.catch(() => undefined);
  return nextOperation;
}

async function exchangeCode(authCode: string, refreshTokens: TokenStore): Promise<void> {
  const { data } = await api.exchange({ auth_code: authCode });

  await refreshTokens.set(data.refresh_token);
  useSessionStore.getState().setSession({ user: data.user, accessToken: data.access_token });
}

async function refreshStoredSession(refreshTokens: TokenStore): Promise<void> {
  if (useSessionStore.getState().status !== 'authenticated') {
    useSessionStore.getState().setRestoring();
  }

  let refreshToken: string | null = null;
  let rotatedRefreshToken: string | null = null;

  try {
    refreshToken = await refreshTokens.get();

    if (!refreshToken) {
      useSessionStore.getState().clearSession();
      return;
    }

    const refreshed = await api.refresh({ refresh_token: refreshToken });
    await refreshTokens.set(refreshed.data.refresh_token);
    rotatedRefreshToken = refreshed.data.refresh_token;
    const me = await api.me(refreshed.data.access_token);

    if (useSessionStore.getState().status === 'restoring') {
      useSessionStore
        .getState()
        .setSession({ user: me.data.user, accessToken: refreshed.data.access_token });
    }
  } catch {
    if (useSessionStore.getState().status === 'restoring') {
      if (!rotatedRefreshToken && (await refreshTokens.get()) === refreshToken) {
        await refreshTokens.clear();
      }
      useSessionStore.getState().clearSession();
    }
  }
}

async function endSession(refreshTokens: TokenStore): Promise<void> {
  const refreshToken = await refreshTokens.get();

  if (refreshToken) {
    try {
      await api.logout({ refresh_token: refreshToken });
    } catch {
      // A failed revocation should not block the local session from ending.
    }
  }

  await refreshTokens.clear();
  useSessionStore.getState().clearSession();
}

export function establishSessionFromCode(authCode: string, refreshTokens: TokenStore): Promise<void> {
  return runSessionOperation(() => exchangeCode(authCode, refreshTokens));
}

export function restoreSession(refreshTokens: TokenStore): Promise<void> {
  return runSessionOperation(() => refreshStoredSession(refreshTokens));
}

export function signOut(refreshTokens: TokenStore): Promise<void> {
  return runSessionOperation(() => endSession(refreshTokens));
}
