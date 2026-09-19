import assert from 'node:assert/strict';
import test from 'node:test';

import { authCodeFromUrl, inviteTokenFromInput, inviteTokenFromUrl } from './deep-link';

test('extracts the auth code from a homely deep link', () => {
  assert.equal(authCodeFromUrl('homely://auth?auth_code=abc123'), 'abc123');
});

test('extracts the auth code from a path-style deep link', () => {
  assert.equal(authCodeFromUrl('homely:///auth?auth_code=xyz789'), 'xyz789');
});

test('returns null when the deep link has no auth code', () => {
  assert.equal(authCodeFromUrl('homely://auth'), null);
  assert.equal(authCodeFromUrl(null), null);
});

test('returns null for blank or malformed deep links', () => {
  assert.equal(authCodeFromUrl('homely://auth?auth_code='), null);
  assert.equal(authCodeFromUrl('not a url'), null);
});

test('extracts the invite token from the invite deep link', () => {
  assert.equal(inviteTokenFromUrl('homely://invite?invite_token=token-123'), 'token-123');
  assert.equal(inviteTokenFromUrl('homely:///invite?invite_token=token-456'), 'token-456');
});

test('inviteTokenFromUrl ignores other links and malformed values', () => {
  assert.equal(inviteTokenFromUrl('homely://auth?auth_code=abc123'), null);
  assert.equal(inviteTokenFromUrl('homely://invite?invite_token='), null);
  assert.equal(inviteTokenFromUrl('not a url'), null);
  assert.equal(inviteTokenFromUrl(null), null);
});

test('inviteTokenFromInput accepts a full link or a raw token', () => {
  assert.equal(inviteTokenFromInput('homely://invite?invite_token=token-123'), 'token-123');
  assert.equal(inviteTokenFromInput('  raw-token  '), 'raw-token');
});

test('inviteTokenFromInput rejects blank and non-invite links', () => {
  assert.equal(inviteTokenFromInput('   '), null);
  assert.equal(inviteTokenFromInput('homely://auth?auth_code=abc'), null);
});
