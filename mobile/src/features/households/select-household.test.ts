import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { API_URL } from '@/api/config';
import { useActiveHouseholdStore } from '@/stores/active-household';
import { useSessionStore } from '@/stores/session';
import { selectHousehold } from './select-household';

const user = {
  id: 'u1',
  fullname: 'Ada',
  email: 'ada@example.com',
  role: 'user',
  profile_completed: true,
  created_at: null,
};

type CapturedRequest = {
  url: string;
  init?: RequestInit;
};

function resetStores() {
  useSessionStore.setState({ status: 'restoring', accessToken: null, user: null });
  useActiveHouseholdStore.setState({ activeHouseholdId: null });
}

function mockJson(context: TestContext, body: unknown, status = 200): CapturedRequest[] {
  const calls: CapturedRequest[] = [];

  context.mock.method(globalThis, 'fetch', async (...args: Parameters<typeof fetch>) => {
    calls.push({ url: String(args[0]), init: args[1] });
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  });

  return calls;
}

test('selectHousehold patches the selection and only then updates the active household', async (context) => {
  resetStores();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });
  useActiveHouseholdStore.getState().setActiveHouseholdId('h1');

  const calls = mockJson(context, {
    message: 'Household selected',
    data: { selected_household_id: 'h2' },
  });

  const selected = await selectHousehold('h2');

  assert.equal(calls[0].url, `${API_URL}/households/h2/selection`);
  assert.equal(calls[0].init?.method, 'PATCH');
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.equal(selected, 'h2');
  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, 'h2');
});

test('selectHousehold does not update the active household when the request fails', async (context) => {
  resetStores();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });
  useActiveHouseholdStore.getState().setActiveHouseholdId('h1');

  mockJson(context, { message: 'Unavailable', data: {} }, 503);

  await assert.rejects(selectHousehold('h2'), /API request failed: 503/);

  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, 'h1');
});

test('selectHousehold throws without an access token', async (context) => {
  resetStores();

  const calls = mockJson(context, {});

  await assert.rejects(selectHousehold('h2'), /Missing access token/);

  assert.equal(calls.length, 0);
});
