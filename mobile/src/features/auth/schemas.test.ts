import assert from 'node:assert/strict';
import test from 'node:test';

import { emailSchema } from './schemas';

test('normalizes a valid email', () => {
  const parsed = emailSchema.safeParse('  Person@Example.COM ');

  assert.equal(parsed.success, true);
  if (parsed.success) {
    assert.equal(parsed.data, 'person@example.com');
  }
});

test('rejects an invalid email', () => {
  assert.equal(emailSchema.safeParse('not-an-email').success, false);
});
