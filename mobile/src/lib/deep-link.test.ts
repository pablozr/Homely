import assert from 'node:assert/strict';
import test from 'node:test';

import { authCodeFromUrl } from './deep-link';

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
