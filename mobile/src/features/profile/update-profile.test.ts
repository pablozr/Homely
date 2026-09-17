import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { API_URL } from '@/api/config';
import { useSessionStore } from '@/stores/session';
import { updateProfile } from './update-profile';

const user = {
  id: 'u1',
  fullname: 'ada',
  email: 'ada@example.com',
  role: 'user',
  profile_completed: false,
  created_at: null,
};

type CapturedRequest = {
  url: string;
  init?: RequestInit;
};

function resetSession() {
  useSessionStore.setState({ status: 'restoring', accessToken: null, user: null });
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

test('updateProfile sends the fullname and merges the profile into the session', async (context) => {
  resetSession();
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });

  const calls = mockJson(context, {
    message: 'Profile updated',
    data: {
      user: {
        ...user,
        fullname: 'Ada Lovelace',
        initials: 'AL',
        profile_completed: true,
      },
    },
  });

  const profile = await updateProfile('Ada Lovelace');

  assert.equal(calls[0].url, `${API_URL}/profile/me`);
  assert.equal(calls[0].init?.method, 'PATCH');
  assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer access-1');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { fullname: 'Ada Lovelace' });
  assert.equal(profile.profile_completed, true);

  const session = useSessionStore.getState();
  assert.equal(session.accessToken, 'access-1');
  assert.equal(session.status, 'authenticated');
  assert.equal(session.user?.fullname, 'Ada Lovelace');
  assert.equal(session.user?.profile_completed, true);
  assert.equal(session.user?.email, 'ada@example.com');
});

test('updateProfile throws without an access token and does not call the API', async (context) => {
  resetSession();

  const calls = mockJson(context, {});

  await assert.rejects(updateProfile('Ada Lovelace'), /Missing access token/);

  assert.equal(calls.length, 0);
});
