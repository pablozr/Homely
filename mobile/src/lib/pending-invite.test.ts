import assert from 'node:assert/strict';
import test from 'node:test';

import {
  INVITE_TOKEN_MAX_LENGTH,
  PENDING_INVITE_TTL_MS,
  createPendingInvite,
  isPendingInviteExpired,
  parseInviteToken,
  parsePendingInvite,
} from './pending-invite';

const NOW = 1_800_000_000_000;

test('parseInviteToken trims and keeps a valid token', () => {
  assert.equal(parseInviteToken('  abc123  '), 'abc123');
  assert.equal(
    parseInviteToken('a'.repeat(INVITE_TOKEN_MAX_LENGTH)),
    'a'.repeat(INVITE_TOKEN_MAX_LENGTH),
  );
});

test('parseInviteToken rejects blank and oversized tokens', () => {
  assert.equal(parseInviteToken('   '), null);
  assert.equal(parseInviteToken('a'.repeat(INVITE_TOKEN_MAX_LENGTH + 1)), null);
  assert.equal(parseInviteToken(null), null);
  assert.equal(parseInviteToken(123), null);
});

test('createPendingInvite stamps the saved time', () => {
  assert.deepEqual(createPendingInvite('token-1', NOW), { token: 'token-1', savedAt: NOW });
});

test('isPendingInviteExpired uses the seven day window', () => {
  const invite = createPendingInvite('token-1', NOW);

  assert.equal(isPendingInviteExpired(invite, NOW + PENDING_INVITE_TTL_MS - 1), false);
  assert.equal(isPendingInviteExpired(invite, NOW + PENDING_INVITE_TTL_MS), true);
});

test('parsePendingInvite reads back a fresh pending invite', () => {
  const invite = createPendingInvite('token-1', NOW);
  const parsed = parsePendingInvite(JSON.stringify(invite), NOW + 1000);

  assert.deepEqual(parsed, invite);
});

test('parsePendingInvite drops expired invites', () => {
  const invite = createPendingInvite('token-1', NOW);

  assert.equal(parsePendingInvite(JSON.stringify(invite), NOW + PENDING_INVITE_TTL_MS), null);
});

test('parsePendingInvite rejects malformed and foreign payloads', () => {
  assert.equal(parsePendingInvite(null, NOW), null);
  assert.equal(parsePendingInvite('not json', NOW), null);
  assert.equal(parsePendingInvite('{"token":"t"}', NOW), null);
  assert.equal(parsePendingInvite('{"token":"","savedAt":1}', NOW), null);
  assert.equal(parsePendingInvite('{"token":"t","savedAt":-1}', NOW), null);
  assert.equal(
    parsePendingInvite(JSON.stringify({ token: 't', savedAt: NOW, extra: true }), NOW)?.token,
    't',
  );
});
