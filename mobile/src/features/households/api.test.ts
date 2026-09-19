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

test('accepts an invite with the token body and access token', async (context) => {
  const calls = mockFetch(context, {
    message: 'Invite accepted',
    data: {
      household,
      membership: { id: 'm1', user_id: 'u1', role: 'MEMBER', status: 'ACTIVE', joined_at: 'x' },
      membership_created: true,
      selected_household_id: 'h1',
    },
  });

  const response = await householdsApi.acceptInvite('access-1', { invite_token: 'token-1' });

  assert.equal(calls[0].url, `${API_URL}/households/invites/accept`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { invite_token: 'token-1' });
  assert.equal(response.data.selected_household_id, 'h1');
});

test('creates an invite with idempotency key and without a body', async (context) => {
  const calls = mockFetch(
    context,
    {
      message: 'Invite created',
      data: {
        id: 'i1',
        household_id: 'h1',
        created_at: 'x',
        expires_at: 'y',
        invite_url: 'homely://invite?invite_token=token-1',
      },
    },
    201,
  );

  const response = await householdsApi.createInvite('access-1', 'h1', 'idem-1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/invites`);
  assert.equal(calls[0].init?.method, 'POST');

  const headers = calls[0].init?.headers as Record<string, string>;
  assert.equal(headers.Authorization, 'Bearer access-1');
  assert.equal(headers['Idempotency-Key'], 'idem-1');
  assert.equal(calls[0].init?.body, undefined);
  assert.equal(response.data.invite_url, 'homely://invite?invite_token=token-1');
});

test('lists outstanding invites for a household', async (context) => {
  const calls = mockFetch(context, {
    message: 'Invites retrieved',
    data: {
      invites: [{ id: 'i1', household_id: 'h1', created_at: 'x', expires_at: 'y' }],
    },
  });

  const response = await householdsApi.listInvites('access-1', 'h1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/invites`);
  assert.equal(calls[0].init?.method, 'GET');
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.equal(response.data.invites[0].id, 'i1');
});

test('revokes an invite with a bodyless POST', async (context) => {
  const calls = mockFetch(context, {
    message: 'Invite revoked',
    data: { invite_id: 'i1', revoked_at: 'z' },
  });

  const response = await householdsApi.revokeInvite('access-1', 'h1', 'i1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/invites/i1/revoke`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.equal(calls[0].init?.body, undefined);
  assert.equal(response.data.invite_id, 'i1');
});

test('lists active members for a household', async (context) => {
  const calls = mockFetch(context, {
    message: 'Members retrieved',
    data: {
      memberships: [
        {
          id: 'm1',
          user_id: 'u1',
          role: 'OWNER',
          status: 'ACTIVE',
          joined_at: 'x',
          fullname: 'Ada',
        },
      ],
    },
  });

  const response = await householdsApi.listMembers('access-1', 'h1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/members`);
  assert.equal(calls[0].init?.method, 'GET');
  assert.equal(response.data.memberships[0].fullname, 'Ada');
});

test('removes a member with a bodyless POST', async (context) => {
  const calls = mockFetch(context, {
    message: 'Member removed',
    data: { membership_id: 'm2', removed_at: 'z' },
  });

  const response = await householdsApi.removeMember('access-1', 'h1', 'm2');

  assert.equal(calls[0].url, `${API_URL}/households/h1/members/m2/remove`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.equal(calls[0].init?.body, undefined);
  assert.equal(response.data.membership_id, 'm2');
});

test('leaves a household with a bodyless POST', async (context) => {
  const calls = mockFetch(context, {
    message: 'Household left',
    data: { household_id: 'h1', left_at: 'z' },
  });

  const response = await householdsApi.leaveHousehold('access-1', 'h1');

  assert.equal(calls[0].url, `${API_URL}/households/h1/leave`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.equal(calls[0].init?.body, undefined);
  assert.equal(response.data.household_id, 'h1');
});

test('transfers ownership with the target membership body', async (context) => {
  const calls = mockFetch(context, {
    message: 'Ownership transferred',
    data: {
      household_id: 'h1',
      previous_owner_membership_id: 'm1',
      previous_owner_role: 'MEMBER',
      new_owner_membership_id: 'm2',
      new_owner_role: 'OWNER',
    },
  });

  const response = await householdsApi.transferOwnership('access-1', 'h1', {
    target_membership_id: 'm2',
  });

  assert.equal(calls[0].url, `${API_URL}/households/h1/ownership-transfer`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { target_membership_id: 'm2' });
  assert.equal(response.data.new_owner_membership_id, 'm2');
});
