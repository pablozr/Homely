import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { QueryClient } from '@tanstack/react-query';

import { clearHouseholdCache, householdsQueryKey, queryClient } from '@/lib/query-client';
import { useActiveHouseholdStore } from '@/stores/active-household';
import { useSessionStore } from '@/stores/session';
import { establishSessionFromCode, restoreSession, signOut } from './session';

const user = {
  id: 'u1',
  fullname: 'Ada',
  email: 'ada@example.com',
  role: 'user',
  profile_completed: false,
  created_at: null,
};

type CapturedRequest = {
  url: string;
  init?: RequestInit;
};

function createTokenStore(initial: string | null) {
  let token = initial;

  return {
    current: () => token,

    get: async () => token,

    set: async (next: string) => {
      token = next;
    },

    clear: async () => {
      token = null;
    },
  };
}

function resetSession() {
  useSessionStore.setState({ status: 'restoring', accessToken: null, user: null });
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function mockJson(context: TestContext, body: unknown, status = 200): CapturedRequest[] {
  const calls: CapturedRequest[] = [];

  context.mock.method(globalThis, 'fetch', async (...args: Parameters<typeof fetch>) => {
    calls.push({ url: String(args[0]), init: args[1] });
    return jsonResponse(body, status);
  });

  return calls;
}

test('establishSessionFromCode stores only the refresh token and keeps the access token in memory', async (context) => {
  resetSession();

  const store = createTokenStore(null);
  mockJson(context, {
    message: 'Session created',
    data: { user, access_token: 'access-1', refresh_token: 'refresh-1' },
  });

  await establishSessionFromCode('code-1', store);

  assert.equal(store.current(), 'refresh-1');
  assert.equal(useSessionStore.getState().status, 'authenticated');
  assert.equal(useSessionStore.getState().accessToken, 'access-1');
  assert.deepEqual(useSessionStore.getState().user, user);
});

test('restoreSession goes straight to unauthenticated without a stored refresh token', async (context) => {
  resetSession();

  const store = createTokenStore(null);
  const calls = mockJson(context, {});

  await restoreSession(store);

  assert.equal(useSessionStore.getState().status, 'unauthenticated');
  assert.equal(calls.length, 0);
});

test('restoreSession refreshes tokens and loads the user silently', async (context) => {
  resetSession();

  const store = createTokenStore('refresh-1');
  const calls: CapturedRequest[] = [];

  context.mock.method(globalThis, 'fetch', async (...args: Parameters<typeof fetch>) => {
    const url = String(args[0]);
    calls.push({ url, init: args[1] });

    if (url.endsWith('/auth/refresh')) {
      return jsonResponse({
        message: 'Token refreshed',
        data: { access_token: 'access-2', refresh_token: 'refresh-2' },
      });
    }

    if (url.endsWith('/auth/me')) {
      return jsonResponse({ data: { user } });
    }

    return jsonResponse({ message: 'Not found', data: {} }, 404);
  });

  await restoreSession(store);

  assert.equal(store.current(), 'refresh-2');
  assert.equal(useSessionStore.getState().status, 'authenticated');
  assert.equal(useSessionStore.getState().accessToken, 'access-2');
  assert.deepEqual(useSessionStore.getState().user, user);
  assert.equal((calls[1].init?.headers as Record<string, string>).Authorization, 'Bearer access-2');
});

test('restoreSession clears a rejected refresh token', async (context) => {
  resetSession();

  const store = createTokenStore('stale');
  mockJson(context, { message: 'Invalid refresh token', data: {} }, 401);

  await restoreSession(store);

  assert.equal(store.current(), null);
  assert.equal(useSessionStore.getState().status, 'unauthenticated');
});

test('restoreSession keeps the rotated token and exits restoration when profile loading fails', async (context) => {
  resetSession();

  const store = createTokenStore('refresh-1');

  context.mock.method(globalThis, 'fetch', async (...args: Parameters<typeof fetch>) => {
    if (String(args[0]).endsWith('/auth/refresh')) {
      return jsonResponse({
        message: 'Token refreshed',
        data: { access_token: 'access-2', refresh_token: 'refresh-2' },
      });
    }

    return jsonResponse({ message: 'Unavailable', data: {} }, 503);
  });

  await restoreSession(store);

  assert.equal(store.current(), 'refresh-2');
  assert.equal(useSessionStore.getState().status, 'unauthenticated');
});

test('serializes a deep link exchange before session restoration', async (context) => {
  resetSession();

  const store = createTokenStore('stale-refresh');
  const calls: CapturedRequest[] = [];

  context.mock.method(globalThis, 'fetch', async (...args: Parameters<typeof fetch>) => {
    const url = String(args[0]);
    calls.push({ url, init: args[1] });

    if (url.endsWith('/auth/exchange')) {
      return jsonResponse({
        message: 'Session created',
        data: { user, access_token: 'access-1', refresh_token: 'refresh-1' },
      });
    }

    if (url.endsWith('/auth/refresh')) {
      return jsonResponse({
        message: 'Token refreshed',
        data: { access_token: 'access-2', refresh_token: 'refresh-2' },
      });
    }

    return jsonResponse({ data: { user } });
  });

  await Promise.all([establishSessionFromCode('code-1', store), restoreSession(store)]);

  assert.equal(calls[0].url.endsWith('/auth/exchange'), true);
  assert.equal(calls[1].url.endsWith('/auth/refresh'), true);
  assert.equal(store.current(), 'refresh-2');
  assert.equal(useSessionStore.getState().status, 'authenticated');
});

test('signOut revokes the refresh token and clears the local session', async (context) => {
  resetSession();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });
  useActiveHouseholdStore.getState().setActiveHouseholdId('h1');

  const store = createTokenStore('refresh-1');
  const calls = mockJson(context, { message: 'Logged out', data: {} });

  await signOut(store);

  assert.equal(calls[0].url.endsWith('/auth/logout'), true);
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { refresh_token: 'refresh-1' });
  assert.equal(store.current(), null);
  assert.equal(useSessionStore.getState().status, 'unauthenticated');
  assert.equal(useSessionStore.getState().accessToken, null);
  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, null);
});

test('signOut still ends the local session when revocation fails', async (context) => {
  resetSession();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });
  useActiveHouseholdStore.getState().setActiveHouseholdId('h1');

  const store = createTokenStore('refresh-1');
  mockJson(context, { message: 'Internal server error', data: {} }, 500);

  await signOut(store);

  assert.equal(store.current(), null);
  assert.equal(useSessionStore.getState().status, 'unauthenticated');
  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, null);
});

test('signOut removes the cached households so the next login cannot leak them', async (context) => {
  resetSession();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });
  useActiveHouseholdStore.getState().setActiveHouseholdId('h1');

  const store = createTokenStore('refresh-1');
  mockJson(context, { message: 'Logged out', data: {} });

  const client = new QueryClient();
  client.setQueryData(householdsQueryKey, {
    message: 'Households retrieved',
    data: { households: [{ id: 'previous-account' }], selected_household_id: 'previous-account' },
  });

  await signOut(store, () => clearHouseholdCache(client));

  assert.equal(client.getQueryData(householdsQueryKey), undefined);
});

test('signOut clears the shared query client used by the app provider', async (context) => {
  resetSession();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });

  const store = createTokenStore('refresh-1');
  mockJson(context, { message: 'Logged out', data: {} });
  queryClient.setQueryData(householdsQueryKey, {
    message: 'Households retrieved',
    data: { households: [{ id: 'previous-account' }], selected_household_id: 'previous-account' },
  });

  await signOut(store);

  assert.equal(queryClient.getQueryData(householdsQueryKey), undefined);
});
