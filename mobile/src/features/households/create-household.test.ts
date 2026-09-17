import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { API_URL } from '@/api/config';
import { useActiveHouseholdStore } from '@/stores/active-household';
import { useSessionStore } from '@/stores/session';
import { createHousehold } from './create-household';

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
  role: 'OWNER',
  joined_at: '2026-01-01T00:00:00+00:00',
  created_at: '2026-01-01T00:00:00+00:00',
};

type CapturedRequest = {
  url: string;
  init?: RequestInit;
};

function resetStores() {
  useSessionStore.setState({ status: 'restoring', accessToken: null, user: null });
  useActiveHouseholdStore.setState({ activeHouseholdId: null });
}

function mockJson(context: TestContext, body: unknown, status = 201): CapturedRequest[] {
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

test('createHousehold posts with the idempotency key and activates the selected household', async (context) => {
  resetStores();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });

  const calls = mockJson(context, {
    message: 'Household created',
    data: { household, selected_household_id: 'h1' },
  });

  const data = await createHousehold({
    name: 'Casa da Praia',
    timezone: 'America/Sao_Paulo',
    idempotencyKey: 'idem-1',
  });

  assert.equal(calls[0].url, `${API_URL}/households`);
  assert.equal(calls[0].init?.method, 'POST');

  const headers = calls[0].init?.headers as Record<string, string>;
  assert.equal(headers.Authorization, 'Bearer access-1');
  assert.equal(headers['Idempotency-Key'], 'idem-1');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
    name: 'Casa da Praia',
    timezone: 'America/Sao_Paulo',
  });
  assert.equal(data.household.id, 'h1');
  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, 'h1');
});

test('createHousehold throws without an access token and does not call the API', async (context) => {
  resetStores();

  const calls = mockJson(context, {});

  await assert.rejects(
    createHousehold({ name: 'Casa', timezone: 'UTC', idempotencyKey: 'idem-1' }),
    /Missing access token/,
  );

  assert.equal(calls.length, 0);
  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, null);
});

test('createHousehold keeps the previous active household on failure', async (context) => {
  resetStores();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });
  useActiveHouseholdStore.getState().setActiveHouseholdId('h0');

  mockJson(context, { message: 'Unavailable', data: {} }, 503);

  await assert.rejects(
    createHousehold({ name: 'Casa', timezone: 'UTC', idempotencyKey: 'idem-1' }),
    /API request failed: 503/,
  );

  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, 'h0');
});
