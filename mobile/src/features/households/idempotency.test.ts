import assert from 'node:assert/strict';
import test from 'node:test';

import { resolveIdempotencyAttempt } from './idempotency';

test('creates a key for the first attempt', () => {
  const attempt = resolveIdempotencyAttempt(null, '{"name":"a"}', () => 'key-1');

  assert.deepEqual(attempt, { key: 'key-1', signature: '{"name":"a"}' });
});

test('reuses the key when retrying with the same payload', () => {
  const first = resolveIdempotencyAttempt(null, '{"name":"a"}', () => 'key-1');
  const retry = resolveIdempotencyAttempt(first, '{"name":"a"}', () => 'key-2');

  assert.equal(retry.key, 'key-1');
  assert.equal(retry, first);
});

test('replaces the key when the payload changes', () => {
  const first = resolveIdempotencyAttempt(null, '{"name":"a"}', () => 'key-1');
  const changed = resolveIdempotencyAttempt(first, '{"name":"b"}', () => 'key-2');

  assert.equal(changed.key, 'key-2');
  assert.equal(changed.signature, '{"name":"b"}');
});
