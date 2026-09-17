import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { API_URL } from '@/api/config';
import { profileApi } from './api';

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

test('loads the profile without exposing the email', async (context) => {
  const calls = mockFetch(context, {
    message: 'Profile retrieved',
    data: {
      user: {
        id: 'u1',
        fullname: 'Ada',
        initials: 'A',
        role: 'user',
        profile_completed: false,
        created_at: null,
      },
    },
  });

  const response = await profileApi.getProfile('access-1');

  assert.equal(calls[0].url, `${API_URL}/profile/me`);
  assert.equal(calls[0].init?.method, 'GET');
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.equal(response.data.user.profile_completed, false);
  assert.equal('email' in response.data.user, false);
});

test('updates the profile with a PATCH request and the access token', async (context) => {
  const calls = mockFetch(context, {
    message: 'Profile updated',
    data: {
      user: {
        id: 'u1',
        fullname: 'Ada Lovelace',
        initials: 'AL',
        role: 'user',
        profile_completed: true,
        created_at: null,
      },
    },
  });

  const response = await profileApi.updateProfile('access-1', { fullname: 'Ada Lovelace' });

  assert.equal(calls[0].url, `${API_URL}/profile/me`);
  assert.equal(calls[0].init?.method, 'PATCH');
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { fullname: 'Ada Lovelace' });
  assert.equal(response.data.user.profile_completed, true);
});
