import assert from 'node:assert/strict';
import test from 'node:test';

import { useSessionStore } from './session';

const user = {
  id: 'u1',
  fullname: 'Ada',
  email: 'ada@example.com',
  role: 'user',
  created_at: null,
};

function resetSession() {
  useSessionStore.setState({ status: 'restoring', accessToken: null, user: null });
}

test('starts in the restoring state', () => {
  resetSession();

  assert.equal(useSessionStore.getState().status, 'restoring');
});

test('setSession keeps the access token in memory', () => {
  resetSession();

  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });

  assert.equal(useSessionStore.getState().status, 'authenticated');
  assert.equal(useSessionStore.getState().accessToken, 'access-1');
  assert.deepEqual(useSessionStore.getState().user, user);
});

test('clearSession drops the access token and user', () => {
  useSessionStore.getState().setSession({ user, accessToken: 'access-1' });

  useSessionStore.getState().clearSession();

  assert.equal(useSessionStore.getState().status, 'unauthenticated');
  assert.equal(useSessionStore.getState().accessToken, null);
  assert.equal(useSessionStore.getState().user, null);
});
