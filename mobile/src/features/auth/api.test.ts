import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { API_URL } from '@/api/config';
import { authApi } from './api';

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

test('requests a magic link with the email payload', async (context) => {
  const calls = mockFetch(context, { message: 'Magic link sent', data: {} });

  await authApi.requestMagicLink({ email: 'person@example.com' });

  assert.equal(calls[0].url, `${API_URL}/auth/magic-link`);
  assert.equal(calls[0].init?.method, 'POST');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { email: 'person@example.com' });
});

test('exchanges a magic link code for a session', async (context) => {
  const calls = mockFetch(context, {
    message: 'Session created',
    data: {
      user: { id: 'u1', fullname: 'Ada', email: 'ada@example.com', role: 'user', created_at: null },
      access_token: 'access-1',
      refresh_token: 'refresh-1',
    },
  });

  const response = await authApi.exchange({ auth_code: 'code-1' });

  assert.equal(calls[0].url, `${API_URL}/auth/exchange`);
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { auth_code: 'code-1' });
  assert.equal(response.data.access_token, 'access-1');
  assert.equal(response.data.user.email, 'ada@example.com');
});

test('refreshes a session with the stored refresh token', async (context) => {
  const calls = mockFetch(context, {
    message: 'Token refreshed',
    data: { access_token: 'access-2', refresh_token: 'refresh-2' },
  });

  await authApi.refresh({ refresh_token: 'refresh-1' });

  assert.equal(calls[0].url, `${API_URL}/auth/refresh`);
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { refresh_token: 'refresh-1' });
});

test('logs out the stored refresh token', async (context) => {
  const calls = mockFetch(context, { message: 'Logged out', data: {} });

  await authApi.logout({ refresh_token: 'refresh-1' });

  assert.equal(calls[0].url, `${API_URL}/auth/logout`);
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { refresh_token: 'refresh-1' });
});

test('authenticates the current user request with the access token', async (context) => {
  const calls = mockFetch(context, {
    data: {
      user: { id: 'u1', fullname: 'Ada', email: 'ada@example.com', role: 'user', created_at: null },
    },
  });

  await authApi.me('access-1');

  assert.equal(calls[0].url, `${API_URL}/auth/me`);
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
});
