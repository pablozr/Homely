import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { API_URL } from '@/api/config';
import { householdsApi } from './api';

type CapturedRequest = {
  url: string;
  init?: RequestInit;
};

function mockFetch(context: TestContext, body: unknown, status = 200) {
  const calls: CapturedRequest[] = [];

  context.mock.method(globalThis, 'fetch', async (...args: Parameters<typeof fetch>) => {
    calls.push({ url: String(args[0]), init: args[1] });
    return new Response(JSON.stringify(body), { status });
  });

  return calls;
}

const household = {
  id: 'h1',
  name: 'Casa da Praia',
  timezone: 'America/Sao_Paulo',
  default_due_time: '20:00:00',
  role: 'OWNER',
  joined_at: '2026-01-01T00:00:00+00:00',
  created_at: '2026-01-01T00:00:00+00:00',
};

test('creates a household with the access token and idempotency key', async (context) => {
  const calls = mockFetch(context, {
    message: 'Household created',
    data: { household, selected_household_id: 'h1' },
  });

  const response = await householdsApi.createHousehold(
    'access-1',
    { name: 'Casa da Praia', timezone: 'America/Sao_Paulo' },
    'idem-1',
  );

  assert.equal(calls[0].url, `${API_URL}/households`);
  assert.equal(calls[0].init?.method, 'POST');

  const headers = calls[0].init?.headers as Record<string, string>;
  assert.equal(headers.Authorization, 'Bearer access-1');
  assert.equal(headers['Idempotency-Key'], 'idem-1');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
    name: 'Casa da Praia',
    timezone: 'America/Sao_Paulo',
  });
  assert.equal(response.data.household.role, 'OWNER');
  assert.equal(response.data.selected_household_id, 'h1');
});

test('lists households with the access token', async (context) => {
  const calls = mockFetch(context, {
    message: 'Households retrieved',
    data: { households: [household], selected_household_id: 'h1' },
  });

  const response = await householdsApi.listHouseholds('access-1');

  assert.equal(calls[0].url, `${API_URL}/households`);
  assert.equal(calls[0].init?.method, 'GET');
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.equal(response.data.households[0].name, 'Casa da Praia');
});

test('selects a household with a bodyless PATCH and the access token', async (context) => {
  const calls = mockFetch(context, {
    message: 'Household selected',
    data: { selected_household_id: 'h2' },
  });

  const response = await householdsApi.selectHousehold('access-1', 'h2');

  assert.equal(calls[0].url, `${API_URL}/households/h2/selection`);
  assert.equal(calls[0].init?.method, 'PATCH');
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.equal(calls[0].init?.body, undefined);
  assert.equal(response.data.selected_household_id, 'h2');
});
