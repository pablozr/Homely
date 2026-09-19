import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { API_URL } from '@/api/config';
import { ApiError } from '@/api/client';
import type { PendingInvite, PendingInviteStore } from '@/lib/pending-invite';
import { useActiveHouseholdStore } from '@/stores/active-household';
import { useSessionStore } from '@/stores/session';
import { acceptInvite, attemptPendingInvite, isTerminalInviteError } from './accept-invite';
import type { InviteAcceptData } from './types';

const user = {
  id: 'u1',
  fullname: 'Ada',
  email: 'ada@example.com',
  role: 'user',
  profile_completed: true,
  created_at: null,
};

const household = {
  id: 'h1',
  name: 'Casa da Praia',
  timezone: 'America/Sao_Paulo',
  default_due_time: '20:00:00',
  role: 'MEMBER',
  joined_at: '2026-01-01T00:00:00+00:00',
  created_at: '2026-01-01T00:00:00+00:00',
};

const acceptData: InviteAcceptData = {
  household,
  membership: { id: 'm1', user_id: 'u1', role: 'MEMBER', status: 'ACTIVE', joined_at: 'x' },
  membership_created: true,
  selected_household_id: 'h1',
};

function createMemoryStore(initial: PendingInvite | null) {
  let pending = initial;
  const events: string[] = [];

  const store: PendingInviteStore = {
    async get() {
      return pending;
    },
    async save(token: string, now?: number) {
      pending = { token, savedAt: now ?? Date.now() };
      return pending;
    },
    async clear() {
      events.push('clear');
      pending = null;
    },
  };

  return { store, events, current: () => pending };
}

function mockJson(context: TestContext, body: unknown, status = 200) {
  const calls: { url: string; init?: RequestInit }[] = [];

  context.mock.method(globalThis, 'fetch', async (...args: Parameters<typeof fetch>) => {
    calls.push({ url: String(args[0]), init: args[1] });
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  });

  return calls;
}

function resetStores() {
  useSessionStore.setState({ status: 'restoring', accessToken: null, user: null });
  useActiveHouseholdStore.setState({ activeHouseholdId: null });
}

test('attemptPendingInvite stays idle without a pending invite', async () => {
  const { store, events } = createMemoryStore(null);
  let calls = 0;

  const result = await attemptPendingInvite(store, {
    accept: async () => {
      calls += 1;
      return acceptData;
    },
  });

  assert.deepEqual(result, { status: 'idle' });
  assert.equal(calls, 0);
  assert.deepEqual(events, []);
});

test('attemptPendingInvite clears and reports acceptance on success', async () => {
  const { store, events, current } = createMemoryStore({ token: 'token-1', savedAt: 1 });
  const tokens: string[] = [];

  const result = await attemptPendingInvite(store, {
    accept: async (token) => {
      tokens.push(token);
      return acceptData;
    },
  });

  assert.deepEqual(result, { status: 'accepted', data: acceptData, token: 'token-1' });
  assert.deepEqual(tokens, ['token-1']);
  assert.deepEqual(events, ['clear']);
  assert.equal(current(), null);
});

test('attemptPendingInvite clears pending on terminal 404 and 409', async () => {
  for (const status of [404, 409]) {
    const { store, events, current } = createMemoryStore({ token: 'token-1', savedAt: 1 });

    const result = await attemptPendingInvite(store, {
      accept: async () => {
        throw new ApiError(status, 'gone');
      },
    });

    assert.deepEqual(result, { status: 'terminal', token: 'token-1' });
    assert.deepEqual(events, ['clear']);
    assert.equal(current(), null);
  }
});

test('attemptPendingInvite keeps pending for retry on 5xx and 429', async () => {
  for (const status of [500, 503, 429]) {
    const { store, events, current } = createMemoryStore({ token: 'token-1', savedAt: 1 });

    const result = await attemptPendingInvite(store, {
      accept: async () => {
        throw new ApiError(status, 'later');
      },
    });

    assert.deepEqual(result, { status: 'retry', token: 'token-1' });
    assert.deepEqual(events, []);
    assert.deepEqual(current(), { token: 'token-1', savedAt: 1 });
  }
});

test('attemptPendingInvite keeps pending on network failures', async () => {
  const { store, events, current } = createMemoryStore({ token: 'token-1', savedAt: 1 });

  const result = await attemptPendingInvite(store, {
    accept: async () => {
      throw new TypeError('Network request failed');
    },
  });

  assert.deepEqual(result, { status: 'retry', token: 'token-1' });
  assert.deepEqual(events, []);
  assert.deepEqual(current(), { token: 'token-1', savedAt: 1 });
});

test('attemptPendingInvite preserves a newer pending invite when acceptance succeeds', async () => {
  const { store, events, current } = createMemoryStore({ token: 'A', savedAt: 1 });
  const tokens: string[] = [];

  const first = await attemptPendingInvite(store, {
    accept: async (token) => {
      tokens.push(token);
      await store.save('B', 2);
      return acceptData;
    },
  });

  assert.deepEqual(first, { status: 'accepted', data: acceptData, token: 'A' });
  assert.deepEqual(tokens, ['A']);
  assert.deepEqual(events, []);
  assert.deepEqual(current(), { token: 'B', savedAt: 2 });

  const second = await attemptPendingInvite(store, {
    accept: async (token) => {
      tokens.push(token);
      return acceptData;
    },
  });

  assert.deepEqual(second, { status: 'accepted', data: acceptData, token: 'B' });
  assert.deepEqual(tokens, ['A', 'B']);
  assert.deepEqual(events, ['clear']);
  assert.equal(current(), null);
});

test('attemptPendingInvite preserves a newer pending invite on a terminal 404', async () => {
  const { store, events, current } = createMemoryStore({ token: 'A', savedAt: 1 });

  const result = await attemptPendingInvite(store, {
    accept: async () => {
      await store.save('B', 2);
      throw new ApiError(404, 'gone');
    },
  });

  assert.deepEqual(result, { status: 'terminal', token: 'A' });
  assert.deepEqual(events, []);
  assert.deepEqual(current(), { token: 'B', savedAt: 2 });
});

test('isTerminalInviteError only flags 404 and 409', () => {
  assert.equal(isTerminalInviteError(new ApiError(404, 'gone')), true);
  assert.equal(isTerminalInviteError(new ApiError(409, 'gone')), true);
  assert.equal(isTerminalInviteError(new ApiError(400, 'bad')), false);
  assert.equal(isTerminalInviteError(new ApiError(500, 'down')), false);
  assert.equal(isTerminalInviteError(new Error('boom')), false);
});

test('acceptInvite posts the token and activates the returned household', async (context) => {
  resetStores();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });

  const calls = mockJson(context, { message: 'Invite accepted', data: acceptData });

  const data = await acceptInvite('token-1');

  assert.equal(calls[0].url, `${API_URL}/households/invites/accept`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { invite_token: 'token-1' });
  assert.equal(data.selected_household_id, 'h1');
  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, 'h1');
});

test('acceptInvite throws without an access token and keeps the active household', async (context) => {
  resetStores();
  useActiveHouseholdStore.getState().setActiveHouseholdId('h0');

  const calls = mockJson(context, {});

  await assert.rejects(acceptInvite('token-1'), /Missing access token/);

  assert.equal(calls.length, 0);
  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, 'h0');
});

test('acceptInvite does not activate a household when the request fails', async (context) => {
  resetStores();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });
  useActiveHouseholdStore.getState().setActiveHouseholdId('h0');

  mockJson(context, { message: 'Invite unavailable', data: {} }, 409);

  await assert.rejects(acceptInvite('token-1'), /API request failed: 409/);

  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, 'h0');
});
